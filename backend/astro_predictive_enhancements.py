from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import swisseph as swe

SIGNS_SR = ["Ovan", "Bik", "Blizanci", "Rak", "Lav", "Devica", "Vaga", "Škorpion", "Strelac", "Jarac", "Vodolija", "Ribe"]
RULERS = {
    "Ovan": "Mars", "Bik": "Venera", "Blizanci": "Merkur", "Rak": "Mesec", "Lav": "Sunce", "Devica": "Merkur",
    "Vaga": "Venera", "Škorpion": "Mars", "Strelac": "Jupiter", "Jarac": "Saturn", "Vodolija": "Saturn", "Ribe": "Jupiter",
}
ASPECT_ANGLES = {"konjunkcija": 0, "opozicija": 180, "trigon": 120, "kvadrat": 90, "sekstil": 60, "kvinkunks": 150}
HARD_ASPECTS = {"konjunkcija", "opozicija", "kvadrat", "kvinkunks"}
STRUCTURAL_TRANSIT_PLANETS = {"Jupiter", "Saturn", "Uran", "Neptun", "Pluton", "Severni čvor", "Južni čvor"}
FAST_TIMING_PLANETS = {"Sunce", "Mesec", "Merkur", "Venera", "Mars"}


def _norm(x: float) -> float:
    return x % 360.0


def _diff(a: float, b: float) -> float:
    v = abs(_norm(a) - _norm(b)) % 360.0
    return 360.0 - v if v > 180 else v


def _signed_delta(a: float, b: float, angle: float) -> float:
    return (_norm(a - b) - angle + 540.0) % 360.0 - 180.0


def _jd(dt: datetime) -> float:
    utc = dt.astimezone(timezone.utc)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600, swe.GREG_CAL)


def _revjul_iso(jd_ut: float) -> str:
    y, m, d, h = swe.revjul(jd_ut, swe.GREG_CAL)
    hour = int(h)
    minute_float = (h - hour) * 60
    minute = int(minute_float)
    second = int(round((minute_float - minute) * 60))
    if second >= 60:
        second -= 60
        minute += 1
    if minute >= 60:
        minute -= 60
        hour += 1
    return datetime(y, m, d, min(hour, 23), minute, second, tzinfo=timezone.utc).isoformat()


