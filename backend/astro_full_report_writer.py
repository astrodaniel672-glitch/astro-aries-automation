from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel


class FullReportWriteRequest(BaseModel):
    natal_data: dict[str, Any]
    predictive_data: dict[str, Any] | None = None
    interpretation_payload: dict[str, Any] | None = None
    client_context: dict[str, Any] | None = None
    report_type: str = "full_natal_predictive"
    sections: list[str] | None = None


DEFAULT_SECTIONS = [
    "intro",
    "identity_vitality",
    "money_values",
    "communication_learning",
    "home_family",
    "love_children_creativity",
    "work_health_routine",
    "relationships_marriage",
    "crisis_transformation",
    "foreign_higher_education",
    "career_status",
    "friends_networks",
    "hidden_endings_psychology",
    "predictive_scheme",
    "predictive_overview",
    "hard_events",
    "timeline",
    "direct_answers",
    "final_word",
]


SECTION_TITLES = {
    "intro": "Uvod",
    "identity_vitality": "Osnovni pečat karte — ko si, kako te vide i šta nosiš",
    "money_values": "Finansije, vrednosti i odnos prema novcu",
    "communication_learning": "Um, komunikacija i blisko okruženje",
    "home_family": "Dom, porodica i koreni",
    "love_children_creativity": "Ljubav, talenti, kreativnost i deca",
    "work_health_routine": "Svakodnevni rad, rutina i zdravlje",
    "relationships_marriage": "Partnerstvo, brak i odnosi jedan-na-jedan",
    "crisis_transformation": "Tuđ novac, krize, dugovi i regeneracija",
    "foreign_higher_education": "Inostranstvo, obrazovanje, pravo i viši smisao",
    "career_status": "Karijera, status i profesionalni vrh",
    "friends_networks": "Prijatelji, mreže i rezultati rada",
    "hidden_endings_psychology": "Karma, podsvest, tajne i završeci",
    "predictive_scheme": "Prediktivna šema — kako se čita naredni period",
    "predictive_overview": "Dominanta narednih 12 meseci",
    "hard_events": "Konkretna dešavanja i granica tvrdnje",
    "timeline": "Hronologija perioda",
    "direct_answers": "Direktni odgovori na pitanja",
    "final_word": "Završna reč",
}


THEME_TO_COVERAGE_KEY = {
    "intro": "intro",
    "identity_vitality": "identity_vitality",
    "money_values": "money_values",
    "communication_learning": "communication_learning",
    "home_family": "home_family",
    "love_children_creativity": "love_children_creativity",
    "work_health_routine": "work_health_routine",
    "relationships_marriage": "relationships_marriage",
    "crisis_transformation": "crisis_transformation",
    "foreign_higher_education": "foreign_higher_education",
    "career_status": "career_status",
    "friends_networks": "friends_networks",
    "hidden_endings_psychology": "hidden_endings_psychology",
    "predictive_scheme": "predictive_scheme",
    "predictive_overview": "predictive_overview",
    "hard_events": "hard_events",
    "timeline": "timeline",
    "direct_answers": "direct_answers",
    "final_word": "final_word",
}

PREDICTIVE_SECTIONS = {"predictive_scheme", "predictive_overview", "hard_events", "timeline", "direct_answers", "final_word"}


