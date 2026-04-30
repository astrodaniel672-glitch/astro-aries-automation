from __future__ import annotations

from typing import Any

EXACT_ORB_DEG = 0.1667  # 0°10'
TIGHT_ORB_DEG = 1.0
HARD_EVENT_VALID_ORB_DEG = 2.0

ASPECT_NATURE = {
    "konjunkcija": "neutral_powerful",
    "opozicija": "hard",
    "kvadrat": "hard",
    "trigon": "soft",
    "sekstil": "soft",
    "kvinkunks": "adjustment",
    "polukvadrat": "minor_hard",
    "seskvikvadrat": "minor_hard",
    "polisekstil": "minor_soft",
}

BASE_ORBS = {
    "konjunkcija": 8.0,
    "opozicija": 8.0,
    "trigon": 6.0,
    "kvadrat": 6.0,
    "sekstil": 4.0,
    "kvinkunks": 2.0,
    "polukvadrat": 2.0,
    "seskvikvadrat": 2.0,
    "polisekstil": 2.0,
}

GROUP_MAX_ORB = {
    "planet:planet": {
        "konjunkcija": 8.0,
        "opozicija": 8.0,
        "trigon": 6.0,
        "kvadrat": 6.0,
        "sekstil": 4.0,
        "kvinkunks": 2.0,
        "polukvadrat": 2.0,
        "seskvikvadrat": 2.0,
        "polisekstil": 2.0,
    },
    "angle:planet": {
        "konjunkcija": 6.0,
        "opozicija": 6.0,
        "trigon": 4.0,
        "kvadrat": 4.0,
        "sekstil": 3.0,
        "kvinkunks": 2.0,
        "polukvadrat": 1.5,
        "seskvikvadrat": 1.5,
        "polisekstil": 1.5,
    },
    "lot:natal_point": {
        "konjunkcija": 2.0,
        "opozicija": 2.0,
        "trigon": 1.5,
        "kvadrat": 1.5,
        "sekstil": 1.0,
        "kvinkunks": 1.0,
        "polukvadrat": 1.0,
        "seskvikvadrat": 1.0,
        "polisekstil": 1.0,
    },
    "midpoint:natal_point": {
        "konjunkcija": 1.5,
        "opozicija": 1.5,
        "trigon": 1.0,
        "kvadrat": 1.0,
        "sekstil": 1.0,
        "kvinkunks": 0.75,
        "polukvadrat": 0.75,
        "seskvikvadrat": 0.75,
        "polisekstil": 0.75,
    },
    "fixed_star:natal_point": {
        "konjunkcija": 1.0,
    },
}

HARD_ASPECTS = {"konjunkcija", "opozicija", "kvadrat", "polukvadrat", "seskvikvadrat", "kvinkunks"}
ANGLE_POINTS = {"ASC", "DSC", "MC", "IC"}
CORE_POINTS = {"Sunce", "Mesec", "Merkur", "Venera", "Mars", "Jupiter", "Saturn", "Uran", "Neptun", "Pluton", "Severni čvor", "Južni čvor", "Lilit"}


def _group_key(aspect: dict[str, Any]) -> str:
    group_a = aspect.get("group_a") or "planet"
    group_b = aspect.get("group_b") or "planet"
    return f"{group_a}:{group_b}"


def _allowed_orb(aspect: dict[str, Any]) -> float:
    aspect_name = aspect.get("aspect")
    group_key = _group_key(aspect)
    if group_key in GROUP_MAX_ORB:
        return GROUP_MAX_ORB[group_key].get(aspect_name, BASE_ORBS.get(aspect_name, 0.0))
    reverse_key = ":".join(group_key.split(":")[::-1])
    if reverse_key in GROUP_MAX_ORB:
        return GROUP_MAX_ORB[reverse_key].get(aspect_name, BASE_ORBS.get(aspect_name, 0.0))
    return BASE_ORBS.get(aspect_name, 0.0)


def _orb_class(orb: float, allowed: float) -> str:
    if orb <= EXACT_ORB_DEG:
        return "exact"
    if orb <= TIGHT_ORB_DEG:
        return "tight"
    if orb <= min(HARD_EVENT_VALID_ORB_DEG, allowed):
        return "valid"
    if orb <= allowed:
        return "background"
    return "discard"


