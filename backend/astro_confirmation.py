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
STRUCTURAL_SOURCE_LIMITS = {"progression": 2, "solar_arc": 2, "transit": 1}
WEAK_NATAL_SOURCES = {"arabic_lots", "midpoints"}
NARRATIVE_FOCUS_MAX_THEMES = 4


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


def _row_key(row: dict[str, Any]) -> str:
    return "|".join(str(row.get(key) or "") for key in ("method", "point_a", "point_b", "aspect", "orb", "exact_utc", "date"))


def _point_sources(natal_book: dict[str, Any], point: str) -> set[str]:
    point = _point_name(point)
    sources: set[str] = set()
    source_map = {
        "planets": natal_book.get("planets", {}) or {},
        "angles": natal_book.get("angles", {}) or {},
        "arabic_lots": natal_book.get("arabic_lots", {}) or {},
        "midpoints": natal_book.get("midpoints", {}) or {},
    }
    for source_name, source in source_map.items():
        if point in source:
            sources.add(source_name)
    if point in {"ASC", "DSC", "MC", "IC"}:
        sources.add("angles")
    return sources


def _is_core_point(natal_book: dict[str, Any], point: str) -> bool:
    sources = _point_sources(natal_book, point)
    return bool(sources & {"planets", "angles"}) or _point_name(point) in {"ASC", "DSC", "MC", "IC"}


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


