from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel

try:
    from backend.astro_section_evidence import SectionEvidenceRequest, build_section_evidence_pack
except ModuleNotFoundError:
    from astro_section_evidence import SectionEvidenceRequest, build_section_evidence_pack


class FullReportWriteRequest(BaseModel):
    natal_data: dict[str, Any]
    predictive_data: dict[str, Any] | None = None
    interpretation_payload: dict[str, Any] | None = None
    client_context: dict[str, Any] | None = None
    report_type: str = "full_natal_predictive"
    sections: list[str] | None = None
    use_evidence_pack: bool = True


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


NATAL_SECTIONS = {
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
}


SECTION_TITLES = {
    "intro": "Dobrodošla u svoju kartu",
    "identity_vitality": "POGLAVLJE 1\nKo si zapravo — osnovni pečat tvoje karte",
    "money_values": "POGLAVLJE 2\nNovac, vrednost i cena sigurnosti",
    "communication_learning": "POGLAVLJE 3\nUm, reč i blisko okruženje",
    "home_family": "POGLAVLJE 4\nDom, koreni i ono što nosiš iz prvog prostora",
    "love_children_creativity": "POGLAVLJE 5\nLjubav, talenti, deca i ono što pali dušu",
    "work_health_routine": "POGLAVLJE 6\nRad, svakodnevica i telo koje govori istinu",
    "relationships_marriage": "POGLAVLJE 7\nPartnerstvo, brak i ogledalo preko puta tebe",
    "crisis_transformation": "POGLAVLJE 8\nTuđ novac, krize i mehanizam regeneracije",
    "foreign_higher_education": "POGLAVLJE 9\nZnanje, inostranstvo, pravo i šira slika života",
    "career_status": "POGLAVLJE 10\nKarijera, status i profesionalni vrh",
    "friends_networks": "POGLAVLJE 11\nPrijatelji, mreže i rezultati tvog rada",
    "hidden_endings_psychology": "POGLAVLJE 12\nKarma, skriveno, podsvest i tihi završeci",
    "predictive_scheme": "PREDIKCIJE\nKako se čita naredni period",
    "predictive_overview": "Dominanta narednih 12 meseci",
    "hard_events": "Šta se konkretno aktivira — i gde se ne sme izmišljati",
    "timeline": "Hronologija perioda",
    "direct_answers": "Direktni odgovori na pitanja",
    "final_word": "Završna reč",
}