def _evidence_weight(aspect: dict[str, Any], orb_class: str) -> str:
    aspect_name = aspect.get("aspect")
    point_a = aspect.get("point_a")
    point_b = aspect.get("point_b")
    group_key = _group_key(aspect)

    if orb_class == "discard":
        return "discard"
    if orb_class == "exact":
        return "primary_evidence"
    if orb_class == "tight":
        return "strong_evidence"
    if orb_class == "valid":
        if aspect_name in HARD_ASPECTS or group_key == "angle:planet":
            return "supporting_evidence"
        return "secondary_support"
    if orb_class == "background":
        return "background_only"
    return "background_only"


def _hard_event_candidate(aspect: dict[str, Any], orb_class: str) -> bool:
    aspect_name = aspect.get("aspect")
    if aspect_name not in HARD_ASPECTS:
        return False
    if orb_class not in {"exact", "tight", "valid"}:
        return False
    if float(aspect.get("orb") or 99) > HARD_EVENT_VALID_ORB_DEG:
        return False
    point_a = aspect.get("point_a")
    point_b = aspect.get("point_b")
    group_a = aspect.get("group_a")
    group_b = aspect.get("group_b")
    has_angle = point_a in ANGLE_POINTS or point_b in ANGLE_POINTS or group_a == "angle" or group_b == "angle"
    has_core = point_a in CORE_POINTS or point_b in CORE_POINTS
    return bool(has_angle or has_core)


def classify_aspect(aspect: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(aspect)
    orb = float(aspect.get("orb") or 0.0)
    allowed = _allowed_orb(aspect)
    orb_class = _orb_class(orb, allowed)
    enriched["allowed_orb"] = allowed
    enriched["orb_class"] = orb_class
    enriched["aspect_nature"] = ASPECT_NATURE.get(aspect.get("aspect"), "unknown")
    enriched["evidence_weight"] = _evidence_weight(aspect, orb_class)
    enriched["usable_as_proof"] = enriched["evidence_weight"] in {"primary_evidence", "strong_evidence", "supporting_evidence"}
    enriched["hard_event_candidate"] = _hard_event_candidate(aspect, orb_class)
    return enriched


def classify_aspect_sets(aspect_sets: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {name: [classify_aspect(row) for row in rows] for name, rows in (aspect_sets or {}).items()}


def proof_book(classified_sets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    primary: list[dict[str, Any]] = []
    strong: list[dict[str, Any]] = []
    supporting: list[dict[str, Any]] = []
    background: list[dict[str, Any]] = []
    discarded: list[dict[str, Any]] = []
    hard_events: list[dict[str, Any]] = []

    for set_name, rows in (classified_sets or {}).items():
        for row in rows:
            item = dict(row)
            item["aspect_set"] = set_name
            weight = item.get("evidence_weight")
            if weight == "primary_evidence":
                primary.append(item)
            elif weight == "strong_evidence":
                strong.append(item)
            elif weight == "supporting_evidence":
                supporting.append(item)
            elif weight == "discard":
                discarded.append(item)
            else:
                background.append(item)
            if item.get("hard_event_candidate"):
                hard_events.append(item)

    sort_key = lambda x: float(x.get("orb") or 99)
    for bucket in [primary, strong, supporting, background, discarded, hard_events]:
        bucket.sort(key=sort_key)

    return {
        "primary_evidence": primary,
        "strong_evidence": strong,
        "supporting_evidence": supporting,
        "background_only": background,
        "discarded_by_orb_rules": discarded,
        "hard_event_candidates": hard_events,
        "rules": {
            "exact_orb_deg": EXACT_ORB_DEG,
            "tight_orb_deg": TIGHT_ORB_DEG,
            "hard_event_valid_orb_deg": HARD_EVENT_VALID_ORB_DEG,
            "evidence_rule": "AI interpretation may use primary/strong/supporting as proof. Background aspects are context only. Discarded aspects must not be used as proof.",
        },
    }


def enhance_with_rules(result: dict[str, Any]) -> dict[str, Any]:
    aspect_sets = result.get("aspect_sets") or {}
    classified = classify_aspect_sets(aspect_sets)
    proof = proof_book(classified)

    result["aspect_sets"] = classified
    result["proof_book"] = proof

    if isinstance(result.get("book_of_data"), dict):
        result["book_of_data"]["aspect_sets"] = classified
        result["book_of_data"]["proof_book"] = proof

    warnings = result.setdefault("quality_warnings", [])
    warnings.append("Aspekti su klasifikovani kroz astro_rules: exact/tight/valid/background/discard. AI ne sme koristiti background/discard kao dokaz.")
    if isinstance(result.get("book_of_data"), dict):
        result["book_of_data"]["quality_warnings"] = result["quality_warnings"]
    return result
