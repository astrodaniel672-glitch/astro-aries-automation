from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel


class SectionEvidenceRequest(BaseModel):
    section_key: str
    natal_data: dict[str, Any]
    predictive_data: dict[str, Any] | None = None
    interpretation_payload: dict[str, Any] | None = None
    client_context: dict[str, Any] | None = None


SECTION_FOCUS_HINTS = {
    "identity_vitality": "ASC, vladar ASC, Sunce, Mesec, planete u 1, aspekti prema ASC/MC, dispozitori, dostojanstvo vladara ASC i svetala, Almuten ako postoji.",
    "money_values": "2. kuća, vladar 2, planete u 2, Venera, Jupiter, Fortuna, 8. kuća kao tuđ novac, aspekti vladara 2/8, dispozitor novca, relevantni lotovi/midpointi ako postoje.",
    "communication_learning": "3. kuća, vladar 3, Merkur, planete u 3, aspekti Merkura, dispozitor Merkura, odnos 3/9, Južni/Severni čvor ako dodiruje komunikaciju.",
    "home_family": "4. kuća/IC, vladar 4, planete u 4, Mesec, Sunce za roditeljske figure, aspekti vladara 4, dispozitor lanca doma, 10. kuća kao drugi roditelj.",
    "love_children_creativity": "5. kuća, vladar 5, Venera, Sunce, planete u 5, aspekti vladara 5, Eros/lotovi ako postoje, deca samo oprezno, kreativnost kroz 5/2/10.",
    "work_health_routine": "6. kuća, vladar 6, planete u 6, Merkur/Mars/Saturn za radnu rutinu, zdravstvene predispozicije bez dijagnoza, odnos 6/10.",
    "relationships_marriage": "7. kuća/DSC, vladar 7, Venera/Mars, planete u 7, aspekti vladara 7, dispozitor, Lot braka ako postoji, odnos 5/7/10/4.",
    "crisis_transformation": "8. kuća, vladar 8, planete u 8, Mesec/Mars/Saturn/Pluton, aspekti vladara 8, 2/8 osa, dug/kredit/nasledstvo samo uz dokaz.",
    "foreign_higher_education": "9. kuća, vladar 9, Jupiter, Merkur, planete u 9, Fortuna u 9 ako postoji, aspekti 9/10/3.",
    "career_status": "10. kuća/MC, vladar 10, planete u 10, Sunce/Saturn/Jupiter/Mars, aspekti prema MC, odnos 6/10/2/11, dispozitor karijere, lotovi statusa ako postoje.",
    "friends_networks": "11. kuća, vladar 11, Jupiter/Venera, planete u 11, aspekti 11/10/2, publika, mreže, rezultati rada.",
    "hidden_endings_psychology": "12. kuća, vladar 12, planete u 12, Saturn/Neptun/Pluton/Mesec, aspekti 12/6/8, skriveno, izolacija, karma bez zastrašivanja.",
}

RELEVANT_NATAL_KEYS = [
    "angles",
    "houses",
    "house_cusps",
    "planets",
    "points",
    "aspects",
    "aspect_sets",
    "house_rulers",
    "dignities",
    "planetary_condition",
    "dispositor_chains",
    "proof_book",
    "lots",
    "fixed_stars",
    "nodes",
    "lilith",
    "chiron",
    "almuten",
    "midpoints",
    "antiscia",
    "dodecatemoria",
]


