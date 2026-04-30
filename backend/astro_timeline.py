from __future__ import annotations

from datetime import datetime
from typing import Any


def _month_key(iso_text: str | None) -> str | None:
    if not iso_text:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_text).replace("Z", "+00:00"))
        return f"{dt.year:04d}-{dt.month:02d}"
    except Exception:
        return None


def _event_date(row: dict[str, Any]) -> str | None:
    return row.get("exact_utc") or row.get("calculation_utc") or row.get("progressed_utc_symbolic")


def _event_weight(row: dict[str, Any]) -> int:
    weight = row.get("evidence_weight")
    if weight == "primary_evidence":
        return 4
    if weight == "strong_evidence":
        return 3
    if weight == "supporting_evidence":
        return 2
    if weight == "secondary_support":
        return 1
    return 0


def _compact_contact(row: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "source": source,
        "date": _event_date(row),
        "point_a": row.get("point_a"),
        "point_b": row.get("point_b"),
        "aspect": row.get("aspect"),
        "orb": row.get("orb"),
        "orb_class": row.get("orb_class"),
        "evidence_weight": row.get("evidence_weight"),
        "usable_as_proof": row.get("usable_as_proof"),
        "hard_event_candidate": row.get("hard_event_candidate"),
        "method": row.get("method"),
    }


def _theme_hits_for_contact(row: dict[str, Any], confirmation_matrix: dict[str, Any]) -> list[str]:
    themes = (confirmation_matrix or {}).get("themes", {}) or {}
    out: list[str] = []
    a = row.get("point_a")
    b = row.get("point_b")
    aspect = row.get("aspect")
    for key, data in themes.items():
        supports = []
        for bucket in ["progression_support", "solar_arc_support", "transit_timing"]:
            supports.extend(data.get(bucket, []) or [])
        for item in supports:
            if item.get("point_a") == a and item.get("point_b") == b and item.get("aspect") == aspect:
                out.append(key)
                break
    return out[:5]


def _sanitize_lunar_returns(lunar_returns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = []
    for row in lunar_returns or []:
        try:
            orb = float(row.get("orb") or 999)
        except Exception:
            orb = 999
        if orb <= 1.0:
            clean.append(row)
    return clean


def _append_warning_once(result: dict[str, Any], warning: str) -> None:
    warnings = result.setdefault("quality_warnings", [])
    if warning not in warnings:
        warnings.append(warning)


def build_month_by_month(result: dict[str, Any]) -> dict[str, Any]:
    confirmation_matrix = result.get("confirmation_matrix") or {}
    months: dict[str, dict[str, Any]] = {}

    def ensure_month(key: str) -> dict[str, Any]:
        if key not in months:
            months[key] = {
                "month": key,
                "events": [],
                "primary_count": 0,
                "strong_count": 0,
                "supporting_count": 0,
                "hard_event_candidates": 0,
                "top_themes": {},
            }
        return months[key]

    sources = {
        "transit": ((result.get("transits_to_natal") or {}).get("window_hits") or []),
        "secondary_progression": ((result.get("secondary_progressions") or {}).get("contacts_to_natal") or []),
        "solar_arc": ((result.get("solar_arc") or {}).get("contacts_to_natal") or []),
    }

    for source, rows in sources.items():
        for row in rows:
            if not row.get("usable_as_proof"):
                continue
            key = _month_key(_event_date(row))
            if not key:
                key = _month_key((result.get("settings") or {}).get("prediction_start"))
            if not key:
                continue
            event = _compact_contact(row, source)
            event["theme_hits"] = _theme_hits_for_contact(row, confirmation_matrix)
            bucket = ensure_month(key)
            bucket["events"].append(event)
            if event.get("evidence_weight") == "primary_evidence":
                bucket["primary_count"] += 1
            elif event.get("evidence_weight") == "strong_evidence":
                bucket["strong_count"] += 1
            elif event.get("evidence_weight") == "supporting_evidence":
                bucket["supporting_count"] += 1
            if event.get("hard_event_candidate"):
                bucket["hard_event_candidates"] += 1
            for theme in event.get("theme_hits") or []:
                bucket["top_themes"][theme] = bucket["top_themes"].get(theme, 0) + _event_weight(row)

    clean_lunars = _sanitize_lunar_returns(result.get("lunar_returns") or [])
    for row in clean_lunars:
        key = _month_key(row.get("exact_utc"))
        if not key:
            continue
        bucket = ensure_month(key)
        bucket["events"].append({
            "source": "lunar_return",
            "date": row.get("exact_utc"),
            "orb": row.get("orb"),
            "trigger_role": "monthly_timing_only",
            "usable_as_proof": False,
        })

    ordered = []
    for key in sorted(months.keys()):
        bucket = months[key]
        bucket["events"].sort(key=lambda x: (x.get("date") or "", -1 if x.get("usable_as_proof") else 1))
        bucket["top_themes_ranked"] = sorted(bucket["top_themes"].items(), key=lambda kv: kv[1], reverse=True)[:5]
        bucket["month_intensity_score"] = bucket["primary_count"] * 4 + bucket["strong_count"] * 3 + bucket["supporting_count"] * 2 + bucket["hard_event_candidates"]
        ordered.append(bucket)

    return {
        "rules": {
            "purpose": "Month-by-month timing index. It is calculation-only, not interpretation.",
            "proof_rule": "Only proof contacts are counted for intensity. Lunar returns are timing triggers only.",
            "lunar_filter": "Lunar return entries with orb greater than 1° are removed as false returns/oppositions.",
        },
        "months": ordered,
        "clean_lunar_returns_count": len(clean_lunars),
    }


def enhance_with_timeline(result: dict[str, Any]) -> dict[str, Any]:
    clean_lunars = _sanitize_lunar_returns(result.get("lunar_returns") or [])
    removed = len(result.get("lunar_returns") or []) - len(clean_lunars)
    result["lunar_returns"] = clean_lunars
    result["month_by_month"] = build_month_by_month(result)
    if removed:
        _append_warning_once(result, f"Filtered {removed} invalid lunar_return rows with orb > 1°.")
    _append_warning_once(result, "month_by_month added: monthly timing index from usable predictive contacts and clean lunar returns.")
    return result
