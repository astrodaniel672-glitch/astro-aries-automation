from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PredictiveInterpretRequest(BaseModel):
    predictive_data: dict[str, Any]
    client_name: str | None = None
    focus_question: str | None = None
    style: str = "professional_serbian"


ALLOWED_STATUSES = {"strong", "moderate"}
CAUTION_STATUSES = {"weak"}
BLOCKED_STATUSES = {"insufficient"}


def _fmt_contact(row: dict[str, Any]) -> str:
    a = row.get("point_a") or row.get("source") or "tačka"
    b = row.get("point_b") or "natal"
    aspect = row.get("aspect") or "kontakt"
    orb = row.get("orb")
    date = row.get("exact_utc") or row.get("date") or "bez tačnog datuma"
    weight = row.get("evidence_weight") or row.get("orb_class") or "proof"
    return f"{a} {aspect} {b} — orb {orb}, {weight}, {date}"


def _top_rows(rows: list[dict[str, Any]], limit: int = 4) -> list[str]:
    return [_fmt_contact(row) for row in (rows or [])[:limit]]


def _theme_block(theme_key: str, theme: dict[str, Any]) -> dict[str, Any]:
    status = theme.get("status")
    permission = theme.get("interpretation_permission")
    allowed = status in ALLOWED_STATUSES
    cautious = status in CAUTION_STATUSES
    blocked = status in BLOCKED_STATUSES
    return {
        "theme": theme_key,
        "label": theme.get("label"),
        "status": status,
        "confirmation_score": theme.get("confirmation_score"),
        "permission": permission,
        "can_claim_concrete_event": allowed,
        "must_be_cautious": cautious,
        "blocked_for_event_claims": blocked,
        "evidence": {
            "natal_basis": _top_rows(theme.get("natal_basis", []), 3),
            "annual_activation": theme.get("annual_activation"),
            "solar_return_support": theme.get("solar_return_support", [])[:4],
            "progression_support": _top_rows(theme.get("progression_support", []), 4),
            "solar_arc_support": _top_rows(theme.get("solar_arc_support", []), 4),
            "transit_timing": _top_rows(theme.get("transit_timing", []), 6),
            "lunar_triggers": theme.get("lunar_triggers", [])[:4],
        },
    }


def build_interpretation_payload(data: dict[str, Any], client_name: str | None = None, focus_question: str | None = None) -> dict[str, Any]:
    matrix = data.get("confirmation_matrix") or {}
    themes = matrix.get("themes") or {}
    ranked = matrix.get("ranked_themes") or []
    month_by_month = data.get("month_by_month") or {}

    allowed_blocks = []
    cautious_blocks = []
    blocked_blocks = []

    for item in ranked:
        key = item.get("theme")
        if not key or key not in themes:
            continue
        block = _theme_block(key, themes[key])
        if block["can_claim_concrete_event"]:
            allowed_blocks.append(block)
        elif block["must_be_cautious"]:
            cautious_blocks.append(block)
        else:
            blocked_blocks.append({"theme": key, "label": block.get("label"), "status": block.get("status"), "rule": "Do not claim concrete event."})

    months = month_by_month.get("months", []) or []
    top_months = sorted(months, key=lambda m: m.get("month_intensity_score", 0), reverse=True)[:8]

    return {
        "success": True,
        "schema": "ASTRO_ARIES_PREDICTIVE_INTERPRETATION_PAYLOAD_V1",
        "client_name": client_name,
        "focus_question": focus_question,
        "rules": {
            "source": "Interpret only from predictive calculation JSON.",
            "allowed": "Concrete event wording allowed only for confirmation_matrix status strong/moderate.",
            "weak": "Weak themes may be mentioned as tendencies only, without firm event claims.",
            "insufficient": "Insufficient themes must not be turned into predictions.",
            "transit_rule": "Transits are timing, not standalone proof.",
            "tone": "Serbian, professional astrologer voice, direct but not fatalistic.",
        },
        "allowed_theme_blocks": allowed_blocks[:8],
        "cautious_theme_blocks": cautious_blocks[:6],
        "blocked_theme_blocks": blocked_blocks[:12],
        "top_timing_months": top_months,
        "draft_structure": [
            "Uvod: kratak, ljudski, bez tehničkog pretrpavanja.",
            "Glavne aktivirane teme: samo strong/moderate.",
            "Vremenski raspored: meseci sa najvećim month_intensity_score.",
            "Oprezne napomene: weak teme kao mogućnost, bez tvrdnji.",
            "Šta se ne tvrdi: insufficient teme se ne predstavljaju kao događaj.",
        ],
    }


def interpret_predictive_payload(request: PredictiveInterpretRequest) -> dict[str, Any]:
    payload = build_interpretation_payload(request.predictive_data, request.client_name, request.focus_question)
    # This endpoint deliberately returns a controlled interpretation payload, not free prose yet.
    # The next AI writing layer can use this payload as its only allowed source.
    return payload
