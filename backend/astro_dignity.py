from __future__ import annotations

from typing import Any

CLASSICAL_PLANETS = ["Sunce", "Mesec", "Merkur", "Venera", "Mars", "Jupiter", "Saturn"]

RULERS = {
    "Ovan": "Mars",
    "Bik": "Venera",
    "Blizanci": "Merkur",
    "Rak": "Mesec",
    "Lav": "Sunce",
    "Devica": "Merkur",
    "Vaga": "Venera",
    "Škorpion": "Mars",
    "Strelac": "Jupiter",
    "Jarac": "Saturn",
    "Vodolija": "Saturn",
    "Ribe": "Jupiter",
}

SIGN_OPPOSITES = {
    "Ovan": "Vaga",
    "Bik": "Škorpion",
    "Blizanci": "Strelac",
    "Rak": "Jarac",
    "Lav": "Vodolija",
    "Devica": "Ribe",
    "Vaga": "Ovan",
    "Škorpion": "Bik",
    "Strelac": "Blizanci",
    "Jarac": "Rak",
    "Vodolija": "Lav",
    "Ribe": "Devica",
}
DOMICILES = {
    "Sunce": ["Lav"],
    "Mesec": ["Rak"],
    "Merkur": ["Blizanci", "Devica"],
    "Venera": ["Bik", "Vaga"],
    "Mars": ["Ovan", "Škorpion"],
    "Jupiter": ["Strelac", "Ribe"],
    "Saturn": ["Jarac", "Vodolija"],
}
EXALTATIONS = {
    "Sunce": "Ovan",
    "Mesec": "Bik",
    "Merkur": "Devica",
    "Venera": "Ribe",
    "Mars": "Jarac",
    "Jupiter": "Rak",
    "Saturn": "Vaga",
}
TRIPLICITY_BY_ELEMENT = {
    "fire": {"day": "Sunce", "night": "Jupiter", "participating": "Saturn"},
    "earth": {"day": "Venera", "night": "Mesec", "participating": "Mars"},
    "air": {"day": "Saturn", "night": "Merkur", "participating": "Jupiter"},
    "water": {"day": "Venera", "night": "Mars", "participating": "Mesec"},
}
SIGN_ELEMENT = {
    "Ovan": "fire",
    "Lav": "fire",
    "Strelac": "fire",
    "Bik": "earth",
    "Devica": "earth",
    "Jarac": "earth",
    "Blizanci": "air",
    "Vaga": "air",
    "Vodolija": "air",
    "Rak": "water",
    "Škorpion": "water",
    "Ribe": "water",
}
# Egyptian bounds/terms by sign. Each tuple is inclusive upper degree within sign.
EGYPTIAN_TERMS = {
    "Ovan": [(6, "Jupiter"), (14, "Venera"), (21, "Merkur"), (26, "Mars"), (30, "Saturn")],
    "Bik": [(8, "Venera"), (14, "Merkur"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],
    "Blizanci": [(6, "Merkur"), (12, "Jupiter"), (17, "Venera"), (24, "Mars"), (30, "Saturn")],
    "Rak": [(7, "Mars"), (13, "Venera"), (19, "Merkur"), (26, "Jupiter"), (30, "Saturn")],
    "Lav": [(6, "Jupiter"), (13, "Venera"), (19, "Saturn"), (25, "Merkur"), (30, "Mars")],
    "Devica": [(7, "Merkur"), (13, "Venera"), (17, "Jupiter"), (21, "Mars"), (30, "Saturn")],
    "Vaga": [(6, "Saturn"), (14, "Merkur"), (21, "Jupiter"), (28, "Venera"), (30, "Mars")],
    "Škorpion": [(7, "Mars"), (11, "Venera"), (19, "Merkur"), (24, "Jupiter"), (30, "Saturn")],
    "Strelac": [(12, "Jupiter"), (17, "Venera"), (21, "Merkur"), (26, "Saturn"), (30, "Mars")],
    "Jarac": [(7, "Merkur"), (14, "Jupiter"), (22, "Venera"), (26, "Saturn"), (30, "Mars")],
    "Vodolija": [(7, "Merkur"), (13, "Venera"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],
    "Ribe": [(12, "Venera"), (16, "Jupiter"), (19, "Merkur"), (28, "Mars"), (30, "Saturn")],
}
CHALDEAN_FACE_SEQUENCE = ["Mars", "Sunce", "Venera", "Merkur", "Mesec", "Saturn", "Jupiter"]
# Starts at 0 Aries with Mars and advances every 10 degrees through zodiac.
PLANET_NATURE = {
    "Sunce": "luminary",
    "Mesec": "luminary",
    "Merkur": "neutral",
    "Venera": "benefic",
    "Mars": "malefic",
    "Jupiter": "benefic",
    "Saturn": "malefic",
}
ANGULAR_HOUSES = {1, 4, 7, 10}
SUCCEDENT_HOUSES = {2, 5, 8, 11}
CADENT_HOUSES = {3, 6, 9, 12}


def _detriment_signs(planet: str) -> list[str]:
    return [SIGN_OPPOSITES[s] for s in DOMICILES.get(planet, [])]


def _fall_sign(planet: str) -> str | None:
    exalt = EXALTATIONS.get(planet)
    return SIGN_OPPOSITES.get(exalt) if exalt else None


def _term_ruler(sign: str, degree_in_sign: float) -> str | None:
    for upper, ruler in EGYPTIAN_TERMS.get(sign, []):
        if degree_in_sign < upper:
            return ruler
    return None


def _face_ruler(sign_index: int, degree_in_sign: float) -> str:
    decan_index = int(degree_in_sign // 10)
    global_decan = sign_index * 3 + min(decan_index, 2)
    return CHALDEAN_FACE_SEQUENCE[global_decan % len(CHALDEAN_FACE_SEQUENCE)]


def _triplicity(sign: str, sect: str) -> dict[str, Any]:
    element = SIGN_ELEMENT.get(sign)
    rulers = TRIPLICITY_BY_ELEMENT.get(element, {})
    return {
        "element": element,
        "sect_ruler": rulers.get("day" if sect == "day" else "night"),
        "participating_ruler": rulers.get("participating"),
        "all": rulers,
    }


def _essential_dignity(planet: str, data: dict[str, Any], sect: str) -> dict[str, Any]:
    sign = data.get("sign")
    degree = float(data.get("degree_in_sign") or 0)
    sign_index = int(data.get("sign_index") or 0)
    term = _term_ruler(sign, degree)
    face = _face_ruler(sign_index, degree)
    trip = _triplicity(sign, sect)
    score = 0
    reasons: list[str] = []

    if sign in DOMICILES.get(planet, []):
        score += 5
        reasons.append("domicile/sedište +5")
    if sign == EXALTATIONS.get(planet):
        score += 4
        reasons.append("exaltation/egzaltacija +4")
    if planet == trip.get("sect_ruler"):
        score += 3
        reasons.append("triplicity ruler by sect +3")
    elif planet == trip.get("participating_ruler"):
        score += 1
        reasons.append("participating triplicity ruler +1")
    if planet == term:
        score += 2
        reasons.append("Egyptian term/bound ruler +2")
    if planet == face:
        score += 1
        reasons.append("face/decan ruler +1")
    if sign in _detriment_signs(planet):
        score -= 5
        reasons.append("detriment/izgon -5")
    if sign == _fall_sign(planet):
        score -= 4
        reasons.append("fall/pad -4")

    return {
        "score": score,
        "reasons": reasons,
        "domicile_signs": DOMICILES.get(planet, []),
        "detriment_signs": _detriment_signs(planet),
        "exaltation_sign": EXALTATIONS.get(planet),
        "fall_sign": _fall_sign(planet),
        "triplicity": trip,
        "term_ruler": term,
        "face_ruler": face,
    }


def _accidental_dignity(planet: str, data: dict[str, Any], sun: dict[str, Any] | None) -> dict[str, Any]:
    house = int(data.get("house") or 0)
    retrograde = bool(data.get("retrograde"))
    score = 0
    reasons: list[str] = []

    if house in ANGULAR_HOUSES:
        score += 5
        reasons.append("angular house +5")
    elif house in SUCCEDENT_HOUSES:
        score += 2
        reasons.append("succedent house +2")
    elif house in CADENT_HOUSES:
        score -= 2
        reasons.append("cadent house -2")

    if retrograde:
        score -= 2
        reasons.append("retrograde -2")

    if planet not in {"Sunce", "Mesec"} and sun and "longitude" in sun and "longitude" in data:
        diff = abs(float(data["longitude"]) - float(sun["longitude"])) % 360
        if diff > 180:
            diff = 360 - diff
        if diff <= 8.5:
            score -= 5
            reasons.append(f"combust/spaljen od Sunca ({round(diff, 2)}°) -5")
        elif diff <= 17:
            score -= 2
            reasons.append(f"under beams/pod zracima Sunca ({round(diff, 2)}°) -2")

    if data.get("out_of_bounds"):
        score -= 1
        reasons.append("out of bounds -1")

    return {"score": score, "reasons": reasons}


def _condition_label(total: int) -> str:
    if total >= 8:
        return "very_strong"
    if total >= 4:
        return "strong"
    if total >= 1:
        return "mixed_positive"
    if total == 0:
        return "neutral_mixed"
    if total >= -4:
        return "challenged"
    return "very_challenged"


def _house_rulers(houses: list[dict[str, Any]]) -> dict[str, Any]:
    return {str(h.get("house")): {"sign": h.get("sign"), "ruler": h.get("ruler"), "cusp": h.get("formatted"), "longitude": h.get("longitude")} for h in houses}


def _dispositor_chain(planet: str, planets: dict[str, Any], max_steps: int = 12) -> dict[str, Any]:
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = planet
    for _ in range(max_steps):
        pdata = planets.get(current)
        if not pdata:
            return {"chain": chain, "terminal": None, "cycle": False, "note": f"No data for {current}"}
        sign = pdata.get("sign")
        dispositor = RULERS.get(sign)
        chain.append({"planet": current, "sign": sign, "house": pdata.get("house"), "dispositor": dispositor})
        if not dispositor:
            return {"chain": chain, "terminal": None, "cycle": False}
        if dispositor == current:
            return {"chain": chain, "terminal": current, "cycle": False, "terminal_type": "own_sign"}
        if dispositor in seen:
            chain.append({"planet": dispositor, "cycle_return": True})
            return {"chain": chain, "terminal": dispositor, "cycle": True, "terminal_type": "loop"}
        seen.add(current)
        current = dispositor
    return {"chain": chain, "terminal": current, "cycle": True, "terminal_type": "max_steps"}


def _planet_condition_summary(planet: str, dignity: dict[str, Any]) -> dict[str, Any]:
    essential = dignity["essential"]["score"]
    accidental = dignity["accidental"]["score"]
    total = dignity["total_score"]
    return {
        "planet": planet,
        "essential_score": essential,
        "accidental_score": accidental,
        "total_score": total,
        "condition": dignity["condition"],
        "nature": PLANET_NATURE.get(planet),
    }


def enhance_with_dignities(result: dict[str, Any]) -> dict[str, Any]:
    planets = result.get("planets", {}) or {}
    houses = result.get("houses", []) or []
    sect = (result.get("sect", {}) or {}).get("sect", "day")
    sun = planets.get("Sunce")

    dignities: dict[str, Any] = {}
    conditions: dict[str, Any] = {}
    chains: dict[str, Any] = {}

    for planet in CLASSICAL_PLANETS:
        pdata = planets.get(planet)
        if not pdata:
            continue
        essential = _essential_dignity(planet, pdata, sect)
        accidental = _accidental_dignity(planet, pdata, sun)
        total = essential["score"] + accidental["score"]
        dignities[planet] = {
            "planet": planet,
            "sign": pdata.get("sign"),
            "house": pdata.get("house"),
            "formatted": pdata.get("formatted"),
            "essential": essential,
            "accidental": accidental,
            "total_score": total,
            "condition": _condition_label(total),
        }
        conditions[planet] = _planet_condition_summary(planet, dignities[planet])
        chains[planet] = _dispositor_chain(planet, planets)

    result["dignities"] = {
        "system": "Classical dignity baseline: domicile, exaltation, triplicity by sect, Egyptian terms, Chaldean faces, detriment, fall + simple accidental dignity.",
        "planets": dignities,
    }
    result["planetary_condition"] = conditions
    result["dispositor_chains"] = chains
    result["house_rulers"] = _house_rulers(houses)

    if "book_of_data" in result and isinstance(result["book_of_data"], dict):
        result["book_of_data"]["dignities"] = result["dignities"]
        result["book_of_data"]["planetary_condition"] = result["planetary_condition"]
        result["book_of_data"]["dispositor_chains"] = result["dispositor_chains"]
        result["book_of_data"]["house_rulers"] = result["house_rulers"]

    warnings = result.setdefault("quality_warnings", [])
    warnings.append("Bonitet je proračunski baseline: za finalnu verziju moguće je dodatno fino podešavanje termina, sekte, helijačkih stanja i recepcija.")
    if "book_of_data" in result and isinstance(result["book_of_data"], dict):
        result["book_of_data"]["quality_warnings"] = result["quality_warnings"]
    return result