def _theme_match_detail(theme: dict[str, Any], natal_book: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    points = {_point_name(row.get("point_a")), _point_name(row.get("point_b"))}
    points.discard("")
    houses: set[int] = set()
    core_house_points: set[str] = set()
    weak_house_points: set[str] = set()
    point_sources: dict[str, list[str]] = {}

    for point in points:
        sources = _point_sources(natal_book, point)
        if sources:
            point_sources[point] = sorted(sources)
        point_houses = _houses_for_natal_point(natal_book, point)
        houses |= point_houses
        if point_houses & theme["houses"]:
            if _is_core_point(natal_book, point):
                core_house_points.add(point)
            elif sources & WEAK_NATAL_SOURCES:
                weak_house_points.add(point)

    direct_houses = houses & theme["houses"]
    direct_planets = points & theme["planets"]
    direct_angles = points & theme["angles"]
    has_angle_match = bool(direct_angles)
    has_core_house_match = bool(core_house_points)
    has_weak_house_match = bool(weak_house_points)
    has_direct_planet_match = bool(direct_planets)

    primary_theme_match = has_angle_match or has_core_house_match or (has_direct_planet_match and bool(direct_houses))

    score = 0.0
    if has_core_house_match:
        score += 2.5
    elif has_weak_house_match:
        score += 0.75
    if has_direct_planet_match:
        score += 1.0 if direct_houses else 0.45
    if has_angle_match:
        score += 2.5
    if row.get("hard_event_candidate") and primary_theme_match:
        score += 0.5

    if not primary_theme_match and has_weak_house_match:
        score = min(score, 1.0)
    elif not primary_theme_match:
        score = min(score, 0.75)

    return {
        "theme_match_score": round(score, 2),
        "primary_theme_match": primary_theme_match,
        "direct_houses": sorted(direct_houses),
        "direct_planets": sorted(direct_planets),
        "direct_angles": sorted(direct_angles),
        "core_house_points": sorted(core_house_points),
        "weak_house_points": sorted(weak_house_points),
        "point_sources": point_sources,
    }


def _theme_match_score(theme: dict[str, Any], natal_book: dict[str, Any], row: dict[str, Any]) -> float:
    return float(_theme_match_detail(theme, natal_book, row)["theme_match_score"])


def _usable(row: dict[str, Any]) -> bool:
    return bool(row.get("usable_as_proof")) or row.get("evidence_weight") in {"primary_evidence", "strong_evidence", "supporting_evidence"}


def _is_fast_timing_only(row: dict[str, Any]) -> bool:
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
            detail = _theme_match_detail(theme, natal_book, row)
            match = float(detail["theme_match_score"])
            if match > 0:
                item = dict(row)
                item.update(detail)
                item["natal_basis_strength"] = "core" if detail["primary_theme_match"] else "secondary_context"
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
            score = 1 if direct_house else 0.25
            rows.append({"point": name, "formatted": data.get("formatted"), "house": house, "score": score, "support_type": "house" if direct_house else "planet_only"})
    rows.sort(key=lambda x: -float(x.get("score") or 0))
    return rows[:6]


def _source_theme_allowances(natal_book: dict[str, Any], rows: list[dict[str, Any]], source: str) -> dict[str, dict[str, dict[str, Any]]]:
    per_theme: dict[str, dict[str, dict[str, Any]]] = {key: {} for key in THEMES}
    max_themes = STRUCTURAL_SOURCE_LIMITS.get(source, 2)
    for row in rows or []:
        if not _usable(row):
            continue
        candidates: list[tuple[str, dict[str, Any]]] = []
        for theme_key, theme in THEMES.items():
            detail = _theme_match_detail(theme, natal_book, row)
            if not detail["primary_theme_match"]:
                continue
            if float(detail["theme_match_score"]) <= 0:
                continue
            candidates.append((theme_key, detail))
        candidates.sort(key=lambda item: (-float(item[1].get("theme_match_score") or 0), -_row_weight(row), float(row.get("orb") or 99), item[0]))
        for theme_key, detail in candidates[:max_themes]:
            per_theme.setdefault(theme_key, {})[_row_key(row)] = detail
    return per_theme


def _predictive_support(
    theme: dict[str, Any],
    natal_book: dict[str, Any],
    rows: list[dict[str, Any]],
    source: str,
    allowed_details: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not _usable(row):
            continue
        key = _row_key(row)
        detail = (allowed_details or {}).get(key)
        if detail is None:
            detail = _theme_match_detail(theme, natal_book, row)
            if source in {"progression", "solar_arc", "transit"} and not detail["primary_theme_match"]:
                continue
        match = float(detail["theme_match_score"])
        if match > 0:
            item = dict(row)
            item.update(detail)
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
    return sum(1 for key in ["annual", "solar", "progression", "solar_arc"] if counts.get(key, 0) > 0)


def _status(score: float, counts: dict[str, int]) -> str:
    has_core_natal = counts.get("core_natal", 0) > 0
    structural_layers = _structural_layer_count(counts)
    has_primary_direction = counts.get("primary_progression", 0) > 0 or counts.get("primary_solar_arc", 0) > 0
    has_annual_or_solar = counts.get("annual", 0) > 0 or counts.get("solar", 0) > 0
    if has_core_natal and has_annual_or_solar and has_primary_direction and structural_layers >= 3 and score >= 9.5:
        return "strong"
    if has_core_natal and (has_primary_direction or has_annual_or_solar) and score >= 4.0:
        return "weak"
    return "insufficient"


def _capped_score(raw_score: float, status: str, counts: dict[str, int]) -> float:
    structural_layers = _structural_layer_count(counts)
    has_annual_or_solar = counts.get("annual", 0) > 0 or counts.get("solar", 0) > 0
    has_primary_direction = counts.get("primary_progression", 0) > 0 or counts.get("primary_solar_arc", 0) > 0
    if status == "strong":
        return raw_score
    if status == "weak":
        cap = 5.75
        if not has_annual_or_solar:
            cap = min(cap, 5.25)
        if not has_primary_direction:
            cap = min(cap, 4.75)
        if structural_layers < 2:
            cap = min(cap, 4.5)
        return min(raw_score, cap)
    return min(raw_score, 2.75)


def _interpretation_permission(status: str) -> str:
    if status == "strong":
        return "allowed"
    if status == "weak":
        return "caution_only"
    return "blocked"


def _astrological_narrative_classification(theme_key: str, row: dict[str, Any]) -> dict[str, Any]:
    counts = row.get("layer_counts", {}) or {}
    score = float(row.get("confirmation_score") or 0)
    status = row.get("status")
    structural_layers = _structural_layer_count(counts)
    has_core_natal = counts.get("core_natal", 0) > 0
    has_annual = counts.get("annual", 0) > 0
    has_solar = counts.get("solar", 0) > 0
    has_direction = counts.get("primary_progression", 0) > 0 or counts.get("primary_solar_arc", 0) > 0
    has_timing = counts.get("transit", 0) > 0 or counts.get("fast_timing", 0) > 0 or counts.get("lunar", 0) > 0

    if status == "strong":
        level = "hard_event_allowed"
        narrative_mode = "concrete_event_allowed"
        can_claim = True
    elif has_core_natal and score >= 5.25 and structural_layers >= 2 and (has_annual or has_solar or has_direction):
        level = "main_narrative_focus"
        narrative_mode = "main_theme_without_event_claim"
        can_claim = False
    elif status == "weak":
        level = "supporting_tendency"
        narrative_mode = "brief_tendency_only"
        can_claim = False
    else:
        level = "blocked"
        narrative_mode = "do_not_interpret_as_prediction"
        can_claim = False

    return {
        "theme": theme_key,
        "label": row.get("label"),
        "status": status,
        "confirmation_score": row.get("confirmation_score"),
        "raw_confirmation_score": row.get("raw_confirmation_score"),
        "astrological_level": level,
        "narrative_mode": narrative_mode,
        "can_claim_concrete_event": can_claim,
        "must_be_cautious": not can_claim,
        "world_rule_basis": {
            "natal_promise_required": has_core_natal,
            "annual_or_solar_activation": bool(has_annual or has_solar),
            "progression_or_solar_arc_direction": has_direction,
            "timing_only_present": has_timing,
            "structural_layer_count": structural_layers,
        },
        "wording_rule": (
            "Može se formulisati kao konkretan događaj samo ako je hard_event_allowed."
            if can_claim
            else "Formulisati kao naglašenu temu, proces, pritisak, potrebu za odlukom ili tendenciju; bez tvrdnje da će se događaj sigurno desiti."
        ),
    }


def _build_astrological_theme_groups(matrix: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    classified = [_astrological_narrative_classification(theme_key, row) for theme_key, row in matrix.items()]
    hard_allowed = [item for item in classified if item["astrological_level"] == "hard_event_allowed"]
    narrative_focus = [item for item in classified if item["astrological_level"] == "main_narrative_focus"]
    supporting = [item for item in classified if item["astrological_level"] == "supporting_tendency"]
    blocked = [item for item in classified if item["astrological_level"] == "blocked"]

    hard_allowed.sort(key=lambda item: (-float(item.get("confirmation_score") or 0), item["theme"]))
    narrative_focus.sort(key=lambda item: (-float(item.get("confirmation_score") or 0), item["theme"]))
    supporting.sort(key=lambda item: (-float(item.get("confirmation_score") or 0), item["theme"]))
    blocked.sort(key=lambda item: item["theme"])

    main_focus = narrative_focus[:NARRATIVE_FOCUS_MAX_THEMES]
    remaining_supporting = narrative_focus[NARRATIVE_FOCUS_MAX_THEMES:] + supporting
    remaining_supporting.sort(key=lambda item: (-float(item.get("confirmation_score") or 0), item["theme"]))

    return {
        "hard_event_theme_blocks": hard_allowed,
        "narrative_focus_theme_blocks": main_focus,
        "supporting_tendency_theme_blocks": remaining_supporting,
        "blocked_theme_blocks": blocked,
    }


def build_confirmation_matrix(result: dict[str, Any]) -> dict[str, Any]:
    natal_book = result.get("natal_book_of_data") or {}
    natal_proof = result.get("natal_proof_book") or (natal_book.get("proof_book") if isinstance(natal_book, dict) else {}) or {}
    annual = result.get("annual_profection") or {}
    solar_return = result.get("solar_return") or {}
    progressions = (result.get("secondary_progressions") or {}).get("contacts_to_natal", [])
    solar_arc = (result.get("solar_arc") or {}).get("contacts_to_natal", [])
    transits = (result.get("transits_to_natal") or {}).get("window_hits", [])
    lunars = result.get("lunar_returns") or []

    progression_allowances = _source_theme_allowances(natal_book, progressions, "progression")
    solar_arc_allowances = _source_theme_allowances(natal_book, solar_arc, "solar_arc")
    transit_allowances = _source_theme_allowances(natal_book, transits, "transit")

    matrix: dict[str, Any] = {}
    for theme_key, theme in THEMES.items():
        natal_basis = _collect_natal_basis(theme, natal_book, natal_proof)
        annual_activation = _annual_activation(theme, annual)
        solar_support_all = _solar_support(theme, solar_return)
        solar_structural = [x for x in solar_support_all if x.get("support_type") == "house"]
        progression_support = _predictive_support(theme, natal_book, progressions, "progression", progression_allowances.get(theme_key, {}))
        solar_arc_support = _predictive_support(theme, natal_book, solar_arc, "solar_arc", solar_arc_allowances.get(theme_key, {}))
        transit_timing = _predictive_support(theme, natal_book, transits, "transit", transit_allowances.get(theme_key, {}))
        lunar_triggers = _lunar_support(theme, natal_book, lunars)

        core_natal = [row for row in natal_basis if row.get("natal_basis_strength") == "core"]
        primary_progression = [row for row in progression_support if row.get("primary_theme_match")]
        primary_solar_arc = [row for row in solar_arc_support if row.get("primary_theme_match")]
        counts = {
            "natal": len(natal_basis),
            "core_natal": len(core_natal),
            "secondary_natal": len(natal_basis) - len(core_natal),
            "annual": 1 if annual_activation.get("activated") else 0,
            "solar": len(solar_structural),
            "solar_planet_only": len([x for x in solar_support_all if x.get("support_type") == "planet_only"]),
            "progression": len(progression_support),
            "primary_progression": len(primary_progression),
            "solar_arc": len(solar_arc_support),
            "primary_solar_arc": len(primary_solar_arc),
            "transit": len([x for x in transit_timing if not x.get("timing_only")]),
            "fast_timing": len([x for x in transit_timing if x.get("timing_only")]),
            "lunar": len(lunar_triggers),
        }

        raw_score = 0.0
        raw_score += min(2, len(core_natal)) * 1.25
        raw_score += min(2, len(natal_basis) - len(core_natal)) * 0.35
        raw_score += annual_activation.get("score", 0)
        raw_score += sum(float(row.get("score") or 0) for row in solar_support_all[:4])
        raw_score += min(3.5, sum(row.get("confirmation_weight", 0) for row in progression_support[:2]))
        raw_score += min(4.0, sum(row.get("confirmation_weight", 0) for row in solar_arc_support[:2]))
        raw_score += min(1.0, sum(row.get("confirmation_weight", 0) for row in transit_timing[:4]))
        raw_score += 0.25 if lunar_triggers and (progression_support or solar_arc_support) else 0

        status = _status(raw_score, counts)
        visible_score = _capped_score(raw_score, status, counts)
        matrix[theme_key] = {
            "label": theme["label"],
            "status": status,
            "confirmation_score": round(visible_score, 2),
            "raw_confirmation_score": round(raw_score, 2),
            "layer_counts": counts,
            "natal_basis": natal_basis,
            "annual_activation": annual_activation,
            "solar_return_support": solar_support_all,
            "progression_support": progression_support,
            "solar_arc_support": solar_arc_support,
            "transit_timing": transit_timing,
            "lunar_triggers": lunar_triggers,
            "interpretation_permission": _interpretation_permission(status),
        }

    ranked = sorted(matrix.items(), key=lambda kv: kv[1]["confirmation_score"], reverse=True)
    theme_groups = _build_astrological_theme_groups(matrix)
    return {
        "rules": {
            "method_hierarchy": "World-standard predictive hierarchy: natal promise first, annual profection and solar return as yearly frame, secondary progressions/solar arc as development/direction, transits and lunar returns as timing only.",
            "hard_event": "Concrete event wording requires core natal promise + annual/solar activation + primary progression or solar arc + at least 3 structural layers. Transits may time, not create the event.",
            "narrative_focus": "A theme may become main narrative focus with core natal promise plus at least two structural layers, but it must be written as a process/tendency unless hard_event is met.",
            "supporting_tendency": "Supporting themes can be mentioned briefly as tendencies, background pressure or timing sensitivity only.",
            "blocked": "Insufficient themes must not be turned into predictions.",
            "moderate_policy": "Moderate is intentionally not emitted as an event status until the interpretive payload builder separates moderate from allowed concrete claims.",
            "primary_theme_match_rule": "A contact must directly touch a theme house, angle, or theme planet. Generic contacts are not allowed to confirm many unrelated themes.",
            "contact_reuse_rule": "One progression/solar-arc contact can feed only its best direct themes, usually no more than two. Transit contacts are restricted to one timing theme.",
            "transit_rule": "Fast transits and lunar returns are timing only. They cannot lift a theme to strong by themselves.",
            "score_cap_rule": "The public confirmation_score is capped by status/layer completeness; raw_confirmation_score is kept for debugging.",
            "solar_rule": "Solar return planet-only support without house placement is weak support, not a full structural layer.",
            "lot_midpoint_rule": "Arabic lots and midpoints are secondary natal context. They do not carry the same confirmation weight as planets or angles.",
        },
        "ranked_themes": [{"theme": key, "label": value["label"], "status": value["status"], "confirmation_score": value["confirmation_score"]} for key, value in ranked],
        "astrological_theme_groups": theme_groups,
        "narrative_focus_theme_blocks": theme_groups["narrative_focus_theme_blocks"],
        "supporting_tendency_theme_blocks": theme_groups["supporting_tendency_theme_blocks"],
        "hard_event_theme_blocks": theme_groups["hard_event_theme_blocks"],
        "themes": matrix,
    }
