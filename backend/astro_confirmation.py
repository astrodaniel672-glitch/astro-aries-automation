from __future__ import annotations

from typing import Any

THEMES = {
    "identity_vitality": {"label": "Ličnost, telo, vitalnost, životni pravac", "houses": {1}, "planets": {"Sunce", "Mars", "ASC"}, "angles": {"ASC"}},
    "money_values": {"label": "Novac, zarada, vrednosti, imovina", "houses": {2, 8}, "planets": {"Venera", "Jupiter", "Saturn"}, "angles": set()},
    "communication_learning": {"label": "Učenje, papiri, komunikacija, kraći putevi", "houses": {3, 9}, "planets": {"Merkur", "Jupiter"}, "angles": set()},
    "home_family": {"label": "Dom, porodica, nekretnine, privatna osnova", "houses": {4}, "planets": {"Mesec", "Saturn", "IC"}, "angles": {"IC"}},
    "love_children_creativity": {"label": "Ljubav, deca, kreativnost, radost", "houses": {5}, "planets": {"Venera", "Sunce", "Mesec"}, "angles": set()},
    "work_health_routine": {"label": "Posao, rutina, zdravlje, obaveze", "houses": {6}, "planets": {"Merkur", "Mars", "Saturn"}, "angles": set()},
    "relationships_marriage": {"label": "Odnosi, partnerstvo, brak, javni ugovori", "houses": {7}, "planets": {"Venera", "Mars", "Mesec", "DSC"}, "angles": {"DSC"}},
    "crisis_transformation": {"label": "Krize, dugovi, tuđ novac, duboka transformacija", "houses": {8}, "planets": {"Mars", "Saturn", "Pluton", "Mesec"}, "angles": set()},
    "foreign_higher_education": {"label": "Inostranstvo, viša znanja, pravo, vera, putovanja", "houses": {9}, "planets": {"Jupiter", "Merkur", "Sunce"}, "angles": set()},
    "career_status": {"label": "Karijera, status, pravac, autoritet", "houses": {10}, "planets": {"Sunce", "Saturn", "Mars", "Jupiter", "MC"}, "angles": {"MC"}},
    "friends_networks": {"label": "Prijatelji, mreže, planovi, publika", "houses": {11}, "planets": {"Jupiter", "Venera", "Saturn"}, "angles": set()},
    "hidden_endings_psychology": {"label": "Podsvest, izolacija, tajne, završeci, skriveni neprijatelji", "houses": {12}, "planets": {"Saturn", "Neptun", "Pluton", "Mesec"}, "angles": set()},
}

HARD_WEIGHTS = {"primary_evidence": 3, "strong_evidence": 2, "supporting_evidence": 1, "secondary_support": 0.5}
FAST_TIMING_POINTS = {"Mesec", "Sunce", "Merkur", "Venera"}
SLOW_OR_STRUCTURAL_POINTS = {"Mars", "Jupiter", "Saturn", "Uran", "Neptun", "Pluton", "Severni čvor", "Južni čvor", "ASC", "DSC", "MC", "IC"}


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _point_name(value: str | None) -> str:
    if not value:
        return ""
    return str(value).replace("angle: ", "").replace("planet: ", "").replace("natal_point: ", "").strip()


def _houses_for_natal_point(natal_book: dict[str, Any], point: str) -> set[int]:
    point = _point_name(point)
    houses: set[int] = set()
    planets = natal_book.get("planets", {}) or {}
    angles = natal_book.get("angles", {}) or {}
    lots = natal_book.get("arabic_lots", {}) or {}
    midpoints = natal_book.get("midpoints", {}) or {}
    for source in (planets, angles, lots, midpoints):
        if point in source:
            h = _safe_int(source[point].get("house"))
            if h:
                houses.add(h)
    return houses


def _theme_match_score(theme: dict[str, Any], natal_book: dict[str, Any], row: dict[str, Any]) -> float:
    points = {_point_name(row.get("point_a")), _point_name(row.get("point_b"))}
    houses: set[int] = set()
    for p in points:
        houses |= _houses_for_natal_point(natal_book, p)
    score = 0.0
    if houses & theme["houses"]:
        score += 2.0
    if points & theme["planets"]:
        score += 1.5
    if points & theme["angles"]:
        score += 2.0
    if row.get("hard_event_candidate"):
        score += 0.5
    return score