def _json_compact(data: Any, max_chars: int = 52000) -> str:
    text = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...TRUNCATED_FOR_SECTION_EVIDENCE_INPUT"


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"].strip()
    parts: list[str] = []
    for item in response.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(cleaned[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Evidence model did not return valid JSON object.")


def _openai_response_text(instructions: str, input_text: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set on the server.")
    model = os.getenv("OPENAI_MODEL", "gpt-5.2")
    payload = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "temperature": 0.18,
        "max_output_tokens": 4500,
        "text": {"verbosity": "high"},
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc
    text = _extract_output_text(parsed)
    if not text:
        raise RuntimeError("OpenAI response did not contain output text.")
    return text


def _filtered_natal_data(natal_data: dict[str, Any]) -> dict[str, Any]:
    filtered = {key: natal_data.get(key) for key in RELEVANT_NATAL_KEYS if key in natal_data}
    return filtered or natal_data


def _input_payload(request: SectionEvidenceRequest) -> str:
    interpretation = request.interpretation_payload or {}
    payload = {
        "section_key": request.section_key,
        "section_focus_hint": SECTION_FOCUS_HINTS.get(request.section_key, "Use the astrologically relevant house, ruler, planets, aspects, dispositors, dignities and proof layers for this section."),
        "client_context": request.client_context or {},
        "natal_data": _filtered_natal_data(request.natal_data or {}),
        "predictive_data": request.predictive_data or {},
        "interpretation_controls": {
            "narrative_focus_theme_blocks": interpretation.get("narrative_focus_theme_blocks", []),
            "supporting_tendency_theme_blocks": interpretation.get("supporting_tendency_theme_blocks", []),
            "hard_event_theme_blocks": interpretation.get("hard_event_theme_blocks", []),
            "blocked_theme_blocks": interpretation.get("blocked_theme_blocks", []),
            "top_timing_months": interpretation.get("top_timing_months", []),
            "required_report_coverage": interpretation.get("required_report_coverage", {}),
        },
    }
    return _json_compact(payload)


def build_section_evidence_pack(request: SectionEvidenceRequest) -> dict[str, Any]:
    instructions = """
Ti si interni astrološki analitičar za ASTRO ARIES STUDIO. Ne pišeš tekst za klijenta. Praviš stručni evidence/judgement pack koji će kasnije koristiti pisac izveštaja.

Vrati ISKLJUČIVO validan JSON objekat, bez markdowna i bez objašnjenja van JSON-a.

CILJ:
Za zadatu sekciju izvuci najvažnije astrološke dokaze i donesi stručnu presudu. Ovo nije stilsko pisanje. Ovo je analitički mozak pre pisanja.

OBAVEZNO:
- Koristi samo dostavljene podatke. Ne izmišljaj stepen, orbis, aspekt, vladara, lot ili planetu ako nisu u podacima.
- Ako ne možeš da nađeš dokaz za tvrdnju, stavi je u cannot_claim.
- Svaki evidence_chain mora završiti konkretnim judgement poljem.
- U evidence_chain koristi: house_or_topic, ruler_or_planet, placement, aspects, dispositor, dignity_condition, interpretation_judgement, life_manifestation.
- Aspekti moraju biti konkretni ako postoje: planeta-planeta, vrsta aspekta, orbis ako je dostupan.
- Vladar kuće je obavezan kada je sekcija vezana za kuću.
- Dignitet/bonitet/dispozitor koristi kada je dostupan.
- Ne pravi generičke tvrdnje tipa "osoba je kreativna" bez dokaza.

JSON FORMAT:
{
  "section_key": "...",
  "main_judgement": "jedna jaka stručna presuda za oblast",
  "main_gift": "glavna snaga oblasti",
  "main_risk": "glavni rizik ili kvar oblasti",
  "repeating_pattern": "obrazac koji se ponavlja kroz život",
  "concrete_manifestations": ["4-8 konkretnih životnih manifestacija"],
  "evidence_chains": [
    {
      "house_or_topic": "...",
      "ruler_or_planet": "...",
      "placement": "...",
      "aspects": ["..."],
      "dispositor": "...",
      "dignity_condition": "...",
      "interpretation_judgement": "...",
      "life_manifestation": "..."
    }
  ],
  "must_say": ["šta pisac mora reći u klijentskom tekstu"],
  "cannot_claim": ["šta se ne sme tvrditi"],
  "tone_instruction": "kako ovu sekciju treba napisati u stilu Knjiga o Tebi"
}
""".strip()
    input_text = _input_payload(request)
    text = _openai_response_text(instructions, input_text)
    parsed = _extract_json_object(text)
    parsed.setdefault("section_key", request.section_key)
    parsed.setdefault("evidence_pack_schema", "ASTRO_ARIES_SECTION_EVIDENCE_PACK_V1")
    return parsed


def section_evidence_payload(request: SectionEvidenceRequest) -> dict[str, Any]:
    pack = build_section_evidence_pack(request)
    return {
        "success": True,
        "schema": "ASTRO_ARIES_SECTION_EVIDENCE_PAYLOAD_V1",
        "section_key": request.section_key,
        "evidence_pack": pack,
    }
