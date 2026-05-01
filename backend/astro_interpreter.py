from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PredictiveInterpretRequest(BaseModel):
    predictive_data: dict[str, Any]
    client_name: str | None = None
    focus_question: str | None = None
    style: str = "professional_serbian"


ALLOWED_STATUSES = {"strong"}
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
    allowed = status in ALLOWED_STATUSES or permission == "allowed"
    cautious = status in CAUTION_STATUSES or permission == "caution_only"
    blocked = status in BLOCKED_STATUSES or permission == "blocked"
    return {
        "theme": theme_key,
        "label": theme.get("label"),
        "status": status,
        "confirmation_score": theme.get("confirmation_score"),
        "raw_confirmation_score": theme.get("raw_confirmation_score"),
        "permission": permission,
        "can_claim_concrete_event": allowed,
        "must_be_cautious": not allowed and not blocked,
        "blocked_for_event_claims": blocked,
        "layer_counts": theme.get("layer_counts"),
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


def _enrich_group_item(item: dict[str, Any], themes: dict[str, Any]) -> dict[str, Any]:
    theme_key = item.get("theme")
    source_theme = themes.get(theme_key, {}) if theme_key else {}
    block = _theme_block(theme_key, source_theme) if theme_key and source_theme else dict(item)
    block.update({k: v for k, v in item.items() if v is not None})
    return block


def _build_fallback_theme_groups(themes: dict[str, Any], ranked: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    hard_event_blocks: list[dict[str, Any]] = []
    narrative_focus_blocks: list[dict[str, Any]] = []
    supporting_blocks: list[dict[str, Any]] = []
    blocked_blocks: list[dict[str, Any]] = []

    for item in ranked:
        key = item.get("theme")
        if not key or key not in themes:
            continue
        block = _theme_block(key, themes[key])
        counts = block.get("layer_counts") or {}
        score = float(block.get("confirmation_score") or 0)
        structural_layers = sum(1 for layer in ["annual", "solar", "progression", "solar_arc"] if counts.get(layer, 0) > 0)
        has_core_natal = counts.get("core_natal", 0) > 0
        has_annual_or_solar = counts.get("annual", 0) > 0 or counts.get("solar", 0) > 0
        has_direction = counts.get("primary_progression", 0) > 0 or counts.get("primary_solar_arc", 0) > 0
        if block["can_claim_concrete_event"]:
            block["astrological_level"] = "hard_event_allowed"
            block["narrative_mode"] = "concrete_event_allowed"
            hard_event_blocks.append(block)
        elif has_core_natal and score >= 5.25 and structural_layers >= 2 and (has_annual_or_solar or has_direction):
            block["astrological_level"] = "main_narrative_focus"
            block["narrative_mode"] = "main_theme_without_event_claim"
            block["wording_rule"] = "Formulisati kao glavnu aktiviranu oblast, proces, pritisak ili potrebu za odlukom; bez tvrdnje da će se događaj sigurno desiti."
            narrative_focus_blocks.append(block)
        elif not block["blocked_for_event_claims"]:
            block["astrological_level"] = "supporting_tendency"
            block["narrative_mode"] = "brief_tendency_only"
            block["wording_rule"] = "Pomenuti kratko kao sporednu tendenciju ili pozadinski pritisak."
            supporting_blocks.append(block)
        else:
            blocked_blocks.append({"theme": key, "label": block.get("label"), "status": block.get("status"), "rule": "Do not claim concrete event."})
    return {
        "hard_event_theme_blocks": hard_event_blocks,
        "narrative_focus_theme_blocks": narrative_focus_blocks[:4],
        "supporting_tendency_theme_blocks": narrative_focus_blocks[4:] + supporting_blocks,
        "blocked_theme_blocks": blocked_blocks,
    }


def build_interpretation_payload(data: dict[str, Any], client_name: str | None = None, focus_question: str | None = None) -> dict[str, Any]:
    matrix = data.get("confirmation_matrix") or {}
    themes = matrix.get("themes") or {}
    ranked = matrix.get("ranked_themes") or []
    month_by_month = data.get("month_by_month") or {}

    source_groups = matrix.get("astrological_theme_groups") or {}
    if source_groups:
        hard_event_blocks = [_enrich_group_item(item, themes) for item in source_groups.get("hard_event_theme_blocks", [])]
        narrative_focus_blocks = [_enrich_group_item(item, themes) for item in source_groups.get("narrative_focus_theme_blocks", [])]
        supporting_blocks = [_enrich_group_item(item, themes) for item in source_groups.get("supporting_tendency_theme_blocks", [])]
        blocked_blocks = source_groups.get("blocked_theme_blocks", [])
    else:
        fallback_groups = _build_fallback_theme_groups(themes, ranked)
        hard_event_blocks = fallback_groups["hard_event_theme_blocks"]
        narrative_focus_blocks = fallback_groups["narrative_focus_theme_blocks"]
        supporting_blocks = fallback_groups["supporting_tendency_theme_blocks"]
        blocked_blocks = fallback_groups["blocked_theme_blocks"]

    cautious_blocks = narrative_focus_blocks + supporting_blocks
    months = month_by_month.get("months", []) or []
    top_months = sorted(months, key=lambda m: m.get("month_intensity_score", 0), reverse=True)[:8]

    return {
        "success": True,
        "schema": "ASTRO_ARIES_PREDICTIVE_INTERPRETATION_PAYLOAD_V1",
        "client_name": client_name,
        "focus_question": focus_question,
        "rules": {
            "source": "Interpret only from predictive calculation JSON.",
            "method_hierarchy": "Natal promise first; annual profection and solar return frame the year; progressions and solar arc confirm development; transits and lunar returns time the manifestation only.",
            "allowed": "Concrete event wording allowed only for hard_event_theme_blocks / confirmation_matrix status strong.",
            "narrative_focus": "Narrative focus themes may be written as active life themes, processes, pressure points or decisions, but not as guaranteed events.",
            "supporting_tendency": "Supporting themes may be mentioned briefly as tendencies only.",
            "insufficient": "Insufficient themes must not be turned into predictions.",
            "transit_rule": "Transits are timing, not standalone proof.",
            "tone": "Serbian, professional astrologer voice, direct but not fatalistic.",
        },
        "allowed_theme_blocks": hard_event_blocks[:8],
        "hard_event_theme_blocks": hard_event_blocks[:8],
        "narrative_focus_theme_blocks": narrative_focus_blocks[:4],
        "supporting_tendency_theme_blocks": supporting_blocks[:8],
        "cautious_theme_blocks": cautious_blocks[:10],
        "blocked_theme_blocks": blocked_blocks[:12],
        "top_timing_months": top_months,
        "draft_structure": [
            "Uvod: kratak, ljudski, bez tehničkog pretrpavanja.",
            "Glavne narativne teme: narrative_focus_theme_blocks, bez tvrdnje da se događaj sigurno dešava.",
            "Konkretni događaji: samo hard_event_theme_blocks ako postoje.",
            "Vremenski raspored: meseci sa najvećim month_intensity_score i tranziti kao tajming.",
            "Sporedne tendencije: supporting_tendency_theme_blocks kratko i oprezno.",
            "Šta se ne tvrdi: blocked_theme_blocks se ne predstavljaju kao događaj.",
        ],
    }


def interpret_predictive_payload(request: PredictiveInterpretRequest) -> dict[str, Any]:
    payload = build_interpretation_payload(request.predictive_data, request.client_name, request.focus_question)
    # This endpoint deliberately returns a controlled interpretation payload, not free prose yet.
    # The next AI writing layer can use this payload as its only allowed source.
    return payload