def _usable(row: dict[str, Any]) -> bool:
    return bool(row.get("usable_as_proof")) or row.get("evidence_weight") in {"primary_evidence", "strong_evidence", "supporting_evidence"}


def _is_fast_timing_only(row: dict[str, Any]) -> bool:
    # Brzi tranziti su timing, ne dokaz za godišnji događaj. Mars ostaje relevantan kao okidač/akcija.
    method = str(row.get("method") or "")
    if not method.startswith("transit"):
        return False
    return _point_name(row.get("point_a")) in FAST_TIMING_POINTS


def _row_weight(row: dict[str, Any]) -> float:
    if _is_fast_timing_only(row):
        return 0.25
    return float(HARD_WEIGHTS.get(row.get("evidence_weight"), 0.0))


def _collect_natal_basis(theme: dict[str, Any], natal_book: dict[str, Any], natal_proof_book: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bucket in ["primary_evidence", "strong_evidence", "supporting_evidence"]:
        for row in natal_proof_book.get(bucket, []) or []:
            match = _theme_match_score(theme, natal_book, row)
            if match > 0:
                item = dict(row)
                item["theme_match_score"] = match
                rows.append(item)
    rows.sort(key=lambda x: (-x.get("theme_match_score", 0), x.get("orb", 99)))
    return rows[:6]


def _annual_activation(theme: dict[str, Any], annual: dict[str, Any]) -> dict[str, Any]:
    active_house = _safe_int((annual or {}).get("active_house"))
    lord = (annual or {}).get("lord_of_year")
    activated = bool(active_house in theme["houses"] or lord in theme["planets"])
    return {"active_house": active_house, "lord_of_year": lord, "activated": activated, "score": 2 if activated else 0}


def _solar_support(theme: dict[str, Any], solar_return: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    planets = solar_return.get("planets", {}) or {}
    angles = solar_return.get("angles", {}) or {}
    for name, data in {**planets, **angles}.items():
        house = _safe_int(data.get("house"))
        direct_house = house in theme["houses"] if house else False
        direct_point = name in theme["angles"] or name in theme["planets"]
        if direct_house or direct_point:
            # Bez solarne kuće ovo je slab signal, ne pun dokaz.
            score = 1 if direct_house else 0.25
            rows.append({"point": name, "formatted": data.get("formatted"), "house": house, "score": score, "support_type": "house" if direct_house else "planet_only"})
    rows.sort(key=lambda x: -float(x.get("score") or 0))
    return rows[:6]


def _predictive_support(theme: dict[str, Any], natal_book: dict[str, Any], rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not _usable(row):
            continue
        match = _theme_match_score(theme, natal_book, row)
        if match > 0:
            item = dict(row)
            item["theme_match_score"] = match
            item["confirmation_weight"] = _row_weight(row)
            item["confirmation_source"] = source
            if _is_fast_timing_only(row):
                item["timing_only"] = True
            out.append(item)
    out.sort(key=lambda x: (-x.get("confirmation_weight", 0), -x.get("theme_match_score", 0), x.get("orb", 99)))
    return out[:8]


def _lunar_support(theme: dict[str, Any], natal_book: dict[str, Any], lunar_returns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not lunar_returns:
        return []
    return [{"method": row.get("method"), "exact_utc": row.get("exact_utc"), "orb": row.get("orb"), "trigger_role": "monthly_timing_only"} for row in lunar_returns[:4]]


def _structural_layer_count(counts: dict[str, int]) -> int:
    # Tranzit i lunacija nisu strukturni sloj; oni su timing. Solar je strukturni samo ako nije samo planet_only.
    return sum(1 for key in ["annual", "solar", "progression", "solar_arc"] if counts.get(key, 0) > 0)


def _status(score: float, counts: dict[str, int]) -> str:
    has_natal = counts.get("natal", 0) > 0
    structural_layers = _structural_layer_count(counts)
    has_direction = counts.get("progression", 0) > 0 or counts.get("solar_arc", 0) > 0
    has_annual_or_solar = counts.get("annual", 0) > 0 or counts.get("solar", 0) > 0
    if has_natal and has_annual_or_solar and has_direction and structural_layers >= 3 and score >= 9:
        return "strong"
    if has_natal and has_direction and structural_layers >= 2 and score >= 6:
        return "moderate"
    if has_natal and (has_direction or has_annual_or_solar) and score >= 3.5:
        return "weak"
    return "insufficient"


def build_confirmation_matrix(result: dict[str, Any]) -> dict[str, Any]:
    natal_book = result.get("natal_book_of_data") or {}
    natal_proof = result.get("natal_proof_book") or (natal_book.get("proof_book") if isinstance(natal_book, dict) else {}) or {}
    annual = result.get("annual_profection") or {}
    solar_return = result.get("solar_return") or {}
    progressions = (result.get("secondary_progressions") or {}).get("contacts_to_natal", [])
    solar_arc = (result.get("solar_arc") or {}).get("contacts_to_natal", [])
    transits = (result.get("transits_to_natal") or {}).get("window_hits", [])
    lunars = result.get("lunar_returns") or []

    matrix: dict[str, Any] = {}
    for theme_key, theme in THEMES.items():
        natal_basis = _collect_natal_basis(theme, natal_book, natal_proof)
        annual_activation = _annual_activation(theme, annual)
        solar_support_all = _solar_support(theme, solar_return)
        solar_structural = [x for x in solar_support_all if x.get("support_type") == "house"]
        progression_support = _predictive_support(theme, natal_book, progressions, "progression")
        solar_arc_support = _predictive_support(theme, natal_book, solar_arc, "solar_arc")
        transit_timing = _predictive_support(theme, natal_book, transits, "transit")
        lunar_triggers = _lunar_support(theme, natal_book, lunars)

        counts = {
            "natal": len(natal_basis),
            "annual": 1 if annual_activation.get("activated") else 0,
            "solar": len(solar_structural),
            "solar_planet_only": len([x for x in solar_support_all if x.get("support_type") == "planet_only"]),
            "progression": len(progression_support),
            "solar_arc": len(solar_arc_support),
            "transit": len([x for x in transit_timing if not x.get("timing_only")]),
            "fast_timing": len([x for x in transit_timing if x.get("timing_only")]),
            "lunar": len(lunar_triggers),
        }

        score = 0.0
        score += min(2, len(natal_basis)) * 1.25
        score += annual_activation.get("score", 0)
        score += sum(float(row.get("score") or 0) for row in solar_support_all[:4])
        score += min(4, sum(row.get("confirmation_weight", 0) for row in progression_support[:2]))
        score += min(5, sum(row.get("confirmation_weight", 0) for row in solar_arc_support[:3]))
        # Tranziti su timing: spori/Mars imaju limitiran doprinos; Mesec/Sunce/Merkur/Venera skoro samo datiraju.
        score += min(1.5, sum(row.get("confirmation_weight", 0) for row in transit_timing[:6]))
        score += 0.25 if lunar_triggers and (progression_support or solar_arc_support) else 0

        status = _status(score, counts)
        matrix[theme_key] = {
            "label": theme["label"],
            "status": status,
            "confirmation_score": round(score, 2),
            "layer_counts": counts,
            "natal_basis": natal_basis,
            "annual_activation": annual_activation,
            "solar_return_support": solar_support_all,
            "progression_support": progression_support,
            "solar_arc_support": solar_arc_support,
            "transit_timing": transit_timing,
            "lunar_triggers": lunar_triggers,
            "interpretation_permission": "allowed" if status in {"strong", "moderate"} else "caution_or_do_not_claim_event",
        }

    ranked = sorted(matrix.items(), key=lambda kv: kv[1]["confirmation_score"], reverse=True)
    return {
        "rules": {
            "strong": "Natal basis + annual/solar activation + progression or solar arc + at least 3 structural layers. Transits only time the event.",
            "moderate": "Natal basis + progression or solar arc + at least 2 structural layers.",
            "weak": "Natal basis plus limited support; mention as tendency only.",
            "insufficient": "Do not claim a concrete event. Context only.",
            "transit_rule": "Fast transits and lunar returns are timing only. They cannot lift a theme to strong by themselves.",
            "solar_rule": "Solar return planet-only support without house placement is weak support, not a full structural layer.",
        },
        "ranked_themes": [{"theme": key, "label": value["label"], "status": value["status"], "confirmation_score": value["confirmation_score"]} for key, value in ranked],
        "themes": matrix,
    }
