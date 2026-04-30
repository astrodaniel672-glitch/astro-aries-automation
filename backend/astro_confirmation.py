from __future__ import annotations

from typing import Any

THEMES = {
    "identity_vitality": {
        "label": "Ličnost, telo, vitalnost, životni pravac",
        "houses": {1},
        "planets": {"Sunce", "Mars", "ASC"},
        "angles": {"ASC"},
    },
    "money_values": {
        "label": "Novac, zarada, vrednosti, imovina",
        "houses": {2, 8},
        "planets": {"Venera", "Jupiter", "Saturn"},
        "angles": set(),
    },
    "communication_learning": {
        "label": "Učenje, papiri, komunikacija, kraći putevi",
        "houses": {3, 9},
        "planets": {"Merkur", "Jupiter"},
        "angles": set(),
    },
    "home_family": {
        "label": "Dom, porodica, nekretnine, privatna osnova",
        "houses": {4},
        "planets": {"Mesec", "Saturn", "IC"},
        "angles": {"IC"},
    },
    "love_children_creativity": {
        "label": "Ljubav, deca, kreativnost, radost",
        "houses": {5},
        "planets": {"Venera", "Sunce", "Mesec"},
        "angles": set(),
    },
    "work_health_routine": {
        "label": "Posao, rutina, zdravlje, obaveze",
        "houses": {6},
        "planets": {"Merkur", "Mars", "Saturn"},
        "angles": set(),
    },
    "relationships_marriage": {
        "label": "Odnosi, partnerstvo, brak, javni ugovori",
        "houses": {7},
        "planets": {"Venera", "Mars", "Mesec", "DSC"},
        "angles": {"DSC"},
    },
    "crisis_transformation": {
        "label": "Krize, dugovi, tuđ novac, duboka transformacija",
        "houses": {8},
        "planets": {"Mars", "Saturn", "Pluton", "Mesec"},
        "angles": set(),
    },
    "foreign_higher_education": {
        "label": "Inostranstvo, viša znanja, pravo, vera, putovanja",
        "houses": {9},
        "planets": {"Jupiter", "Merkur", "Sunce"},
        "angles": set(),
    },
    "career_status": {
        "label": "Karijera, status, pravac, autoritet",
        "houses": {10},
        "planets": {"Sunce", "Saturn", "Mars", "Jupiter", "MC"},
        "angles": {"MC"},
    },
    "friends_networks": {
        "label": "Prijatelji, mreže, planovi, publika",
        "houses": {11},
        "planets": {"Jupiter", "Venera", "Saturn"},
        "angles": set(),
    },
    "hidden_endings_psychology": {
        "label": "Podsvest, izolacija, tajne, završeci, skriveni neprijatelji",
        "houses": {12},
        "planets": {"Saturn", "Neptun", "Pluton", "Mesec"},
        "angles": set(),
    },
}

HARD_WEIGHTS = {
    "primary_evidence": 3,
    "strong_evidence": 2,
    "supporting_evidence": 1,
    "secondary_support": 0.5,
}


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
    if point.startswith("Lot of") or point.startswith("Pars"):
        item = lots.get(point)
        if item:
            h = _safe_int(item.get("house"))
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


def _row_weight(row: dict[str, Any]) -> float:
    return float(HARD_WEIGHTS.get(row.get("evidence_weight"), 0.0))


