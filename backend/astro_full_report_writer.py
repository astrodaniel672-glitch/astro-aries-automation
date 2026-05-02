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


SECTION_DEPTH = {
    "intro": "Napiši 450–700 reči. Uvod mora odmah privući pažnju; ne objašnjavaj predugo šta je izveštaj.",
    "identity_vitality": "Napiši 1200–1700 reči. Ovo je glavni pečat karte i mora biti dubok, upečatljiv i ličan.",
    "money_values": "Napiši 1000–1500 reči. Obradi novac životno, sa jasnim razlikovanjem zarade, kriza i tuđeg novca.",
    "communication_learning": "Napiši 900–1300 reči. Objasni um, govor, učenje, okruženje i greške kroz realne primere.",
    "home_family": "Napiši 1000–1500 reči. Dom, roditelji i koreni moraju imati dubinu, ali bez izmišljanja događaja.",
    "love_children_creativity": "Napiši 1000–1500 reči. Razlikuj ljubav, flert, ozbiljnu vezu, decu i kreativnost.",
    "work_health_routine": "Napiši 1000–1500 reči. Razlikuj radnu rutinu, kolege, obaveze i zdravstvene predispozicije.",
    "relationships_marriage": "Napiši 1100–1600 reči. Partnerstvo, brak i ugovori moraju biti jasni, direktni i bez lažnih obećanja.",
    "crisis_transformation": "Napiši 900–1300 reči. 8. kuću obradi ozbiljno, bez senzacionalizma.",
    "foreign_higher_education": "Napiši 800–1200 reči. Razlikuj znanje, pravo, inostranstvo, put i status kroz obrazovanje.",
    "career_status": "Napiši 1200–1700 reči. Razlikuj karijeru, status, firmu, poziciju, šefa, kolege, ugovor i stabilnost.",
    "friends_networks": "Napiši 750–1100 reči. Razlikuj prijatelje, publiku, tim, mreže i rezultate rada.",
    "hidden_endings_psychology": "Napiši 900–1300 reči. Karmu i 12. kuću piši ozbiljno, bez zastrašivanja.",
    "predictive_scheme": "Napiši 650–950 reči. Objasni prediktivnu logiku klijentski, bez debug jezika.",
    "predictive_overview": "Napiši 900–1300 reči. Ovo je pregled narednih 12 meseci, konkretan ali bez tvrdog događaja ako nije dozvoljen.",
    "hard_events": "Napiši 650–1000 reči. Ako nema tvrdih događaja, objasni šta se aktivira kao proces i šta se ne sme tvrditi.",
    "timeline": "Napiši 900–1400 reči. Mesece piši kao životni vodič, ne kao listu intenziteta.",
    "direct_answers": "Napiši 600–1000 reči ili više ako ima pitanja. Odgovaraj direktno: da/ne/delimično, vreme, mehanizam, šta sada.",
    "final_word": "Napiši 450–750 reči. Završetak mora biti ličan, jak i pamtljiv, bez novih tvrdnji.",
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
        "temperature": 0.55,
        "max_output_tokens": 7000,
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


def _base_instructions() -> str:
    return """
Ti si profesionalni astrolog i pisac izveštaja u ASTRO ARIES STUDIU. Pišeš kao Astrolog Daniel: direktno, prirodno, srpski, jasno, zanimljivo, iskreno i bez generičkog horoskopa.

STROGA PRAVILA:
- Pišeš isključivo na srpskom jeziku, ekavica.
- Obraćaš se direktno klijentu: ti, tvoj, kod tebe.
- Tekst mora ličiti na premium knjigu/izveštaj za klijenta, ne na opis metode.
- Ne pominješ JSON, payload, score, hard_event, allowed_theme_blocks, confirmation_matrix, API, model, debug, sistem, modul, sekcija, input ili tehničke nazive aplikacije.
- Ne pišeš rečenice iz perspektive alata. Zabranjeno: "u dostavljenim podacima za ovu sekciju", "u ovom pozivu", "ako želiš", "mogu u narednoj sekciji", "nemam kompletan set", "nije dostavljeno u ovoj sekciji".
- Ne počinji svaku sekciju objašnjavanjem šta ćeš uraditi. Uđi odmah u tumačenje.
- Ne ponavljaj prečesto frazu "karta ne daje dovoljno jak pokazatelj". Upotrebi je samo kada je zaista neophodno. Inače piši prirodnije: "ovde ne bih išao do tvrdnje", "to ostaje predispozicija, ne gotova činjenica", "ovo se vidi kao obrazac, ne kao siguran događaj".
- Ne koristi formulacije "dao/dao-la". Piši neutralno: "podaci koji su uneti", "tvoja karta", "kod tebe".
- Ne pišeš bullet liste u tumačenju. Tekst mora biti narativan, sa naslovom i podnaslovom.
- Ne izmišljaš. Ako podatak nije potvrđen, napiši da nema dovoljno jakog pokazatelja da se to tvrdi.
- Nema fraza: možda, moguće je svašta, univerzum, energija će sama, sve je moguće, samo veruj.
- Ne daješ deset opcija. Izvedi najjaču sintezu iz dostavljenih podataka.
- Tehničke astrološke pokazatelje prevodiš u život: posao, status, porodica, novac, odnos, odluka, papir, telo, svakodnevica.
- Aspekti, kuće, vladari, dispozitori, dostojanstva i prediktivne tehnike se koriste kao dokaz u pozadini. Možeš ih pomenuti kratko samo kada to pojačava poverenje, ali nikad ne zatrpavaj klijenta tehnikom.
- Svaki pomen aspekta mora odmah imati prevod u realan život. Npr. ne piši samo "Merkur u Ovnu", nego objasni kako osoba govori, odlučuje, greši, uči i reaguje.
- Za predikcije: konkretan događaj smeš tvrditi samo ako kontrolni prediktivni podaci dozvoljavaju tvrd događaj. Ako tvrd događaj ne postoji, piši kao proces, pritisak, tema ili tendencija.
- Ako je tema sporedna ili blokirana pravilima, ne smeš je pretvarati u glavnu tvrdnju.
- Svaka sekcija mora odgovoriti na obavezne podteme iz must_cover, ali ne kao spisak pitanja. Utopi odgovore u prirodan tekst.
- U svakoj većoj natalnoj sekciji moraš dati najmanje 4 konkretne životne manifestacije: kako se vidi u ponašanju, odnosima, poslu, novcu, domu, telu ili odlukama.

CILJ:
Tekst mora zvučati kao plaćeni personalizovani izveštaj, ne kao dnevni horoskop i ne kao generička AI analiza. Klijent treba da oseti da čita tekst pisan baš za njega. Stil je topao, direktan, ponekad oštar, ali nikada grub; zanimljiv, ali nikada izmišljen.
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
        "section_depth_instruction": SECTION_DEPTH.get(section_key, "Napiši duboko, konkretno i narativno."),
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
    depth = SECTION_DEPTH.get(section_key, "Napiši duboko, konkretno i narativno.")
    predictive_note = ""
    if section_key in PREDICTIVE_SECTIONS:
        predictive_note = """
VAŽNO ZA PREDIKTIVNU SEKCIJU:
- Prediktivni i interpretativni podaci jesu dostavljeni ako predictive_context_available ili interpretation_controls_available stoji true.
- Ne smeš napisati da nemaš kompletan prediktivni set samo zato što ne postoji tvrd događaj.
- Ako nema dozvoljenog konkretnog događaja, napiši: period pokreće procese i odluke, ali ne zaključava događaj kao sigurnu činjenicu.
- Koristi glavne teme iz narrative_focus kao okosnicu perioda, supporting teme kao pozadinu, a hard event samo ako postoji.
- Mesece bez intenziteta ne opisuj kao događaje. Ako nema okidača, napiši da je to period održavanja i stabilizacije, ne drama.
""".strip()
    return f"""
Napiši sledeću sekciju kompletnog Astro Aries izveštaja.

SEKCIJA: {title}
DUBINA: {depth}

Obavezno:
- Počni sa naslovom sekcije i kratkim podnaslovom.
- Piši kao gotov tekst za klijenta, ne kao objašnjenje sistema.
- Uđi odmah u tumačenje; ne objašnjavaj da "ovaj deo obrađuje" nešto.
- Pokrij sve podteme iz section_coverage.must_cover ako postoje.
- Ako podatak nije potvrđen u astro podacima, ne preskači ga: reci prirodno da se ne ide do tvrdnje ili da obrazac postoji, ali nije gotov događaj.
- Ne koristi bullet liste.
- Ne piši tehnički debug.
- Ne izmišljaj događaje, zanimanja, brakove, decu, novac, bolest, selidbu ili uspeh ako nisu potvrđeni.
- Za prediktivne delove poštuj kontrolne prediktivne podatke: tvrd događaj samo ako postoji, glavna tema kao proces, sporedna tema kao pozadina.
- Ne završavaj sekciju pozivom "ako želiš" niti upućuj klijenta na narednu sekciju.
- Tekst mora imati konkretnost: ko/šta/kako/gde se vidi u svakodnevnom životu.
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
