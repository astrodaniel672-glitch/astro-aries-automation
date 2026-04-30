from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytz
import swisseph as swe
from fastapi import HTTPException
from pydantic import BaseModel

try:
    from backend.astro_dignity import enhance_with_dignities
    from backend.astro_engine import NatalCalculationRequest, calculate_natal
    from backend.astro_rules import classify_aspect, proof_book
except ModuleNotFoundError:
    from astro_dignity import enhance_with_dignities
    from astro_engine import NatalCalculationRequest, calculate_natal
    from astro_rules import classify_aspect, proof_book


class PredictiveCalculationRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    prediction_start: str | None = None
    prediction_end: str | None = None
    calculation_date: str | None = None
    house_system: str = "P"
    zodiac: str = "tropical"


SIGNS_SR = ["Ovan", "Bik", "Blizanci", "Rak", "Lav", "Devica", "Vaga", "Škorpion", "Strelac", "Jarac", "Vodolija", "Ribe"]
RULERS = {
    "Ovan": "Mars", "Bik": "Venera", "Blizanci": "Merkur", "Rak": "Mesec", "Lav": "Sunce", "Devica": "Merkur",
    "Vaga": "Venera", "Škorpion": "Mars", "Strelac": "Jupiter", "Jarac": "Saturn", "Vodolija": "Saturn", "Ribe": "Jupiter",
}
PLANETS = {
    "Sunce": swe.SUN,
    "Mesec": swe.MOON,
    "Merkur": swe.MERCURY,
    "Venera": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uran": swe.URANUS,
    "Neptun": swe.NEPTUNE,
    "Pluton": swe.PLUTO,
    "Severni čvor": swe.TRUE_NODE,
}
FAST_TRANSIT_PLANETS = ["Sunce", "Mesec", "Merkur", "Venera", "Mars"]
SLOW_TRANSIT_PLANETS = ["Jupiter", "Saturn", "Uran", "Neptun", "Pluton", "Severni čvor"]
TRANSIT_PLANETS = FAST_TRANSIT_PLANETS + SLOW_TRANSIT_PLANETS
ASPECT_ANGLES = {
    "konjunkcija": 0,
    "opozicija": 180,
    "trigon": 120,
    "kvadrat": 90,
    "sekstil": 60,
    "kvinkunks": 150,
}
TRANSIT_MAX_ORB = {
    "Sunce": 1.0,
    "Mesec": 1.0,
    "Merkur": 1.0,
    "Venera": 1.0,
    "Mars": 1.5,
    "Jupiter": 2.0,
    "Saturn": 2.0,
    "Uran": 1.5,
    "Neptun": 1.5,
    "Pluton": 1.5,
    "Severni čvor": 1.5,
}
NATAL_TARGETS = ["Sunce", "Mesec", "Merkur", "Venera", "Mars", "Jupiter", "Saturn", "Uran", "Neptun", "Pluton", "Severni čvor", "Južni čvor", "Lilit"]
ANGLE_TARGETS = ["ASC", "DSC", "MC", "IC"]


def _parse_date(text: str) -> tuple[int, int, int]:
    parts = [p for p in text.strip().replace("/", ".").replace("-", ".").split(".") if p]
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Date must be DD.MM.YYYY")
    return int(parts[2]), int(parts[1]), int(parts[0])


def _parse_time(text: str) -> tuple[int, int, int]:
    parts = [p for p in text.strip().replace("h", ":").replace(".", ":").split(":") if p != ""]
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Time must be HH:MM")
    return int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0


def _date_to_utc_midday(date_text: str) -> datetime:
    y, m, d = _parse_date(date_text)
    return datetime(y, m, d, 12, 0, tzinfo=timezone.utc)


def _default_period(request: PredictiveCalculationRequest) -> tuple[datetime, datetime]:
    if request.prediction_start:
        start = _date_to_utc_midday(request.prediction_start)
    elif request.calculation_date:
        start = _date_to_utc_midday(request.calculation_date)
    else:
        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, now.day, 12, 0, tzinfo=timezone.utc)
    if request.prediction_end:
        end = _date_to_utc_midday(request.prediction_end)
    else:
        end = start + timedelta(days=365)
    if end <= start:
        raise HTTPException(status_code=400, detail="prediction_end must be after prediction_start")
    return start, end