def _collect_natal_basis(theme: dict[str, Any], natal_book: dict[str, Any], natal_proof_book: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bucket in ["primary_evidence", "strong_evidence", "supporting_evidence"]:
        for row in natal_proof_book.get(bucket, []) or []:
            if _theme_match_score(theme, natal_book, row) > 0:
                item = dict(row)
                item["theme_match_score"] = _theme_match_score(theme, natal_book, row)
                rows.append(item)
    rows.sort(key=lambda x: (-x.get("theme_match_score", 0), x.get("orb", 99)))
    return rows[:8]


def _annual_activation(theme: dict[str, Any], annual: dict[str, Any]) -> dict[str, Any]:
    active_house = _safe_int((annual or {}).get("active_house"))
    lord = (annual or {}).get("lord_of_year")
    activated = bool(active_house in theme["houses"] or lord in theme["planets"])
    return {
        "active_house": active_house,
        "lord_of_year": lord,
        "activated": activated,
        "score": 2 if activated else 0,
    }


def _solar_support(theme: dict[str, Any], solar_return: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    planets = solar_return.get("planets", {}) or {}
    angles = solar_return.get("angles", {}) or {}
    for name, data in {**planets, **angles}.items():
        house = _safe_int(data.get("house"))
        if name in theme["planets"] or name in theme["angles"] or house in theme["houses"]:
            rows.append({"point": name, "formatted": data.get("formatted"), "house": house, "score": 1})
    return rows[:10]


def _predictive_support(theme: dict[str, Any], natal_book: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not _usable(row):
            continue
        match = _theme_match_score(theme, natal_book, row)
        if match > 0:
            item = dict(row)
            item["theme_match_score"] = match
            item["confirmation_weight"] = _row_weight(row)
            out.append(item)
    out.sort(key=lambda x: (-x.get("confirmation_weight", 0), -x.get("theme_match_score", 0), x.get("orb", 99)))
    return out[:10]


def _lunar_support(theme: dict[str, Any], natal_book: dict[str, Any], lunar_returns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Lunar returns are treated as timing triggers, not proof. For now keep them as generic monthly triggers.
    if not lunar_returns:
        return []
    return [{"method": row.get("method"), "exact_utc": row.get("exact_utc"), "orb": row.get("orb"), "trigger_role": "monthly_timing_only"} for row in lunar_returns[:6]]


def _status(score: float, counts: dict[str, int]) -> str:
    has_natal = counts.get("natal", 0) > 0
    predictive_layers = sum(1 for key in ["annual", "solar", "progression", "solar_arc", "transit"] if counts.get(key, 0) > 0)
    if has_natal and predictive_layers >= 3 and score >= 8:
        return "strong"
    if has_natal and predictive_layers >= 2 and score >= 5:
        return "moderate"
    if has_natal and predictive_layers >= 1 and score >= 3:
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
        solar_support = _solar_support(theme, solar_return)
        progression_support = _predictive_support(theme, natal_book, progressions)
        solar_arc_support = _predictive_support(theme, natal_book, solar_arc)
        transit_timing = _predictive_support(theme, natal_book, transits)
        lunar_triggers = _lunar_support(theme, natal_book, lunars)

        counts = {
            "natal": len(natal_basis),
            "annual": 1 if annual_activation.get("activated") else 0,
            "solar": len(solar_support),
            "progression": len(progression_support),
            "solar_arc": len(solar_arc_support),
            "transit": len(transit_timing),
            "lunar": len(lunar_triggers),
        }
        score = 0.0
        score += min(3, len(natal_basis)) * 1.5
        score += annual_activation.get("score", 0)
        score += min(2, len(solar_support)) * 1.0
        score += sum(row.get("confirmation_weight", 0) for row in progression_support[:3])
        score += sum(row.get("confirmation_weight", 0) for row in solar_arc_support[:3])
        score += min(3, sum(row.get("confirmation_weight", 0) for row in transit_timing[:5]))
        # Lunar trigger is timing only, deliberately low weight.
        score += 0.5 if lunar_triggers and (progression_support or solar_arc_support or transit_timing) else 0

        matrix[theme_key] = {
            "label": theme["label"],
            "status": _status(score, counts),
            "confirmation_score": round(score, 2),
            "layer_counts": counts,
            "natal_basis": natal_basis,
            "annual_activation": annual_activation,
            "solar_return_support": solar_support,
            "progression_support": progression_support,
            "solar_arc_support": solar_arc_support,
            "transit_timing": transit_timing,
            "lunar_triggers": lunar_triggers,
            "interpretation_permission": "allowed" if _status(score, counts) in {"strong", "moderate"} else "caution_or_do_not_claim_event",
        }

    ranked = sorted(matrix.items(), key=lambda kv: kv[1]["confirmation_score"], reverse=True)
    return {
        "rules": {
            "strong": "Natal basis + at least three predictive layers + high score.",
            "moderate": "Natal basis + at least two predictive layers.",
            "weak": "Natal basis + one predictive layer; can be mentioned cautiously.",
            "insufficient": "Do not claim a concrete event. Context only.",
            "transit_rule": "Transits time the event; they are not enough without natal/profection/solar/progression/solar arc support.",
        },
        "ranked_themes": [{"theme": key, "label": value["label"], "status": value["status"], "confirmation_score": value["confirmation_score"]} for key, value in ranked],
        "themes": matrix,
    }