def _json_compact(data: Any, max_chars: int = 26000) -> str:
    text = json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...TRUNCATED_FOR_SECTION_INPUT"


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"].strip()
    parts: list[str] = []
    for item in response.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def _openai_response(instructions: str, input_text: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set on the server.")
    model = os.getenv("OPENAI_MODEL", "gpt-5.2")
    payload = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "temperature": 0.35,
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc
    text = _extract_output_text(parsed)
    if not text:
        raise RuntimeError("OpenAI response did not contain output text.")
    return text


def _base_instructions() -> str:
    return """
Ti si profesionalni astrolog i pisac izveštaja u ASTRO ARIES STUDIU. Pišeš kao Astrolog Daniel: direktno, prirodno, srpski, jasno, zanimljivo, iskreno i bez generičkog horoskopa.

STROGA PRAVILA:
- Pišeš isključivo na srpskom jeziku, ekavica.
- Obraćaš se direktno klijentu: ti, tvoj, kod tebe.
- Ne pominješ JSON, payload, score, hard_event, allowed_theme_blocks, confirmation_matrix, API, model, debug, sistem, modul, sekcija, input ili tehničke nazive aplikacije.
- Ne pišeš rečenice iz perspektive alata. Zabranjeno: "u dostavljenim podacima za ovu sekciju", "u ovom pozivu", "ako želiš", "mogu u narednoj sekciji", "nemam kompletan set", "nije dostavljeno u ovoj sekciji".
- Ako nema dokaza, piši klijentski i profesionalno: "karta ne daje dovoljno jak pokazatelj da se to tvrdi kao konkretan događaj".
- Ne koristi formulacije "dao/dao-la". Piši neutralno: "podaci koji su uneti", "tvoja karta", "kod tebe".
- Ne pišeš bullet liste u tumačenju. Tekst mora biti narativan, sa naslovom i podnaslovom.
- Ne izmišljaš. Ako podatak nije potvrđen, napiši da nema dovoljno jakog pokazatelja da se to tvrdi.
- Nema fraza: možda, moguće je svašta, univerzum, energija će sama, sve je moguće, samo veruj.
- Ne daješ deset opcija. Izvedi najjaču sintezu iz dostavljenih podataka.
- Tehničke astrološke pokazatelje prevodiš u život: posao, status, porodica, novac, odnos, odluka, papir, telo, svakodnevica.
- Aspekti, kuće, vladari, dispozitori, dostojanstva i prediktivne tehnike se koriste kao dokaz u pozadini. Možeš ih pomenuti kratko samo kada to pojačava poverenje, ali nikad ne zatrpavaj klijenta tehnikom.
- Za predikcije: konkretan događaj smeš tvrditi samo ako kontrolni prediktivni podaci dozvoljavaju tvrd događaj. Ako tvrd događaj ne postoji, piši kao proces, pritisak, tema ili tendencija.
- Ako je tema sporedna ili blokirana pravilima, ne smeš je pretvarati u glavnu tvrdnju.
- Svaka sekcija mora odgovoriti na obavezne podteme iz must_cover, ali ne kao spisak pitanja. Utopi odgovore u prirodan tekst.

CILJ:
Tekst mora zvučati kao plaćeni personalizovani izveštaj, ne kao dnevni horoskop i ne kao generička AI analiza. Klijent treba da oseti da čita tekst pisan baš za njega.
""".strip()


def _section_input(section_key: str, request: FullReportWriteRequest) -> str:
    interpretation = request.interpretation_payload or {}
    coverage = interpretation.get("required_report_coverage", {}) or {}
    coverage_key = THEME_TO_COVERAGE_KEY.get(section_key, section_key)
    section_coverage = coverage.get(coverage_key, {})
    theme_blocks = {
        "narrative_focus_theme_blocks": interpretation.get("narrative_focus_theme_blocks", []),
        "supporting_tendency_theme_blocks": interpretation.get("supporting_tendency_theme_blocks", []),
        "hard_event_theme_blocks": interpretation.get("hard_event_theme_blocks", []),
        "blocked_theme_blocks": interpretation.get("blocked_theme_blocks", []),
        "chart_signature": interpretation.get("chart_signature", {}),
        "top_timing_months": interpretation.get("top_timing_months", []),
        "rules": interpretation.get("rules", {}),
    }
    data = {
        "section_key": section_key,
        "section_title": SECTION_TITLES.get(section_key, section_key),
        "section_coverage": section_coverage,
        "client_context": request.client_context or {},
        "natal_data": request.natal_data or {},
        "predictive_context_available": bool(request.predictive_data),
        "interpretation_controls_available": bool(interpretation),
        "predictive_relevant_data": request.predictive_data or {},
        "interpretation_controls": theme_blocks,
    }
    return _json_compact(data)


def _section_prompt(section_key: str, request: FullReportWriteRequest) -> str:
    title = SECTION_TITLES.get(section_key, section_key)
    predictive_note = ""
    if section_key in PREDICTIVE_SECTIONS:
        predictive_note = """
VAŽNO ZA PREDIKTIVNU SEKCIJU:
- Prediktivni i interpretativni podaci jesu dostavljeni ako predictive_context_available ili interpretation_controls_available stoji true.
- Ne smeš napisati da nemaš kompletan prediktivni set samo zato što ne postoji tvrd događaj.
- Ako nema dozvoljenog konkretnog događaja, napiši: karta pokazuje aktivne procese/teme, ali ne daje dovoljno tvrdog dokaza za sigurnu tvrdnju događaja.
- Koristi glavne teme iz narrative_focus kao okosnicu perioda, supporting teme kao pozadinu, a hard event samo ako postoji.
""".strip()
    return f"""
Napiši sledeću sekciju kompletnog Astro Aries izveštaja.

SEKCIJA: {title}

Obavezno:
- Počni sa naslovom sekcije i kratkim podnaslovom.
- Piši kao gotov tekst za klijenta, ne kao objašnjenje sistema.
- Pokrij sve podteme iz section_coverage.must_cover ako postoje.
- Ako podatak nije potvrđen u astro podacima, ne preskači ga: napiši jasno da karta ne daje dovoljno jak pokazatelj za tvrdnju.
- Ne koristi bullet liste.
- Ne piši tehnički debug.
- Ne izmišljaj događaje, zanimanja, brakove, decu, novac, bolest, selidbu ili uspeh ako nisu potvrđeni.
- Za prediktivne delove poštuj kontrolne prediktivne podatke: tvrd događaj samo ako postoji, glavna tema kao proces, sporedna tema kao pozadina.
- Ne završavaj sekciju pozivom "ako želiš" niti upućuj klijenta na narednu sekciju.
{predictive_note}

ULAZNI PODACI ZA OVU SEKCIJU:
{_section_input(section_key, request)}
""".strip()


def _fallback_section(section_key: str, err: Exception) -> str:
    title = SECTION_TITLES.get(section_key, section_key)
    return (
        f"{title}\n"
        "Ova sekcija nije mogla biti generisana AI modelom u ovom pozivu. "
        "Proveri da li je OPENAI_API_KEY podešen na serveru i da li API poziv prolazi. "
        f"Tehnička poruka: {err}"
    )


def write_full_report(request: FullReportWriteRequest) -> dict[str, Any]:
    requested_sections = request.sections or DEFAULT_SECTIONS
    sections: dict[str, str] = {}
    errors: dict[str, str] = {}
    instructions = _base_instructions()
    for section_key in requested_sections:
        if section_key not in DEFAULT_SECTIONS:
            continue
        prompt = _section_prompt(section_key, request)
        try:
            sections[section_key] = _openai_response(instructions, prompt)
        except Exception as exc:
            errors[section_key] = str(exc)
            sections[section_key] = _fallback_section(section_key, exc)
    full_text = "\n\n".join(sections[key] for key in requested_sections if key in sections)
    coverage = (request.interpretation_payload or {}).get("required_report_coverage", {}) or {}
    return {
        "success": len(errors) == 0,
        "schema": "ASTRO_ARIES_FULL_REPORT_V1",
        "report_type": request.report_type,
        "sections": sections,
        "full_text": full_text,
        "errors": errors,
        "qa": {
            "requested_sections": requested_sections,
            "generated_sections": list(sections.keys()),
            "required_coverage_sections": list(coverage.keys()),
            "rule": "Final QA must verify that every must_cover subtopic is addressed or explicitly marked as not confirmed.",
        },
    }