SECTION_DEPTH = {
    "intro": "Napiši 700–1000 reči. Uvod mora zvučati kao ulaz u knjigu, snažno, lično, bez praznih fraza.",
    "identity_vitality": "Napiši 1500–2200 reči. Ovo je glavni pečat karte i mora biti dubok, upečatljiv i ličan.",
    "money_values": "Napiši 1300–1900 reči. Obradi novac životno, sa jasnim razlikovanjem zarade, kriza i tuđeg novca.",
    "communication_learning": "Napiši 1100–1600 reči. Objasni um, govor, učenje, okruženje i greške kroz realne primere.",
    "home_family": "Napiši 1300–1900 reči. Dom, roditelji i koreni moraju imati dubinu, ali bez izmišljanja događaja.",
    "love_children_creativity": "Napiši 1300–1900 reči. Razlikuj ljubav, flert, ozbiljnu vezu, decu i kreativnost.",
    "work_health_routine": "Napiši 1200–1800 reči. Razlikuj radnu rutinu, kolege, obaveze i zdravstvene predispozicije.",
    "relationships_marriage": "Napiši 1400–2000 reči. Partnerstvo, brak i ugovori moraju biti jasni, direktni i bez lažnih obećanja.",
    "crisis_transformation": "Napiši 1100–1600 reči. 8. kuću obradi ozbiljno, bez senzacionalizma.",
    "foreign_higher_education": "Napiši 1000–1500 reči. Razlikuj znanje, pravo, inostranstvo, put i status kroz obrazovanje.",
    "career_status": "Napiši 1500–2200 reči. Razlikuj karijeru, status, firmu, poziciju, šefa, kolege, ugovor i stabilnost.",
    "friends_networks": "Napiši 900–1300 reči. Razlikuj prijatelje, publiku, tim, mreže i rezultate rada.",
    "hidden_endings_psychology": "Napiši 1100–1600 reči. Karmu i 12. kuću piši ozbiljno, bez zastrašivanja.",
    "predictive_scheme": "Napiši 800–1200 reči. Objasni prediktivnu logiku klijentski, bez debug jezika.",
    "predictive_overview": "Napiši 1100–1600 reči. Ovo je pregled narednih 12 meseci, konkretan ali bez tvrdog događaja ako nije dozvoljen.",
    "hard_events": "Napiši 900–1300 reči. Ako nema tvrdih događaja, objasni šta se aktivira kao proces i šta se ne sme tvrditi.",
    "timeline": "Napiši 1200–1800 reči. Mesece piši kao životni vodič, ne kao listu intenziteta.",
    "direct_answers": "Napiši 800–1400 reči ili više ako ima pitanja. Odgovaraj direktno: da/ne/delimično, vreme, mehanizam, šta sada.",
    "final_word": "Napiši 650–950 reči. Završetak mora biti ličan, jak i pamtljiv, bez novih tvrdnji.",
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

PREDICTIVE_SECTIONS = {"predictive_scheme", "predictive_overview", "hard_events", "timeline", "direct_answers", "final_word"}


def _json_compact(data: Any, max_chars: int = 52000) -> str:
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
        "temperature": 0.38,
        "max_output_tokens": 11000,
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
        with urllib.request.urlopen(req, timeout=300) as resp:
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

STIL KOJI SE TRAŽI — KNJIGA O TEBI MODE:
- Svaka sekcija mora zvučati kao poglavlje iz premium astrološke knjige, ne kao blog, ne kao dnevni horoskop, ne kao tehnički izveštaj.
- Početak poglavlja mora odmah imati udarac: jedna jasna, pamtljiva rečenica koja otvara temu i stavlja klijenta u centar.
- Piši u ritmu: jak uvod → astro dokaz → životni prevod → konkretan zaključak → sledeći dokaz → dublji rez.
- Koristi precizne astrološke podatke kada postoje: znak, kuća, stepen, orbis, retrogradnost, dostojanstvo, bonitet, almuten, lot, midpoint, aspekt. Ali svaki tehnički podatak mora odmah biti preveden u život.
- Nije dovoljno reći šta je položaj. Moraš reći šta taj položaj radi osobi, gde je košta, gde je nosi, gde je čini drugačijom.
- Tekst treba da ima osećaj: "ovo ne može biti napisano za bilo koga drugog".

STROGA PRAVILA:
- Pišeš isključivo na srpskom jeziku, ekavica.
- Obraćaš se direktno klijentu: ti, tvoj, kod tebe.
- Ne pominješ JSON, payload, score, hard_event, allowed_theme_blocks, confirmation_matrix, API, model, debug, sistem, modul, input ili tehničke nazive aplikacije.
- Ne pišeš rečenice iz perspektive alata. Zabranjeno: "u dostavljenim podacima za ovu sekciju", "u ovom pozivu", "ako želiš", "mogu u narednoj sekciji", "nemam kompletan set", "nije dostavljeno u ovoj sekciji".
- Ne počinji svaku sekciju objašnjavanjem šta ćeš uraditi. Uđi odmah u tumačenje.
- Ne koristi formulacije "dao/dao-la". Piši neutralno: "podaci koji su uneti", "tvoja karta", "kod tebe".
- Ne pišeš bullet liste u tumačenju. Tekst mora biti narativan, sa naslovom i podnaslovom.
- Ne izmišljaš. Ako podatak nije potvrđen, napiši da se tu ne ide do tvrdnje, nego ostaje obrazac/predispozicija.
- Nema fraza: možda, moguće je svašta, univerzum, energija će sama, sve je moguće, samo veruj.
- Ne daješ deset opcija. Izvedi najjaču sintezu iz dostavljenih podataka.

EVIDENCE PACK JE GLAVNI IZVOR PRESUDE:
- Ako je uz sekciju dat section_evidence_pack, koristi ga kao obavezan stručni nacrt.
- main_judgement mora postati centralna poruka poglavlja.
- main_gift, main_risk i repeating_pattern moraju se jasno osetiti u tekstu.
- evidence_chains moraju biti pretočeni u narativne pasuse, bez JSON jezika.
- concrete_manifestations moraju postati konkretni primeri u životu.
- cannot_claim moraš poštovati: ne smeš tvrdnju iz cannot_claim pretvoriti u događaj.

PREDIKTIVNA SINTEZA:
- Predikcije nisu opis tranzita. Predikcije su sinteza natalne predispozicije + godišnje profekcije + solara + progresija + solar arc + tranzita kao tajminga.
- Ne tvrdi događaj bez dozvole kontrolnih prediktivnih podataka. Ako nema hard dokaza, napiši aktiviran proces, a ne događaj.
- Ako se spominje period, objasni šta je natalna osnova i koji prediktivni slojevi je aktiviraju.
- Ako postoje egzaktni orbisi u prediktivnim podacima, koristi ih za preciznost: "orbis od...", "egzaktno oko...", ali samo kada su stvarno dostupni.

CILJ:
Tekst mora zvučati kao plaćeni personalizovani izveštaj, ne kao dnevni horoskop i ne kao generička AI analiza. Klijent treba da oseti da čita tekst pisan baš za njega. Stil je topao, direktan, ponekad oštar, ali nikada grub; zanimljiv, ali nikada izmišljen.
""".strip()


def _extract_section_relevant_data(section_key: str, request: FullReportWriteRequest) -> dict[str, Any]:
    natal = request.natal_data or {}
    relevant_keys = [
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
    relevant = {key: natal.get(key) for key in relevant_keys if key in natal}
    if not relevant:
        relevant = natal
    return relevant


def _build_evidence_pack(section_key: str, request: FullReportWriteRequest) -> dict[str, Any] | None:
    if not request.use_evidence_pack or section_key not in NATAL_SECTIONS:
        return None
    evidence_request = SectionEvidenceRequest(
        section_key=section_key,
        natal_data=request.natal_data,
        predictive_data=request.predictive_data,
        interpretation_payload=request.interpretation_payload,
        client_context=request.client_context,
    )
    return build_section_evidence_pack(evidence_request)


def _section_input(section_key: str, request: FullReportWriteRequest, evidence_pack: dict[str, Any] | None = None) -> str:
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
        "section_focus_hint": SECTION_FOCUS_HINTS.get(section_key),
        "style_target": "KNJIGA_O_TEBI_MODE: dramatic premium chapter, concrete aspects/orbs when available, ruler-dispositor-dignity synthesis, final life judgement.",
        "section_evidence_pack": evidence_pack,
        "required_evidence_chain_mode": section_key in NATAL_SECTIONS,
        "section_coverage": section_coverage,
        "client_context": request.client_context or {},
        "natal_relevant_data": _extract_section_relevant_data(section_key, request),
        "predictive_context_available": bool(request.predictive_data),
        "interpretation_controls_available": bool(interpretation),
        "predictive_relevant_data": request.predictive_data or {},
        "interpretation_controls": theme_blocks,
    }
    return _json_compact(data)


def _section_prompt(section_key: str, request: FullReportWriteRequest, evidence_pack: dict[str, Any] | None = None) -> str:
    title = SECTION_TITLES.get(section_key, section_key)
    depth = SECTION_DEPTH.get(section_key, "Napiši duboko, konkretno i narativno.")
    focus = SECTION_FOCUS_HINTS.get(section_key, "")
    evidence_note = ""
    if section_key in NATAL_SECTIONS:
        evidence_note = f"""
OBAVEZNI DOKAZNI LANCI ZA OVU NATALNU SEKCIJU:
- Ako postoji section_evidence_pack, on je glavna stručna osnova. Ne smeš ga ignorisati.
- Pre pisanja mentalno pretvori main_judgement u centralnu osu poglavlja.
- Obavezno koristi relevantne tačke: {focus}
- U tekstu mora biti jasno vidljivo da si koristio vladare kuća, aspekte, dispozitore i snagu planeta.
- Nemoj pisati generički opis znaka/kuće. Svaki pasus mora imati dokaz i životni prevod.
- Ne ostavljaj lanac na tehnici. Posle svakog lanca mora doći presuda: šta to konkretno znači za osobu, gde je dar, gde je kvar, gde je ponavljanje, šta je posledica.
- Koristi stepen/orbis/bonitet samo ako postoji u podacima; kada ga koristiš, neka zvuči kao dokaz, ne kao tabela.
""".strip()
    predictive_note = ""
    if section_key in PREDICTIVE_SECTIONS:
        predictive_note = """
VAŽNO ZA PREDIKTIVNU SEKCIJU:
- Prediktivni i interpretativni podaci jesu dostavljeni ako predictive_context_available ili interpretation_controls_available stoji true.
- Predikcija mora povezati natalnu osnovu sa profekcijom, solarom, progresijama/solar arc slojem i tranzitnim tajmingom.
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
- Počni naslovom koji je već dat i dodaj podnaslov u stilu premium knjige.
- Prva rečenica mora biti snažna i specifična za klijenta, bez opšteg uvoda.
- Piši kao gotov tekst za klijenta, ne kao objašnjenje sistema.
- Uđi odmah u tumačenje; ne objašnjavaj da "ovaj deo obrađuje" nešto.
- Pokrij sve podteme iz section_coverage.must_cover ako postoje.
- Ako podatak nije potvrđen u astro podacima, ne preskači ga: reci prirodno da se ne ide do tvrdnje ili da obrazac postoji, ali nije gotov događaj.
- Ne koristi bullet liste.
- Ne piši tehnički debug.
- Ne izmišljaj događaje, zanimanja, brakove, decu, novac, bolest, selidbu ili uspeh ako nisu potvrđeni.
- Ne završavaj sekciju pozivom "ako želiš" niti upućuj klijenta na narednu sekciju.
- Tekst mora imati konkretnost: ko/šta/kako/gde se vidi u svakodnevnom životu.
- Stil mora biti bliži knjizi nego analitičkom memorandumu: ritam, drama, preciznost i presuda.
{evidence_note}
{predictive_note}

ULAZNI PODACI ZA OVU SEKCIJU:
{_section_input(section_key, request, evidence_pack)}
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
    evidence_packs: dict[str, Any] = {}
    instructions = _base_instructions()
    for section_key in requested_sections:
        if section_key not in DEFAULT_SECTIONS:
            continue
        evidence_pack = None
        try:
            evidence_pack = _build_evidence_pack(section_key, request)
            if evidence_pack:
                evidence_packs[section_key] = evidence_pack
        except Exception as exc:
            errors[f"{section_key}__evidence"] = f"Evidence pack failed: {exc}"
        prompt = _section_prompt(section_key, request, evidence_pack)
        try:
            sections[section_key] = _openai_response(instructions, prompt)
        except Exception as exc:
            errors[section_key] = str(exc)
            sections[section_key] = _fallback_section(section_key, exc)
    full_text = "\n\n".join(sections[key] for key in requested_sections if key in sections)
    coverage = (request.interpretation_payload or {}).get("required_report_coverage", {}) or {}
    return {
        "success": len([key for key in errors if not key.endswith("__evidence")]) == 0,
        "schema": "ASTRO_ARIES_FULL_REPORT_V1",
        "report_type": request.report_type,
        "sections": sections,
        "full_text": full_text,
        "evidence_packs": evidence_packs,
        "errors": errors,
        "qa": {
            "requested_sections": requested_sections,
            "generated_sections": list(sections.keys()),
            "evidence_pack_sections": list(evidence_packs.keys()),
            "required_coverage_sections": list(coverage.keys()),
            "rule": "Final QA must verify that every must_cover subtopic is addressed or explicitly marked as not confirmed, and that every natal section contains evidence chains and final judgements.",
        },
    }
