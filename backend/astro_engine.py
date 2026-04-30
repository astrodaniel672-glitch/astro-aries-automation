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
    house_system: str = "P"
    zodiac: str = "tropical"


SIGNS_SR = [
    "Ovan",
    "Bik",
    "Blizanci",
    "Rak",
    "Lav",
    "Devica",
    "Vaga",
    "Škorpion",
    "Strelac",
    "Jarac",
    "Vodolija",
    "Ribe",
]

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

OPTIONAL_PLANETS = {
    "Hiron": getattr(swe, "CHIRON", None),
}

ASPECTS = [
    ("konjunkcija", 0, 8),
    ("opozicija", 180, 8),
    ("trigon", 120, 6),
    ("kvadrat", 90, 6),
    ("sekstil", 60, 4),
    ("kvinkunks", 150, 2),
]


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


def _deg_norm(value: float) -> float:
    return value % 360.0


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
    return {
        "longitude": round(lon, 6),
        "sign": SIGNS_SR[sign_index],
        "sign_index": sign_index,
        "degree_in_sign": round(deg_in_sign, 6),
        "degree": deg,
        "minute": minute,
        "second": second,
        "formatted": f"{deg}°{minute:02d}' {SIGNS_SR[sign_index]}",
    }


def _geo_place(place: str) -> dict[str, Any]:
    geolocator = Nominatim(user_agent="astro_aries_studio")
    try:
        location = geolocator.geocode(place, timeout=10)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Geocoding failed.", "error": str(exc)}) from exc
    if not location:
        raise HTTPException(status_code=404, detail=f"Place not found: {place}")
    return {
        "input": place,
        "name": location.address,
        "latitude": float(location.latitude),
        "longitude": float(location.longitude),
    }


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
        start = c[i]
        end = c[(i + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return i + 1
        else:
            if lon >= start or lon < end:
                return i + 1
    return 12


def _calc_planet(jd_ut: float, planet_id: int) -> tuple[float, float, bool]:
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _flag = swe.calc_ut(jd_ut, planet_id, flags)
    lon = _deg_norm(result[0])
    speed = result[3]
    return lon, speed, speed < 0


def _aspects(planets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    names = list(planets.keys())
    rows: list[dict[str, Any]] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            lon_a = planets[a]["longitude"]
            lon_b = planets[b]["longitude"]
            diff = abs(lon_a - lon_b) % 360
            if diff > 180:
                diff = 360 - diff
            for aspect_name, angle, orb in ASPECTS:
                delta = abs(diff - angle)
                if delta <= orb:
                    rows.append(
                        {
                            "planet_a": a,
                            "planet_b": b,
                            "aspect": aspect_name,
                            "angle": angle,
                            "orb": round(delta, 4),
                            "exactness": "tight" if delta <= 1 else "normal",
                        }
                    )
                    break
    rows.sort(key=lambda x: x["orb"])
    return rows


def calculate_natal(request: NatalCalculationRequest) -> dict[str, Any]:
    year, month, day = _parse_date(request.birth_date)
    hour, minute, second = _parse_time(request.birth_time)

    ephe_path = os.getenv("SWISS_EPHE_PATH")
    if ephe_path:
        swe.set_ephe_path(ephe_path)

    place = _geo_place(request.birth_place)
    tz_name = _timezone_for(place["latitude"], place["longitude"])
    time_data = _local_to_utc(year, month, day, hour, minute, second, tz_name)
    jd_ut = swe.julday(
        time_data["utc_year"],
        time_data["utc_month"],
        time_data["utc_day"],
        time_data["utc_hour_decimal"],
        swe.GREG_CAL,
    )

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
            lon, speed, retrograde = _calc_planet(jd_ut, planet_id)
        except Exception:
            continue
        info = _sign_info(lon)
        info.update(
            {
                "name": name,
                "speed": round(speed, 8),
                "retrograde": retrograde,
                "house": _house_for_lon(lon, cusps),
            }
        )
        planet_rows[name] = info

    result = {
        "success": True,
        "engine": "Swiss Ephemeris / pyswisseph",
        "settings": {
            "zodiac": "tropical",
            "houses": "Placidus" if request.house_system == "P" else request.house_system,
            "node": "True Node",
            "time_rule": "local birth time converted to UTC using place timezone",
        },
        "input": request.model_dump(),
        "place": place,
        "time": time_data,
        "julian_day_ut": round(jd_ut, 8),
        "angles": angles,
        "houses": houses,
        "planets": planet_rows,
        "aspects": _aspects(planet_rows),
    }
    return result