def _jd(dt: datetime) -> float:
    utc = dt.astimezone(timezone.utc)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600, swe.GREG_CAL)


def _revjul_iso(jd_ut: float) -> str:
    y, m, d, h = swe.revjul(jd_ut, swe.GREG_CAL)
    hour = int(h)
    minute = int((h - hour) * 60)
    second = int(round((((h - hour) * 60) - minute) * 60))
    return datetime(y, m, d, hour, minute, min(second, 59), tzinfo=timezone.utc).isoformat()


def _norm(x: float) -> float:
    return x % 360.0


def _diff(a: float, b: float) -> float:
    v = abs(_norm(a) - _norm(b)) % 360
    return 360 - v if v > 180 else v


def _signed_delta_to_aspect(transit_lon: float, natal_lon: float, angle: float) -> float:
    raw = (_norm(transit_lon - natal_lon) - angle + 540) % 360 - 180
    return raw


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


def _calc_lon(jd_ut: float, planet_id: int) -> dict[str, Any]:
    res, _ = swe.calc_ut(jd_ut, planet_id, swe.FLG_MOSEPH | swe.FLG_SPEED)
    info = _sign_info(res[0])
    info.update({"speed": round(res[3], 8), "retrograde": res[3] < 0})
    return info


def _planet_positions(jd_ut: float, names: list[str] | None = None) -> dict[str, Any]:
    names = names or list(PLANETS.keys())
    data: dict[str, Any] = {}
    for name in names:
        if name in PLANETS:
            data[name] = _calc_lon(jd_ut, PLANETS[name])
    if "Severni čvor" in data:
        sn = _sign_info(data["Severni čvor"]["longitude"] + 180)
        sn.update({"speed": data["Severni čvor"].get("speed"), "retrograde": data["Severni čvor"].get("retrograde")})
        data["Južni čvor"] = sn
    return data


def _natal_targets(natal: dict[str, Any]) -> dict[str, Any]:
    points: dict[str, Any] = {}
    for name in NATAL_TARGETS:
        if name in natal.get("planets", {}):
            points[name] = natal["planets"][name]
    for name in ANGLE_TARGETS:
        if name in natal.get("angles", {}):
            points[name] = natal["angles"][name]
    return points


def _aspect_row(method: str, moving_name: str, moving_lon: float, natal_name: str, natal_lon: float, aspect_name: str, orb: float, exact_jd: float | None = None) -> dict[str, Any]:
    row = {
        "method": method,
        "point_a": moving_name,
        "point_b": natal_name,
        "group_a": "predictive",
        "group_b": "natal_point",
        "aspect": aspect_name,
        "angle": ASPECT_ANGLES[aspect_name],
        "orb": round(orb, 4),
        "exactness": "tight" if orb <= 1 else "normal",
        "moving_position": _sign_info(moving_lon),
        "natal_position": _sign_info(natal_lon),
    }
    if exact_jd:
        row["exact_julian_day_ut"] = round(exact_jd, 8)
        row["exact_utc"] = _revjul_iso(exact_jd)
    classified = classify_aspect(row)
    # Override: predictive contacts are proof only if within strict predictive orb.
    if classified.get("orb") <= 0.1667:
        classified["evidence_weight"] = "primary_evidence"
        classified["orb_class"] = "exact"
        classified["usable_as_proof"] = True
    elif classified.get("orb") <= 1.0:
        classified["evidence_weight"] = "strong_evidence"
        classified["orb_class"] = "tight"
        classified["usable_as_proof"] = True
    elif classified.get("orb") <= 2.0 and aspect_name in {"konjunkcija", "opozicija", "kvadrat", "kvinkunks"}:
        classified["evidence_weight"] = "supporting_evidence"
        classified["orb_class"] = "valid"
        classified["usable_as_proof"] = True
    else:
        classified["evidence_weight"] = "background_only"
        classified["usable_as_proof"] = False
        if classified.get("orb") > 2.0:
            classified["orb_class"] = "background"
    classified["hard_event_candidate"] = bool(classified.get("usable_as_proof") and aspect_name in {"konjunkcija", "opozicija", "kvadrat", "kvinkunks"})
    return classified


