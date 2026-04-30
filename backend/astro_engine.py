from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any

import pytz
import swisseph as swe
from fastapi import HTTPException
from geopy.geocoders import Nominatim
from pydantic import BaseModel
from timezonefinder import TimezoneFinder


class NatalCalculationRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    calculation_date: str | None = None
    house_system: str = "P"
    zodiac: str = "tropical"


SIGNS_SR = ["Ovan", "Bik", "Blizanci", "Rak", "Lav", "Devica", "Vaga", "Škorpion", "Strelac", "Jarac", "Vodolija", "Ribe"]

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
    "Lilit": swe.MEAN_APOG,
}

OPTIONAL_PLANETS = {"Hiron": getattr(swe, "CHIRON", None)}

CORE_PLANET_NAMES = ["Sunce", "Mesec", "Merkur", "Venera", "Mars", "Jupiter", "Saturn", "Uran", "Neptun", "Pluton", "Severni čvor", "Južni čvor", "Lilit", "Hiron"]
ANGLE_NAMES = ["ASC", "DSC", "MC", "IC", "Vertex"]
ANGLE_HOUSES = {"ASC": 1, "DSC": 7, "MC": 10, "IC": 4}

ASPECTS = [
    ("konjunkcija", 0, 8),
    ("opozicija", 180, 8),
    ("trigon", 120, 6),
    ("kvadrat", 90, 6),
    ("sekstil", 60, 4),
    ("polukvadrat", 45, 2),
    ("seskvikvadrat", 135, 2),
    ("kvinkunks", 150, 2),
    ("polisekstil", 30, 2),
]

FIXED_STARS = {
    "Regulus": 150.0,
    "Spica": 203.0,
    "Algol": 56.0,
    "Antares": 249.0,
    "Aldebaran": 69.0,
    "Fomalhaut": 333.0,
    "Sirius": 103.0,
    "Arcturus": 203.0,
    "Vega": 285.0,
    "Deneb Algedi": 323.0,
}

FIRDARIA_DAY = [("Sunce", 10), ("Venera", 8), ("Merkur", 13), ("Mesec", 9), ("Saturn", 11), ("Jupiter", 12), ("Mars", 7)]
FIRDARIA_NIGHT = [("Mesec", 9), ("Saturn", 11), ("Jupiter", 12), ("Mars", 7), ("Sunce", 10), ("Venera", 8), ("Merkur", 13)]


def _parse_date(date_text: str) -> tuple[int, int, int]:
    text = date_text.strip().replace("/", ".").replace("-", ".")
    parts = [p for p in text.split(".") if p]
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="birth_date must be DD.MM.YYYY")
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    return year, month, day


def _parse_time(time_text: str) -> tuple[int, int, int]:
    text = time_text.strip().replace("h", ":").replace(".", ":")
    parts = [p for p in text.split(":") if p != ""]
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="birth_time must be HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return hour, minute, second


def _today_date() -> tuple[int, int, int]:
    now = datetime.utcnow()
    return now.year, now.month, now.day


def _deg_norm(value: float) -> float:
    return value % 360.0


def _angle_diff(a: float, b: float) -> float:
    diff = abs(_deg_norm(a) - _deg_norm(b)) % 360
    return 360 - diff if diff > 180 else diff


def _midpoint(a: float, b: float) -> float:
    a, b = _deg_norm(a), _deg_norm(b)
    if abs(a - b) > 180:
        if a < b:
            a += 360
        else:
            b += 360
    return _deg_norm((a + b) / 2)