def _parse_iso(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _sign_info(lon: float) -> dict[str, Any]:
    lon = _norm(lon)
    sign_index = int(lon // 30)
    deg_in_sign = lon % 30
    deg = int(deg_in_sign)
    minute_float = (deg_in_sign - deg) * 60
    minute = int(minute_float)
    second = int(round((minute_float - minute) * 60))
    sign = SIGNS_SR[sign_index]
    return {
        "longitude": round(lon, 6),
        "sign": sign,
        "sign_index": sign_index,
        "ruler": RULERS[sign],
        "degree_in_sign": round(deg_in_sign, 6),
        "degree": deg,
        "minute": minute,
        "second": second,
        "formatted": f"{deg}°{minute:02d}' {sign}",
    }


def _calc_lon(jd_ut: float, planet_id: int) -> float:
    res, _ = swe.calc_ut(jd_ut, planet_id, swe.FLG_MOSEPH | swe.FLG_SPEED)
    return float(res[0])


def _natal_points(predictive: dict[str, Any]) -> dict[str, dict[str, Any]]:
    natal = predictive.get("natal_book_of_data") or {}
    points: dict[str, dict[str, Any]] = {}
    for source in ("planets", "angles"):
        for name, data in (natal.get(source) or {}).items():
            if isinstance(data, dict) and data.get("longitude") is not None:
                points[name] = data
    for source in ("arabic_lots", "lots", "midpoints"):
        for name, data in (natal.get(source) or {}).items():
            if isinstance(data, dict) and data.get("longitude") is not None:
                points[f"{source}:{name}"] = data
    return points


def _point_contacts(lon: float, natal_points: dict[str, dict[str, Any]], max_orb: float = 2.0, hard_only: bool = False) -> list[dict[str, Any]]:
    contacts: list[dict[str, Any]] = []
    for natal_name, natal_data in natal_points.items():
        natal_lon = natal_data.get("longitude")
        if natal_lon is None:
            continue
        for aspect, angle in ASPECT_ANGLES.items():
            if hard_only and aspect not in HARD_ASPECTS:
                continue
            orb = abs(_signed_delta(lon, float(natal_lon), angle))
            if orb <= max_orb:
                contacts.append({
                    "target": natal_name,
                    "aspect": aspect,
                    "angle": angle,
                    "orb": round(orb, 4),
                    "natal_position": _sign_info(float(natal_lon)),
                    "timing_weight": "exact_trigger" if orb <= 0.25 else "strong_trigger" if orb <= 1.0 else "wide_trigger",
                    "usable_as_timing": orb <= 1.0,
                })
    contacts.sort(key=lambda item: (not item.get("usable_as_timing", False), float(item.get("orb") or 99)))
    return contacts[:24]


def _find_lunation_exact(prev_jd: float, curr_jd: float, target_angle: float) -> float:
    left, right = prev_jd, curr_jd
    for _ in range(40):
        mid = (left + right) / 2
        moon_left = _calc_lon(left, swe.MOON)
        sun_left = _calc_lon(left, swe.SUN)
        moon_mid = _calc_lon(mid, swe.MOON)
        sun_mid = _calc_lon(mid, swe.SUN)
        f_left = _signed_delta(moon_left, sun_left, target_angle)
        f_mid = _signed_delta(moon_mid, sun_mid, target_angle)
        if f_left == 0 or f_left * f_mid <= 0:
            right = mid
        else:
            left = mid
    return (left + right) / 2


def build_lunations_eclipses(predictive: dict[str, Any]) -> dict[str, Any]:
    start = _parse_iso((predictive.get("settings") or {}).get("prediction_start"))
    end = _parse_iso((predictive.get("settings") or {}).get("prediction_end"))
    if not start or not end:
        return {"schema": "ASTRO_ARIES_LUNATIONS_ECLIPSES_V1", "items": [], "quality_note": "Missing prediction period."}
    points = _natal_points(predictive)
    items: list[dict[str, Any]] = []
    prev_jd = _jd(start)
    prev_values = {}
    for angle in (0.0, 180.0):
        moon = _calc_lon(prev_jd, swe.MOON)
        sun = _calc_lon(prev_jd, swe.SUN)
        prev_values[angle] = _signed_delta(moon, sun, angle)
    jd_end = _jd(end)
    jd_now = prev_jd + 0.5
    while jd_now <= jd_end + 0.5:
        for angle, lunation_type in ((0.0, "Mlad Mesec"), (180.0, "Pun Mesec")):
            moon = _calc_lon(jd_now, swe.MOON)
            sun = _calc_lon(jd_now, swe.SUN)
            current = _signed_delta(moon, sun, angle)
            previous = prev_values[angle]
            if previous == 0 or previous * current < 0:
                exact_jd = _find_lunation_exact(jd_now - 0.5, jd_now, angle)
                exact_moon = _calc_lon(exact_jd, swe.MOON)
                exact_sun = _calc_lon(exact_jd, swe.SUN)
                node = _calc_lon(exact_jd, swe.TRUE_NODE)
                node_distance = min(_diff(exact_moon, node), _diff(exact_moon, node + 180))
                contacts = _point_contacts(exact_moon, points, max_orb=2.0, hard_only=True)
                eclipse_candidate = node_distance <= 12.0
                exact_eclipse_candidate = eclipse_candidate and node_distance <= 3.0
                item = {
                    "type": lunation_type,
                    "exact_utc": _revjul_iso(exact_jd),
                    "julian_day_ut": round(exact_jd, 8),
                    "moon_position": _sign_info(exact_moon),
                    "sun_position": _sign_info(exact_sun),
                    "node_distance_degrees": round(node_distance, 4),
                    "eclipse_candidate": eclipse_candidate,
                    "exact_eclipse_candidate": exact_eclipse_candidate,
                    "natal_contacts": contacts,
                    "usable_as_timing": bool([c for c in contacts if c.get("usable_as_timing")]) or exact_eclipse_candidate,
                    "timing_rule": "Lunation/eclipse is timing only. It can activate a theme, but cannot create an event without natal + annual/solar + progression/solar_arc proof.",
                }
                items.append(item)
            prev_values[angle] = current
        jd_now += 0.5
    items.sort(key=lambda item: item.get("exact_utc", ""))
    return {
        "schema": "ASTRO_ARIES_LUNATIONS_ECLIPSES_V1",
        "items": items[:40],
        "rules": {
            "lunation_trigger_orb": "<=1° to natal planet/angle is strong timing; <=2° is wider timing context.",
            "eclipse_candidate": "Moon within 12° of node; within 3° is exact eclipse candidate.",
            "interpretation_limit": "Timing layer only. Do not claim hard event without structural confirmation.",
        },
    }


def _all_structural_hits(predictive: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hit in (predictive.get("transits_to_natal") or {}).get("window_hits", []) or []:
        if hit.get("point_a") in STRUCTURAL_TRANSIT_PLANETS and hit.get("usable_as_proof"):
            item = dict(hit)
            item["source_layer"] = "slow_transit"
            rows.append(item)
    for layer in ("secondary_progressions", "solar_arc"):
        for hit in (predictive.get(layer) or {}).get("contacts_to_natal", []) or []:
            if hit.get("usable_as_proof"):
                item = dict(hit)
                item["source_layer"] = layer
                rows.append(item)
    return rows


def build_mars_detonators(predictive: dict[str, Any]) -> dict[str, Any]:
    window_hits = (predictive.get("transits_to_natal") or {}).get("window_hits", []) or []
    mars_hits = [hit for hit in window_hits if hit.get("point_a") == "Mars" and hit.get("usable_as_proof") and hit.get("aspect") in HARD_ASPECTS]
    structural = _all_structural_hits(predictive)
    detonators: list[dict[str, Any]] = []
    for mars in mars_hits:
        mars_dt = _parse_iso(mars.get("exact_utc"))
        matches = []
        for base in structural:
            base_dt = _parse_iso(base.get("exact_utc"))
            same_target = base.get("point_b") == mars.get("point_b")
            within_window = bool(mars_dt and base_dt and abs((mars_dt - base_dt).days) <= 45)
            if same_target or within_window:
                matches.append({
                    "source_layer": base.get("source_layer"),
                    "point_a": base.get("point_a"),
                    "point_b": base.get("point_b"),
                    "aspect": base.get("aspect"),
                    "orb": base.get("orb"),
                    "exact_utc": base.get("exact_utc"),
                    "match_reason": "same_target" if same_target else "near_structural_window",
                })
        if matches:
            detonators.append({
                "detonator": "Mars",
                "exact_utc": mars.get("exact_utc"),
                "target": mars.get("point_b"),
                "aspect": mars.get("aspect"),
                "orb": mars.get("orb"),
                "moving_position": mars.get("moving_position"),
                "matching_structural_proofs": matches[:10],
                "event_strength": "hard_event_trigger" if len(matches) >= 2 else "timing_trigger",
                "rule": "Mars detonates only an already-supported theme. It cannot create an event alone.",
            })
    detonators.sort(key=lambda item: item.get("exact_utc") or "")
    return {
        "schema": "ASTRO_ARIES_MARS_DETONATORS_V1",
        "items": detonators[:80],
        "rules": {
            "mars_role": "Mars is a detonator/timing layer only.",
            "required_base": "Requires slow transit/progression/solar arc or strong confirmation on same target/near window.",
        },
    }


def build_hard_event_windows(predictive: dict[str, Any]) -> dict[str, Any]:
    structural = _all_structural_hits(predictive)
    mars_items = (predictive.get("mars_detonators") or {}).get("items", []) or []
    lunations = (predictive.get("lunations_eclipses") or {}).get("items", []) or []
    windows: list[dict[str, Any]] = []
    for base in structural:
        base_dt = _parse_iso(base.get("exact_utc"))
        if not base_dt:
            continue
        start = base_dt - timedelta(days=7)
        end = base_dt + timedelta(days=7)
        detonators = [m for m in mars_items if m.get("target") == base.get("point_b") or (_parse_iso(m.get("exact_utc")) and abs((_parse_iso(m.get("exact_utc")) - base_dt).days) <= 14)]
        lunation_triggers = [l for l in lunations if l.get("usable_as_timing") and (_parse_iso(l.get("exact_utc")) and abs((_parse_iso(l.get("exact_utc")) - base_dt).days) <= 14)]
        if not detonators and not lunation_triggers and base.get("source_layer") == "slow_transit":
            continue
        windows.append({
            "window_start_utc": start.isoformat(),
            "peak_utc": base_dt.isoformat(),
            "window_end_utc": end.isoformat(),
            "structural_base": {
                "source_layer": base.get("source_layer"),
                "point_a": base.get("point_a"),
                "point_b": base.get("point_b"),
                "aspect": base.get("aspect"),
                "orb": base.get("orb"),
                "evidence_weight": base.get("evidence_weight"),
            },
            "mars_detonators": detonators[:5],
            "lunation_or_eclipse_triggers": lunation_triggers[:5],
            "claim_level": "hard_event_candidate" if detonators and lunation_triggers else "strong_process_window" if detonators else "timing_support_window",
            "interpretation_rule": "Hard claim still requires thematic confirmation_matrix support. This object gives timing windows, not standalone interpretation.",
        })
    windows.sort(key=lambda item: item.get("peak_utc", ""))
    return {
        "schema": "ASTRO_ARIES_HARD_EVENT_WINDOWS_V1",
        "items": windows[:120],
        "rules": {
            "claim_escalation": "hard_event_candidate requires structural base plus Mars and/or lunation trigger, then theme must be allowed by confirmation_matrix.",
            "no_standalone_claim": "Never use a window alone as a prediction without natal and theme confirmation.",
        },
    }


def build_ai_usage_checklist(predictive: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "ASTRO_ARIES_AI_USAGE_CHECKLIST_V1",
        "mandatory_order": [
            "1_natal_promise: natal_book_of_data + natal_proof_book define what can exist in the life story.",
            "2_annual_activation: annual_profection + lord_of_year + solar_return show the activated life area.",
            "3_structural_confirmation: secondary_progressions and/or solar_arc must confirm the theme for strong claims.",
            "4_timing: transits_to_natal, lunations_eclipses, lunar_returns and mars_detonators only time what is already supported.",
            "5_confirmation_matrix: allowed/narrative/supporting/blocked theme status controls how strongly AI may write.",
            "6_hard_event_windows: use only for date windows; never as standalone interpretation.",
        ],
        "forbidden_shortcuts": [
            "Do not claim event from transit alone.",
            "Do not claim event from lunar return alone.",
            "Do not claim event from Mars alone.",
            "Do not treat lots/midpoints as equal to planet/angle proof.",
            "Do not ignore cannot_claim from section evidence pack.",
            "Do not skip house ruler → placement → aspect → dispositor → dignity → life judgement chain.",
        ],
    }


def enhance_predictive_layers(predictive: dict[str, Any]) -> dict[str, Any]:
    predictive["lunations_eclipses"] = build_lunations_eclipses(predictive)
    predictive["mars_detonators"] = build_mars_detonators(predictive)
    predictive["hard_event_windows"] = build_hard_event_windows(predictive)
    predictive["ai_usage_checklist"] = build_ai_usage_checklist(predictive)
    warnings = predictive.setdefault("quality_warnings", [])
    warnings.append("Enhanced predictive timing added: lunations_eclipses, mars_detonators, hard_event_windows, ai_usage_checklist.")
    warnings.append("Hard event windows are timing candidates only; final narrative must still obey confirmation_matrix and evidence_pack cannot_claim.")
    return predictive