def _contacts_at_jd(method: str, moving: dict[str, Any], natal_points: dict[str, Any], max_orb_default: float = 2.0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for moving_name, moving_data in moving.items():
        moving_lon = moving_data.get("longitude")
        if moving_lon is None:
            continue
        max_orb = TRANSIT_MAX_ORB.get(moving_name, max_orb_default)
        for natal_name, natal_data in natal_points.items():
            natal_lon = natal_data.get("longitude")
            if natal_lon is None:
                continue
            for aspect_name, angle in ASPECT_ANGLES.items():
                orb = abs(_signed_delta_to_aspect(moving_lon, natal_lon, angle))
                if orb <= max_orb:
                    rows.append(_aspect_row(method, moving_name, moving_lon, natal_name, natal_lon, aspect_name, orb))
    rows.sort(key=lambda x: (not x.get("usable_as_proof", False), float(x.get("orb") or 99)))
    return rows


def _find_transit_hits(start: datetime, end: datetime, natal_points: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    total_days = (end.date() - start.date()).days
    # Slow planets every 2 days, fast planets every day. Exact refinement is approximate but useful for workflow.
    for planet in TRANSIT_PLANETS:
        step = 1 if planet in FAST_TRANSIT_PLANETS else 2
        max_orb = TRANSIT_MAX_ORB.get(planet, 1.5)
        for natal_name, natal_data in natal_points.items():
            natal_lon = natal_data.get("longitude")
            if natal_lon is None:
                continue
            for aspect_name, angle in ASPECT_ANGLES.items():
                previous = None
                previous_jd = None
                closest: dict[str, Any] | None = None
                for day in range(0, total_days + 1, step):
                    jd_now = _jd(start + timedelta(days=day))
                    lon = _calc_lon(jd_now, PLANETS[planet])["longitude"]
                    delta = _signed_delta_to_aspect(lon, natal_lon, angle)
                    abs_delta = abs(delta)
                    if abs_delta <= max_orb:
                        if closest is None or abs_delta < closest["orb"]:
                            closest = {"jd": jd_now, "lon": lon, "orb": abs_delta}
                    if previous is not None and delta == 0 or (previous is not None and previous * delta < 0):
                        # Linear approximation of exact moment between previous and current sample.
                        frac = abs(previous) / (abs(previous) + abs(delta)) if (abs(previous) + abs(delta)) else 0
                        exact_jd = previous_jd + (jd_now - previous_jd) * frac
                        exact_lon = _calc_lon(exact_jd, PLANETS[planet])["longitude"]
                        exact_orb = abs(_signed_delta_to_aspect(exact_lon, natal_lon, angle))
                        if exact_orb <= max_orb:
                            hits.append(_aspect_row("transit_exact_window", planet, exact_lon, natal_name, natal_lon, aspect_name, exact_orb, exact_jd))
                    previous = delta
                    previous_jd = jd_now
                if closest and closest["orb"] <= min(max_orb, 1.0):
                    row = _aspect_row("transit_window_closest", planet, closest["lon"], natal_name, natal_lon, aspect_name, closest["orb"], closest["jd"])
                    # Avoid duplicates near exact hits.
                    if not any(h["point_a"] == row["point_a"] and h["point_b"] == row["point_b"] and h["aspect"] == row["aspect"] and abs(h.get("exact_julian_day_ut", 0) - row.get("exact_julian_day_ut", 999999)) < 1 for h in hits):
                        hits.append(row)
    hits.sort(key=lambda x: (x.get("exact_utc") or "", float(x.get("orb") or 99)))
    return hits[:300]


def _solar_return(natal: dict[str, Any], birth_year: int, target_year: int, place_lat: float, place_lon: float, house_system: str) -> dict[str, Any]:
    natal_sun = natal["planets"]["Sunce"]["longitude"]
    # Search around birthday in target year.
    start = datetime(target_year, max(1, int(natal["input"]["birth_date"].split('.')[1])), 1, 0, tzinfo=timezone.utc)
    jd_start = _jd(start) - 40
    best = {"jd": jd_start, "orb": 999.0, "lon": 0.0}
    for i in range(0, 160 * 4):
        jd_now = jd_start + i * 0.25
        sun_lon = _calc_lon(jd_now, swe.SUN)["longitude"]
        orb = _diff(sun_lon, natal_sun)
        if orb < best["orb"]:
            best = {"jd": jd_now, "orb": orb, "lon": sun_lon}
    # Refine around best quarter-day.
    refined = dict(best)
    for j in range(-48, 49):
        jd_now = best["jd"] + j * (0.25 / 48)
        sun_lon = _calc_lon(jd_now, swe.SUN)["longitude"]
        orb = _diff(sun_lon, natal_sun)
        if orb < refined["orb"]:
            refined = {"jd": jd_now, "orb": orb, "lon": sun_lon}
    try:
        cusps, ascmc = swe.houses_ex(refined["jd"], place_lat, place_lon, house_system.encode("ascii"))
        sr_angles = {"ASC": _sign_info(ascmc[0]), "MC": _sign_info(ascmc[1]), "DSC": _sign_info(ascmc[0] + 180), "IC": _sign_info(ascmc[1] + 180)}
        sr_houses = [_sign_info(cusps[i]) | {"house": i + 1} for i in range(12)]
    except Exception as exc:
        sr_angles = {}
        sr_houses = []
    sr_planets = _planet_positions(refined["jd"])
    return {
        "method": "solar_return",
        "target_year": target_year,
        "exact_utc": _revjul_iso(refined["jd"]),
        "julian_day_ut": round(refined["jd"], 8),
        "sun_return_orb": round(refined["orb"], 6),
        "angles": sr_angles,
        "houses": sr_houses,
        "planets": sr_planets,
    }


def _secondary_progressions(natal: dict[str, Any], birth_dt_utc: datetime, calc_dt: datetime, natal_points: dict[str, Any]) -> dict[str, Any]:
    age_days = (calc_dt.date() - birth_dt_utc.date()).days
    years = age_days / 365.2425
    progressed_dt = birth_dt_utc + timedelta(days=years)
    progressed_jd = _jd(progressed_dt)
    planets = _planet_positions(progressed_jd, ["Sunce", "Mesec", "Merkur", "Venera", "Mars", "Jupiter", "Saturn"])
    contacts = _contacts_at_jd("secondary_progression_to_natal", planets, natal_points, 2.0)
    return {
        "method": "secondary_progressions_day_for_year",
        "calculation_utc": calc_dt.isoformat(),
        "progressed_utc_symbolic": progressed_dt.isoformat(),
        "progressed_julian_day_ut": round(progressed_jd, 8),
        "planets": planets,
        "contacts_to_natal": contacts,
    }


def _solar_arc(natal: dict[str, Any], birth_dt_utc: datetime, calc_dt: datetime, natal_points: dict[str, Any]) -> dict[str, Any]:
    age_days = (calc_dt.date() - birth_dt_utc.date()).days
    years = age_days / 365.2425
    progressed_dt = birth_dt_utc + timedelta(days=years)
    progressed_sun = _calc_lon(_jd(progressed_dt), swe.SUN)["longitude"]
    natal_sun = natal["planets"]["Sunce"]["longitude"]
    arc = (progressed_sun - natal_sun) % 360
    directed: dict[str, Any] = {}
    for name, data in natal.get("planets", {}).items():
        if name in NATAL_TARGETS and "longitude" in data:
            directed[name] = _sign_info(data["longitude"] + arc)
    for name, data in natal.get("angles", {}).items():
        if name in ANGLE_TARGETS and "longitude" in data:
            directed[name] = _sign_info(data["longitude"] + arc)
    contacts = _contacts_at_jd("solar_arc_to_natal", directed, natal_points, 2.0)
    return {
        "method": "solar_arc_directions",
        "calculation_utc": calc_dt.isoformat(),
        "arc_degrees": round(arc, 6),
        "directed_points": directed,
        "contacts_to_natal": contacts,
    }


def _lunar_returns(start: datetime, end: datetime, natal: dict[str, Any]) -> list[dict[str, Any]]:
    natal_moon = natal["planets"]["Mesec"]["longitude"]
    rows: list[dict[str, Any]] = []
    jd_start = _jd(start)
    jd_end = _jd(end)
    jd_now = jd_start
    previous_delta = None
    previous_jd = None
    while jd_now <= jd_end:
        moon_lon = _calc_lon(jd_now, swe.MOON)["longitude"]
        delta = ((moon_lon - natal_moon + 540) % 360) - 180
        if previous_delta is not None and previous_delta * delta < 0:
            frac = abs(previous_delta) / (abs(previous_delta) + abs(delta))
            exact_jd = previous_jd + (jd_now - previous_jd) * frac
            exact_moon = _calc_lon(exact_jd, swe.MOON)["longitude"]
            rows.append({"method": "lunar_return", "exact_utc": _revjul_iso(exact_jd), "julian_day_ut": round(exact_jd, 8), "moon_position": _sign_info(exact_moon), "orb": round(_diff(exact_moon, natal_moon), 4)})
        previous_delta = delta
        previous_jd = jd_now
        jd_now += 1.0
    return rows[:24]


def _birth_utc_from_natal(natal: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(natal["time"]["utc_datetime"].replace("Z", "+00:00"))


def _prediction_proof_book(predictive: dict[str, Any]) -> dict[str, Any]:
    sets: dict[str, list[dict[str, Any]]] = {
        "transits": predictive.get("transits_to_natal", {}).get("window_hits", []),
        "secondary_progressions": predictive.get("secondary_progressions", {}).get("contacts_to_natal", []),
        "solar_arc": predictive.get("solar_arc", {}).get("contacts_to_natal", []),
    }
    return proof_book(sets)


def calculate_predictive(request: PredictiveCalculationRequest) -> dict[str, Any]:
    natal_request = NatalCalculationRequest(
        birth_date=request.birth_date,
        birth_time=request.birth_time,
        birth_place=request.birth_place,
        calculation_date=request.calculation_date or request.prediction_start,
        house_system=request.house_system,
        zodiac=request.zodiac,
    )
    natal = enhance_with_dignities(calculate_natal(natal_request))
    start, end = _default_period(request)
    calc_dt = start
    birth_dt_utc = _birth_utc_from_natal(natal)
    natal_points = _natal_targets(natal)
    target_year = start.year

    transits_now = _planet_positions(_jd(start), TRANSIT_PLANETS)
    transit_contacts_now = _contacts_at_jd("transit_to_natal_at_period_start", transits_now, natal_points, 2.0)
    window_hits = _find_transit_hits(start, end, natal_points)
    sr = _solar_return(natal, birth_dt_utc.year, target_year, natal["place"]["latitude"], natal["place"]["longitude"], request.house_system)
    progressions = _secondary_progressions(natal, birth_dt_utc, calc_dt, natal_points)
    solar_arc = _solar_arc(natal, birth_dt_utc, calc_dt, natal_points)
    lunars = _lunar_returns(start, min(end, start + timedelta(days=370)), natal)

    result = {
        "success": True,
        "schema": "ASTRO_ARIES_PREDICTIVE_BOOK_OF_DATA_V1",
        "calculation_only_note": "This endpoint returns predictive calculation data only, not interpretation.",
        "settings": {
            "prediction_start": start.isoformat(),
            "prediction_end": end.isoformat(),
            "rule": "Natal promise first; profection/solar/progression/solar arc confirm; transits/lunations time the manifestation.",
            "proof_rule": "Only contacts marked usable_as_proof may be used as evidence. Background-only contacts are context, not proof.",
        },
        "natal_book_of_data": natal.get("book_of_data"),
        "annual_profection": natal.get("profections"),
        "solar_return": sr,
        "secondary_progressions": progressions,
        "solar_arc": solar_arc,
        "transits_to_natal": {
            "period_start_positions": transits_now,
            "contacts_at_period_start": transit_contacts_now,
            "window_hits": window_hits,
        },
        "lunar_returns": lunars,
        "quality_warnings": [
            "Prediktivni modul je calculation-only. Ne daje tumačenje bez posebnog AI interpretativnog sloja.",
            "Tranziti su timing sloj; ne smeju biti jedini dokaz bez natalne/progresivne/solar/profekcijske potvrde.",
            "Exact transit window koristi numeričku aproksimaciju kroz dnevne/dvodnevne korake; za finalni hard-event modul kasnije se može dodati finija pretraga po satu.",
            "Lunacije/eclipses još nisu kompletno implementirane; lunar returns su uključeni kao mesečni okidač.",
        ],
    }
    result["prediction_proof_book"] = _prediction_proof_book(result)
    return result