def _sign_info(lon: float) -> dict[str, Any]:
    lon = _deg_norm(lon)
    sign_index = int(lon // 30)
    deg_in_sign = lon % 30
    deg = int(deg_in_sign)
    minutes_float = (deg_in_sign - deg) * 60
    minute = int(minutes_float)
    second = int(round((minutes_float - minute) * 60))
    if second == 60:
        minute += 1
        second = 0
    if minute == 60:
        deg += 1
        minute = 0
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


def _geo_place(place: str) -> dict[str, Any]:
    geolocator = Nominatim(user_agent="astro_aries_studio")
    try:
        location = geolocator.geocode(place, timeout=10)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Geocoding failed.", "error": str(exc)}) from exc
    if not location:
        raise HTTPException(status_code=404, detail=f"Place not found: {place}")
    return {"input": place, "name": location.address, "latitude": float(location.latitude), "longitude": float(location.longitude)}


def _timezone_for(lat: float, lon: float) -> str:
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=lat, lng=lon) or tf.closest_timezone_at(lat=lat, lng=lon)
    if not tz_name:
        raise HTTPException(status_code=404, detail="Timezone not found for coordinates.")
    return tz_name


def _local_to_utc(year: int, month: int, day: int, hour: int, minute: int, second: int, tz_name: str) -> dict[str, Any]:
    tz = pytz.timezone(tz_name)
    naive = datetime(year, month, day, hour, minute, second)
    local_dt = tz.localize(naive, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    offset_hours = local_dt.utcoffset().total_seconds() / 3600 if local_dt.utcoffset() else 0
    return {
        "local_datetime": local_dt.isoformat(),
        "utc_datetime": utc_dt.isoformat(),
        "utc_year": utc_dt.year,
        "utc_month": utc_dt.month,
        "utc_day": utc_dt.day,
        "utc_hour_decimal": utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600,
        "utc_offset_hours": offset_hours,
        "timezone": tz_name,
    }


def _house_for_lon(lon: float, cusps: list[float]) -> int:
    lon = _deg_norm(lon)
    c = [_deg_norm(x) for x in cusps]
    for i in range(12):
        start, end = c[i], c[(i + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return i + 1
        else:
            if lon >= start or lon < end:
                return i + 1
    return 12


def _calc_planet(jd_ut: float, planet_id: int) -> dict[str, Any]:
    flags = swe.FLG_MOSEPH | swe.FLG_SPEED | swe.FLG_EQUATORIAL
    ecl_flags = swe.FLG_MOSEPH | swe.FLG_SPEED
    ecl, _ = swe.calc_ut(jd_ut, planet_id, ecl_flags)
    eq, _ = swe.calc_ut(jd_ut, planet_id, flags)
    lon = _deg_norm(ecl[0])
    return {"longitude": lon, "latitude": ecl[1], "speed": ecl[3], "declination": eq[1], "retrograde": ecl[3] < 0}


def _aspects(points: dict[str, dict[str, Any]], label_a: str | None = None, label_b: str | None = None) -> list[dict[str, Any]]:
    names = list(points.keys())
    rows: list[dict[str, Any]] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if "longitude" not in points[a] or "longitude" not in points[b]:
                continue
            diff = _angle_diff(points[a]["longitude"], points[b]["longitude"])
            for aspect_name, angle, orb in ASPECTS:
                delta = abs(diff - angle)
                if delta <= orb:
                    rows.append({"point_a": a, "point_b": b, "group_a": label_a, "group_b": label_b, "aspect": aspect_name, "angle": angle, "orb": round(delta, 4), "exactness": "tight" if delta <= 1 else "normal"})
                    break
    rows.sort(key=lambda x: x["orb"])
    return rows


def _cross_aspects(a_points: dict[str, dict[str, Any]], b_points: dict[str, dict[str, Any]], group_a: str, group_b: str) -> list[dict[str, Any]]:
    rows = []
    for a_name, a_value in a_points.items():
        for b_name, b_value in b_points.items():
            if "longitude" not in a_value or "longitude" not in b_value:
                continue
            diff = _angle_diff(a_value["longitude"], b_value["longitude"])
            for aspect_name, angle, orb in ASPECTS:
                delta = abs(diff - angle)
                if delta <= orb:
                    rows.append({"point_a": a_name, "point_b": b_name, "group_a": group_a, "group_b": group_b, "aspect": aspect_name, "angle": angle, "orb": round(delta, 4), "exactness": "tight" if delta <= 1 else "normal"})
                    break
    rows.sort(key=lambda x: x["orb"])
    return rows


def _lot(name: str, lon: float, cusps: list[float]) -> dict[str, Any]:
    info = _sign_info(lon)
    info.update({"name": name, "house": _house_for_lon(lon, cusps)})
    return info


def _arabic_lots(angles: dict[str, Any], planets: dict[str, dict[str, Any]], cusps: list[float], sect: str) -> dict[str, Any]:
    asc = angles["ASC"]["longitude"]
    dsc = angles["DSC"]["longitude"]
    sun = planets["Sunce"]["longitude"]
    moon = planets["Mesec"]["longitude"]
    venus = planets["Venera"]["longitude"]
    mercury = planets["Merkur"]["longitude"]
    mars = planets["Mars"]["longitude"]
    jupiter = planets["Jupiter"]["longitude"]
    lilith = planets.get("Lilit", {}).get("longitude", venus)
    dsc_ruler = planets.get(angles["DSC"]["ruler"], {}).get("longitude", dsc)
    day = sect == "day"
    lots = {
        "Pars Fortunae": asc + moon - sun if day else asc + sun - moon,
        "Pars Spiritus": asc + sun - moon if day else asc + moon - sun,
        "Lot of Eros": asc + venus - lilith,
        "Lot of Marriage": asc + dsc_ruler - venus,
        "Lot of Necessity": asc + mercury - moon,
        "Lot of Courage": asc + mars - sun,
        "Lot of Victory": asc + jupiter - sun,
    }
    return {name: _lot(name, lon, cusps) for name, lon in lots.items()}


def _midpoints(angles: dict[str, Any], planets: dict[str, dict[str, Any]], cusps: list[float]) -> dict[str, Any]:
    pairs = {
        "Sunce/Mesec": ("Sunce", "Mesec"),
        "Jupiter/MC": ("Jupiter", "MC"),
        "Saturn/MC": ("Saturn", "MC"),
        "Venera/Jupiter": ("Venera", "Jupiter"),
        "Mars/Saturn": ("Mars", "Saturn"),
    }
    vals: dict[str, Any] = {}
    for name, (a, b) in pairs.items():
        lon_a = planets[a]["longitude"] if a in planets else angles[a]["longitude"]
        lon_b = planets[b]["longitude"] if b in planets else angles[b]["longitude"]
        info = _sign_info(_midpoint(lon_a, lon_b))
        info.update({"name": name, "house": _house_for_lon(info["longitude"], cusps)})
        vals[name] = info
    return vals


def _antiscia(lon: float) -> dict[str, Any]:
    antiscia = _deg_norm(180 - lon)
    contra = _deg_norm(360 - lon)
    return {"antiscia": _sign_info(antiscia), "contra_antiscia": _sign_info(contra)}


def _dodekatemoria(lon: float) -> dict[str, Any]:
    sign_start = int(_deg_norm(lon) // 30) * 30
    deg_in_sign = _deg_norm(lon) - sign_start
    return _sign_info(sign_start + deg_in_sign * 12)


def _fixed_star_hits(points: dict[str, dict[str, Any]], orb: float = 1.0) -> list[dict[str, Any]]:
    hits = []
    for point_name, point in points.items():
        lon = point.get("longitude")
        if lon is None:
            continue
        for star, star_lon in FIXED_STARS.items():
            delta = _angle_diff(lon, star_lon)
            if delta <= orb:
                hits.append({"point": point_name, "fixed_star": star, "star_position": _sign_info(star_lon), "orb": round(delta, 4)})
    hits.sort(key=lambda x: x["orb"])
    return hits


def _sect(sun_lon: float, cusps: list[float]) -> dict[str, Any]:
    sun_house = _house_for_lon(sun_lon, cusps)
    is_day = sun_house in {7, 8, 9, 10, 11, 12}
    return {"sect": "day" if is_day else "night", "sun_house": sun_house, "rule": "Sunce iznad horizonta = dnevna karta; ispod horizonta = noćna karta"}


def _profection(year: int, month: int, day: int, calc_date: tuple[int, int, int], houses: list[dict[str, Any]]) -> dict[str, Any]:
    cy, cm, cd = calc_date
    age = cy - year - ((cm, cd) < (month, day))
    active_house = (age % 12) + 1
    cusp = houses[active_house - 1]
    return {"age": age, "active_house": active_house, "house_sign": cusp["sign"], "lord_of_year": cusp["ruler"]}


def _firdaria(year: int, month: int, day: int, sect: str, calc_date: tuple[int, int, int]) -> dict[str, Any]:
    cy, cm, cd = calc_date
    age = cy - year - ((cm, cd) < (month, day))
    sequence = FIRDARIA_DAY if sect == "day" else FIRDARIA_NIGHT
    cursor = 0
    for planet, years in sequence:
        if cursor <= age < cursor + years:
            return {"age": age, "sect": sect, "period_lord": planet, "period_age_start": cursor, "period_age_end": cursor + years, "years_in_period": age - cursor}
        cursor += years
    return {"age": age, "sect": sect, "period_lord": "post-classical-cycle", "period_age_start": cursor, "period_age_end": None, "years_in_period": None}


def _moon_phase_angle(jd_ut: float) -> float:
    sun = _calc_planet(jd_ut, swe.SUN)["longitude"]
    moon = _calc_planet(jd_ut, swe.MOON)["longitude"]
    return _deg_norm(moon - sun)


def _syzygy(jd_ut: float, cusps: list[float]) -> dict[str, Any]:
    best = None
    for i in range(1, 240):
        jd = jd_ut - i * 0.25
        phase = _moon_phase_angle(jd)
        target = 0 if phase < 90 or phase > 270 else 180
        distance = min(abs(phase - target), 360 - abs(phase - target))
        if best is None or distance < best["distance"]:
            best = {"jd": jd, "target": target, "distance": distance}
    if not best:
        return {}
    refined = best
    for j in range(-24, 25):
        jd = best["jd"] + j * (0.25 / 24)
        phase = _moon_phase_angle(jd)
        target = best["target"]
        distance = min(abs(phase - target), 360 - abs(phase - target))
        if distance < refined["distance"]:
            refined = {"jd": jd, "target": target, "distance": distance}
    moon_lon = _calc_planet(refined["jd"], swe.MOON)["longitude"]
    dt = swe.revjul(refined["jd"], swe.GREG_CAL)
    info = _sign_info(moon_lon)
    info.update({"type": "Mlad Mesec" if refined["target"] == 0 else "Pun Mesec", "julian_day_ut": round(refined["jd"], 8), "utc_tuple": dt, "house": _house_for_lon(moon_lon, cusps), "phase_orb": round(refined["distance"], 4)})
    return info


def _enrich_points(points: dict[str, dict[str, Any]], cusps: list[float]) -> dict[str, dict[str, Any]]:
    enriched = {}
    for name, point in points.items():
        if not point or "longitude" not in point:
            continue
        row = dict(point)
        row["antiscia"] = _antiscia(point["longitude"])
        row["dodekatemoria"] = _dodekatemoria(point["longitude"])
        if "declination" in row:
            row["out_of_bounds"] = abs(row["declination"]) > 23.433333
        if "house" not in row:
            row["house"] = _house_for_lon(row["longitude"], cusps)
        enriched[name] = row
    return enriched


def _fix_angle_houses(angles: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    fixed = dict(angles)
    for angle_name, house in ANGLE_HOUSES.items():
        if angle_name in fixed:
            fixed[angle_name]["house"] = house
            fixed[angle_name]["house_assignment_rule"] = "Angular point fixed by definition, not recalculated as floating point within Placidus cusps."
    return fixed


def _quality_warnings(request: NatalCalculationRequest, planets: dict[str, Any]) -> list[str]:
    warnings = []
    if "Hiron" not in planets:
        warnings.append("Hiron nije izračunat u ovom okruženju; tretira se kao opcionalna tačka i ne blokira proračun.")
    warnings.append("Fiksne zvezde trenutno koriste internu aproksimativnu tropikalnu tabelu; sledeća verzija treba da doda precesiju/epohu za profesionalni završni proračun.")
    if not request.birth_time:
        warnings.append("Bez tačnog vremena nema pouzdanih kuća, ASC/MC i lotova.")
    return warnings


def _build_aspect_sets(planets: dict[str, Any], angles: dict[str, Any], lots: dict[str, Any], midpoints: dict[str, Any]) -> dict[str, Any]:
    clean_angles = {k: v for k, v in angles.items() if k in ANGLE_NAMES and isinstance(v, dict)}
    return {
        "planet_aspects": _aspects(planets, "planet", "planet"),
        "angle_aspects": _cross_aspects(clean_angles, planets, "angle", "planet"),
        "lot_aspects": _cross_aspects(lots, {**planets, **clean_angles}, "lot", "natal_point"),
        "midpoint_aspects": _cross_aspects(midpoints, {**planets, **clean_angles}, "midpoint", "natal_point"),
    }


def _book_of_data(result: dict[str, Any]) -> dict[str, Any]:
    angles = result["angles"]
    planets = result["planets"]
    core = {
        "ASC": angles.get("ASC", {}).get("formatted"),
        "MC": angles.get("MC", {}).get("formatted"),
        "Sunce": planets.get("Sunce", {}).get("formatted"),
        "Mesec": planets.get("Mesec", {}).get("formatted"),
        "sect": result.get("sect", {}).get("sect"),
        "profection_house": result.get("profections", {}).get("active_house"),
        "lord_of_year": result.get("profections", {}).get("lord_of_year"),
    }
    return {
        "core_natal": core,
        "input": result["input"],
        "place": result["place"],
        "time": result["time"],
        "settings": result["settings"],
        "angles": result["angles"],
        "houses": result["houses"],
        "planets": result["planets"],
        "arabic_lots": result["arabic_lots"],
        "midpoints": result["midpoints"],
        "syzygy": result["syzygy"],
        "sect": result["sect"],
        "profections": result["profections"],
        "firdaria": result["firdaria"],
        "fixed_star_hits": result["fixed_star_hits"],
        "aspect_sets": result["aspect_sets"],
        "quality_warnings": result["quality_warnings"],
    }


def calculate_natal(request: NatalCalculationRequest) -> dict[str, Any]:
    year, month, day = _parse_date(request.birth_date)
    hour, minute, second = _parse_time(request.birth_time)
    calc_date = _parse_date(request.calculation_date) if request.calculation_date else _today_date()

    ephe_path = os.getenv("SWISS_EPHE_PATH") or "/usr/share/ephe"
    swe.set_ephe_path(ephe_path)

    place = _geo_place(request.birth_place)
    tz_name = _timezone_for(place["latitude"], place["longitude"])
    time_data = _local_to_utc(year, month, day, hour, minute, second, tz_name)
    jd_ut = swe.julday(time_data["utc_year"], time_data["utc_month"], time_data["utc_day"], time_data["utc_hour_decimal"], swe.GREG_CAL)

    try:
        cusps_tuple, ascmc_tuple = swe.houses_ex(jd_ut, place["latitude"], place["longitude"], request.house_system.encode("ascii"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "House calculation failed.", "error": str(exc)}) from exc

    cusps = list(cusps_tuple[:12])
    houses = []
    for idx, cusp in enumerate(cusps, start=1):
        item = _sign_info(cusp)
        item["house"] = idx
        houses.append(item)

    angles = {
        "ASC": _sign_info(ascmc_tuple[0]),
        "MC": _sign_info(ascmc_tuple[1]),
        "DSC": _sign_info(ascmc_tuple[0] + 180),
        "IC": _sign_info(ascmc_tuple[1] + 180),
        "ARMC": round(ascmc_tuple[2], 6),
        "Vertex": _sign_info(ascmc_tuple[3]) if len(ascmc_tuple) > 3 else None,
    }

    planet_rows: dict[str, dict[str, Any]] = {}
    all_planets = dict(PLANETS)
    for name, planet_id in OPTIONAL_PLANETS.items():
        if planet_id is not None:
            all_planets[name] = planet_id

    for name, planet_id in all_planets.items():
        try:
            calc = _calc_planet(jd_ut, planet_id)
        except Exception:
            continue
        info = _sign_info(calc["longitude"])
        info.update({"name": name, "latitude": round(calc["latitude"], 6), "declination": round(calc["declination"], 6), "speed": round(calc["speed"], 8), "retrograde": calc["retrograde"], "house": _house_for_lon(calc["longitude"], cusps)})
        planet_rows[name] = info

    if "Severni čvor" in planet_rows:
        sn = _sign_info(planet_rows["Severni čvor"]["longitude"] + 180)
        sn.update({"name": "Južni čvor", "house": _house_for_lon(sn["longitude"], cusps)})
        planet_rows["Južni čvor"] = sn

    sect_data = _sect(planet_rows["Sunce"]["longitude"], cusps)
    angles_enriched = _fix_angle_houses(_enrich_points({k: v for k, v in angles.items() if isinstance(v, dict)}, cusps))
    planet_rows = _enrich_points(planet_rows, cusps)
    lots = _arabic_lots(angles_enriched, planet_rows, cusps, sect_data["sect"])
    lots = _enrich_points(lots, cusps)
    midpoints = _midpoints(angles_enriched, planet_rows, cusps)
    midpoints = _enrich_points(midpoints, cusps)

    clean_angles = {k: v for k, v in angles_enriched.items() if k in ANGLE_NAMES and isinstance(v, dict)}
    all_points = {**planet_rows, **{f"Lot: {k}": v for k, v in lots.items()}, **{f"Midpoint: {k}": v for k, v in midpoints.items()}, **clean_angles}
    aspect_sets = _build_aspect_sets(planet_rows, clean_angles, lots, midpoints)

    result = {
        "success": True,
        "schema": "ASTRO_ARIES_BOOK_OF_DATA_V1",
        "engine": "Swiss Ephemeris / pyswisseph",
        "settings": {
            "zodiac": "tropical",
            "houses": "Placidus" if request.house_system == "P" else request.house_system,
            "node": "True Node + South Node derived",
            "lilith": "Mean Apogee",
            "time_rule": "local birth time converted to UTC using place timezone before Swiss Ephemeris",
            "ephemeris_path": ephe_path,
            "calculation_date": request.calculation_date or datetime.utcnow().strftime("%d.%m.%Y"),
        },
        "input": request.model_dump(),
        "place": place,
        "time": time_data,
        "julian_day_ut": round(jd_ut, 8),
        "angles": angles_enriched,
        "houses": houses,
        "planets": planet_rows,
        "arabic_lots": lots,
        "midpoints": midpoints,
        "sect": sect_data,
        "fixed_star_hits": _fixed_star_hits(all_points, 1.0),
        "syzygy": _syzygy(jd_ut, cusps),
        "profections": _profection(year, month, day, calc_date, houses),
        "firdaria": _firdaria(year, month, day, sect_data["sect"], calc_date),
        "aspect_sets": aspect_sets,
        "quality_warnings": [],
        "calculation_only_note": "This endpoint returns calculation data only, not interpretation.",
    }
    result["quality_warnings"] = _quality_warnings(request, planet_rows)
    result["book_of_data"] = _book_of_data(result)
    return result
