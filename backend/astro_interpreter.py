from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PredictiveInterpretRequest(BaseModel):
    predictive_data: dict[str, Any]
    client_name: str | None = None
    focus_question: str | None = None
    style: str = "professional_serbian"


ALLOWED_STATUSES = {"strong"}
BLOCKED_STATUSES = {"insufficient"}


REQUIRED_REPORT_COVERAGE: dict[str, dict[str, Any]] = {
    "intro": {
        "section_id": 0,
        "title": "Uvod",
        "must_cover": ["klijent u prvom planu", "ton izveštaja", "bez dubinskih tvrdnji u uvodu", "radoznalost i poverenje"],
        "writing_rule": "Uvod je privlačan, ljudski i direktan, ali bez konkretnih dubinskih tumačenja koja pripadaju kasnijim sferama.",
    },
    "identity_vitality": {
        "section_id": 1,
        "title": "Osnovni pečat karte",
        "must_cover": ["ko je osoba", "kako je drugi vide", "vrline", "mane", "fizički izgled", "čemu teži", "šta je sputava", "ko je sputava", "životni pravac", "lični nastup"],
        "writing_rule": "Sve podteme moraju biti utopljene u narativ o osnovnom pečatu karte, bez nabrajanja pitanja.",
    },
    "money_values": {
        "section_id": 2,
        "title": "Finansije i vrednosti",
        "must_cover": ["životni finansijski obrazac", "potencijal za bogatstvo", "rizik od siromaštva ili oscilacija", "šta donosi najviše novca", "gde ulagati energiju/resurse", "finansijske krize", "uticaj drugih ljudi na novac", "lična zarada", "zajednički novac"],
        "writing_rule": "Razdvojiti zaradu, troškove, vrednovanje rada, ulaganja, krize i novac drugih ljudi. Ne obećavati bogatstvo bez dokaza.",
    },
    "communication_learning": {
        "section_id": 3,
        "title": "Um, komunikacija i blisko okruženje",
        "must_cover": ["kako osoba komunicira", "ko je u blizini/okruženju", "brat/sestra ako je vidljivo", "način učenja", "način razmišljanja", "tipične mentalne greške", "papiri", "kraći putevi", "odluke"],
        "writing_rule": "Tehniku prevesti u svakodnevni govor: kako osoba misli, uči, govori, greši i kako koristi informacije.",
    },
    "home_family": {
        "section_id": 4,
        "title": "Dom, porodica i koreni",
        "must_cover": ["roditeljski dom", "predispozicija mesta života", "kuća/dom/porodica", "šta nosi iz doma", "koreni", "selidbe i promene", "otac", "majka", "privatna sigurnost"],
        "writing_rule": "Razdvojiti atmosferu doma od konkretne selidbe/nekretnine. Roditelje opisivati samo kroz jasne pokazatelje.",
    },
    "love_children_creativity": {
        "section_id": 5,
        "title": "Ljubav, talenti, deca i radost",
        "must_cover": ["talenti", "šta ljubav znači", "kako osoba doživljava ljubav", "veze pre braka", "kako veze počinju", "kako se završavaju", "predispozicija za decu", "broj/pol dece samo ako postoji dokaz", "kreativnost", "radost"],
        "writing_rule": "Ne izmišljati decu, pol dece, trudnoću ili broj veza. Ako nema dokaza, formulisati kao predispoziciju ili ne tvrditi.",
    },
    "work_health_routine": {
        "section_id": 6,
        "title": "Svakodnevni rad, rutina i zdravlje",
        "must_cover": ["svakodnevno funkcionisanje", "kada je osoba produktivna", "šta dobro radi", "gde može biti dobra", "radne obaveze", "kolege kao svakodnevno okruženje", "šta ugrožava zdravlje", "najosetljivije tačke", "zdravstvene predispozicije", "navike"],
        "writing_rule": "Razlikovati rutinu i radno opterećenje od karijernog statusa. Zdravlje pisati kao predispoziciju, ne dijagnozu.",
    },
    "relationships_marriage": {
        "section_id": 7,
        "title": "Partnerstvo, brak i odnosi jedan-na-jedan",
        "must_cover": ["predispozicije za partnerstvo", "kakav je partner", "izgled partnera ako je vidljivo", "čime se partner bavi ako je vidljivo", "gde se upoznaje", "više od jednog braka", "prvi brak", "drugi brak", "kada je predispozicija za brak", "da li osoba već poznaje partnera ako je vidljivo", "javni ugovori"],
        "writing_rule": "Ne obećavati brak, razvod ili partnera bez jasnog lanca. Ako je klijent već u braku, pitanje prilagoditi realnom statusu.",
    },
    "crisis_transformation": {
        "section_id": 8,
        "title": "Tuđ novac, krize i regeneracija",
        "must_cover": ["nasledstvo", "zajednički novac", "finansijski preokret kroz 8. kuću", "dugovi", "krediti", "porezi", "mehanizam oporavka", "regeneracija", "duboke krize", "psihološki pritisak"],
        "writing_rule": "8. kuću ne koristiti senzacionalistički. Nasledstvo, dug ili krizu tvrditi samo uz jasne pokazatelje.",
    },
    "foreign_higher_education": {
        "section_id": 9,
        "title": "Inostranstvo, znanje, pravo i viši smisao",
        "must_cover": ["visoko obrazovanje", "inostranstvo", "šta inostranstvo donosi", "znanje kao rezultat/status", "pravna pitanja", "vera/filozofija", "daleka putovanja", "mentori", "publikovanje"],
        "writing_rule": "Razlikovati učenje, pravo, putovanje, vizu/preseljenje i status kroz znanje. Ne tvrditi odlazak bez potvrde.",
    },
    "career_status": {
        "section_id": 10,
        "title": "Karijera, status i profesionalni vrh",
        "must_cover": ["čime se osoba bavi", "šta joj najviše leži", "vrhunac karijere", "dokle može stići", "značajan poslovni uspeh", "status", "kolege", "šef/nadređeni", "odnos prema poslu", "talenti za posao", "dugoročna stabilnost", "promena posla/firme/pozicije samo ako je razlučeno"],
        "writing_rule": "Obavezno razlikovati karijerni status, firmu, poziciju, ugovor, svakodnevni posao, šefa i kolege. Ne svoditi sve na 'posao'.",
    },
    "friends_networks": {
        "section_id": 11,
        "title": "Prijatelji, mreže i rezultati rada",
        "must_cover": ["prijatelji", "širenje kruga ljudi", "publika", "mreže", "rezultati rada", "ko donosi uspeh", "grupe", "planovi", "podrška"],
        "writing_rule": "Razlikovati prijatelje od publike, mreže od tima, i rezultate rada od same karijere.",
    },
    "hidden_endings_psychology": {
        "section_id": 12,
        "title": "Karma, podsvest, tajne i završeci",
        "must_cover": ["karma", "dobra karma", "teška karma", "šta prevazići", "opasnosti ako postoje", "tajni neprijatelji ako postoje", "12. kuća i zdravlje", "izolacija", "tajne", "šta promeniti", "na šta obratiti pažnju"],
        "writing_rule": "Ne zastrašivati. Tajne neprijatelje, opasnost i zdravstvene probleme tvrditi samo uz dokaz; inače pisati kao obrazac/predispoziciju.",
    },
    "predictive_scheme": {
        "section_id": 13,
        "title": "Prediktivna šema",
        "must_cover": ["natal kao osnova", "profekcija", "solar", "progresije", "solar arc", "tranziti kao tajming", "lunacije/lunarni okidači", "šta je aktivirano", "šta nije dovoljno potvrđeno", "bez nagađanja"],
        "writing_rule": "Pre predikcija jasno izložiti logiku bez tehničkog pretrpavanja. Ne obećavati događaje bez hard_event blokova.",
    },
    "predictive_overview": {
        "section_id": 14,
        "title": "Dominanta narednih 12 meseci",
        "must_cover": ["dominantna tema", "glavni pritisak", "šta nosi period", "šta je u fokusu", "kratak uvod u godinu"],
        "writing_rule": "Koristiti chart_signature i narrative_focus_theme_blocks kao kičmu perioda.",
    },
    "hard_events": {
        "section_id": 15,
        "title": "Konkretna dešavanja",
        "must_cover": ["šta je sigurno aktivirano", "šta donosi konkretna dešavanja", "kada", "kroz koga/šta", "mehanizam događaja", "šta se ne sme tvrditi"],
        "writing_rule": "Konkretne događaje pisati samo iz hard_event_theme_blocks. Ako su prazni, iskreno reći da nema dovoljno hard-event potvrde.",
    },
    "timeline": {
        "section_id": 16,
        "title": "Hronologija perioda",
        "must_cover": ["mesečni/nedeljni periodi", "najaktivniji periodi", "od-do okviri", "vrhunci", "zelene zone", "crvene zone", "bez kontradikcija", "periodi bez jakih događaja"],
        "writing_rule": "Koristiti top_timing_months i tranzite samo kao tajming potvrđenih tema. Ne izmišljati mesece bez aktivacija.",
    },
    "direct_answers": {
        "section_id": 17,
        "title": "Direktni odgovori na konkretna pitanja",
        "must_cover": ["direktan odgovor da/ne/delimično", "kada", "kako/zašto", "šta sada", "bez lažne nade", "prazan skup ako nema aktivacije"],
        "writing_rule": "Odgovoriti direktno. Ako nema dokaza, reći da nema dovoljno potvrde. Ne tražiti pozitivnu tačku po svaku cenu.",
    },
    "final_word": {
        "section_id": 18,
        "title": "Završna reč",
        "must_cover": ["glavna poruka", "šta klijent treba da zapamti", "realan ton", "Astro Aries potpis", "bez prazne motivacije"],
        "writing_rule": "Zaključak mora biti upečatljiv, ljudski i tačan; ne sme unositi nove tvrdnje koje nisu već pokrivene.",
    },
}


THEME_MANIFESTATION_RULES: dict[str, dict[str, Any]] = {
    "identity_vitality": {
        "primary_manifestation": "identity_direction_body_energy_and_personal_positioning",
        "supported_claims": [
            "Sme se pisati o ličnom pravcu, samopouzdanju, nastupu, telu, energiji, načinu predstavljanja i promeni odnosa prema sebi.",
            "Ako su aktivni ASC, Sunce, Mars ili vladar ASC, naglasak je na ličnoj odluci, fizičkom ritmu, hrabrosti ili potrebi da osoba zauzme jasniju poziciju.",
        ],
        "forbidden_claims": [
            "Ne tvrditi zdravstveni događaj, operaciju, povredu ili fizičku krizu bez posebnog hard-event dokaza.",
            "Ne pretvarati opštu aktivaciju identiteta u tvrdnju da osoba sigurno menja život iz korena.",
        ],
    },
    "money_values": {
        "primary_manifestation": "money_income_values_resources_and_spending_pressure",
        "supported_claims": [
            "Sme se pisati o zaradi, troškovima, vrednovanju rada, odnosu prema novcu, potrebi za finansijskom disciplinom i promeni načina upravljanja resursima.",
            "Ako se ponavljaju Venera, Jupiter, Saturn, 2. ili 8. kuća, razdvojiti ličnu zaradu od zajedničkog novca, kredita, duga ili podrške drugih ljudi.",
        ],
        "forbidden_claims": [
            "Ne tvrditi veliki dobitak, siromaštvo, kredit, nasledstvo, dug ili finansijski slom bez aktivacije 2/8 sloja i hard-event potvrde.",
            "Ne obećavati bogatstvo samo na osnovu Jupitera ili Venere bez strukturne potvrde.",
        ],
    },
    "communication_learning": {
        "primary_manifestation": "papers_learning_communication_decision_and_local_movement",
        "supported_claims": [
            "Sme se pisati o papirima, dogovorima, učenju, pregovorima, komunikaciji, porukama, kraćim putevima, odlukama i mentalnom fokusu.",
            "Ako su uključeni Merkur, 3. ili 9. kuća, razlikovati običnu komunikaciju od formalnog dokumenta, edukacije, ispita, pravnog/administrativnog procesa ili putovanja.",
        ],
        "forbidden_claims": [
            "Ne tvrditi potpis ugovora, zvanično rešenje, presudu, ispit ili putovanje ako nema hard-event potvrde i preciznog tajminga.",
            "Ne pretvarati Merkur/Mars tranzit u siguran dokument bez strukturne podrške.",
        ],
    },
    "home_family": {
        "primary_manifestation": "home_family_property_roots_and_private_base",
        "supported_claims": [
            "Sme se pisati o domu, porodici, privatnoj osnovi, roditeljima, organizaciji prostora, emocionalnom osloncu i unutrašnjoj sigurnosti.",
            "Ako su aktivni IC, Mesec, Saturn, 4. kuća ili vladar 4, razlikovati atmosferu doma od konkretne selidbe, kupovine, renoviranja ili porodičnog događaja.",
        ],
        "forbidden_claims": [
            "Ne tvrditi sigurnu selidbu, kupovinu/prodaju nekretnine, smrt/bolest roditelja ili porodični preokret bez annual/solar aktivacije i hard-event potvrde.",
            "Ne pisati o nekretnini kao događaju ako postoji samo psihološki pritisak na IC/Mesec.",
        ],
    },
    "love_children_creativity": {
        "primary_manifestation": "love_romance_children_creativity_pleasure_and_visibility",
        "supported_claims": [
            "Sme se pisati o ljubavi, romantici, privlačnosti, kreativnosti, deci, hobijima, radosti i potrebi da osoba bude viđena.",
            "Ako se ponavljaju 5. kuća, Venera, Sunce ili Mesec, razlikovati flert, vezu, kreativni projekat, temu dece i lično zadovoljstvo.",
        ],
        "forbidden_claims": [
            "Ne tvrditi trudnoću, rođenje deteta, novu vezu, pomirenje ili prekid bez jasnog 5/7/Venera/Mesec hard-event lanca.",
            "Ne pretvarati Venerin tranzit u sudbinsku ljubav ako nema potvrde kroz 5/7 sloj.",
        ],
    },
    "work_health_routine": {
        "primary_manifestation": "daily_work_routine_obligations_colleagues_and_health_habits",
        "supported_claims": [
            "Sme se pisati o svakodnevnom poslu, obavezama, rutini, kolegama, radnom opterećenju, navikama, organizaciji i zdravstvenoj disciplini.",
            "Ako su aktivni 6. kuća, Merkur, Mars ili Saturn, razlikovati promenu ritma rada od promene posla/firme/statusa, jer to nije ista manifestacija.",
        ],
        "forbidden_claims": [
            "Ne tvrditi dijagnozu, bolest, operaciju, otkaz ili promenu firme bez direktne potvrde odgovarajućih kuća i hard-event dozvole.",
            "Ne mešati 6. kuću sa 10. kućom: 6. govori o radu i obavezama, 10. o statusu i karijernom pravcu.",
        ],
    },
    "relationships_marriage": {
        "primary_manifestation": "partnership_marriage_contracts_public_opponents_and_one_to_one_relations",
        "supported_claims": [
            "Sme se pisati o partnerstvu, braku, javnim ugovorima, odnosu jedan-na-jedan, saradnji, suprotnoj strani i načinu pregovaranja.",
            "Ako su aktivni DSC, Venera, Mars, Mesec ili 7. kuća, razlikovati emotivni odnos, brak, ugovor, poslovnog partnera i otvoreni konflikt.",
        ],
        "forbidden_claims": [
            "Ne tvrditi ulazak u brak, razvod, prekid, novu vezu ili sudski spor bez jasnog 7/5/Venera/Mars/DSC hard-event lanca.",
            "Ne obećavati partnera ako se vidi samo potreba za odnosom ili tranzit Venere preko DSC-a.",
        ],
    },
    "crisis_transformation": {
        "primary_manifestation": "shared_money_debts_tax_inheritance_psychological_crisis_and_regeneration",
        "supported_claims": [
            "Sme se pisati o zajedničkom novcu, dugovima, kreditima, porezima, tuđim resursima, dubokoj krizi, psihološkoj transformaciji i regeneraciji.",
            "Ako su aktivni 8. kuća, Mars, Saturn, Pluton ili Mesec, razlikovati finansijski rizik, emotivnu krizu, nasledstvo, kredit i proces oporavka.",
        ],
        "forbidden_claims": [
            "Ne tvrditi smrt, nasledstvo, kredit, bankrot, operaciju ili traumatičan događaj bez najstrože hard-event potvrde.",
            "Ne koristiti 8. kuću senzacionalistički; ako nema dokaza, pisati samo o procesu dubokog pritiska i regeneracije.",
        ],
    },
    "foreign_higher_education": {
        "primary_manifestation": "foreign_affairs_higher_education_law_beliefs_travel_and_publishing",
        "supported_claims": [
            "Sme se pisati o inostranstvu, višem obrazovanju, zakonu, veri, životnoj filozofiji, putovanjima, mentorima, publikovanju i širenju vidika.",
            "Ako je aktivna 9. kuća ili Jupiter/Merkur, razlikovati učenje, put, administraciju, pravni proces i status koji dolazi preko znanja.",
        ],
        "forbidden_claims": [
            "Ne tvrditi odlazak u inostranstvo, preseljenje, vizu, sudski ishod ili završetak fakulteta bez hard-event potvrde.",
            "Ne mešati kratka putovanja 3. kuće sa inostranstvom i dalekim putevima 9. kuće.",
        ],
    },
    "career_status": {
        "primary_manifestation": "career_direction_status_authority_visibility_and_positioning",
        "supported_claims": [
            "Sme se pisati o promeni profesionalnog pravca, statusa, odnosa prema autoritetu, vidljivosti, odgovornosti i načina na koji se osoba pozicionira.",
            "Ako se ponavljaju MC, Sunce, Saturn, Jupiter ili 10. kuća, razlikovati status/poziciju od svakodnevnog posla, firme, kolega ili ugovora.",
        ],
        "forbidden_claims": [
            "Ne tvrditi siguran otkaz, promenu firme, novu poziciju ili unapređenje ako hard_event_theme_blocks ne postoji.",
            "Ne mešati promenu statusa sa promenom firme: za firmu/tim tražiti 7/11/10 potvrdu, za dnevni posao 6. kuću, za ugovor 3/7/Merkur.",
            "Ne pretvarati tranzite Marsa/Merkura u samostalan dokaz za promenu posla.",
        ],
    },
    "friends_networks": {
        "primary_manifestation": "friends_networks_audience_groups_plans_and_results_of_work",
        "supported_claims": [
            "Sme se pisati o prijateljima, mrežama, publici, grupama, podršci, planovima, rezultatima rada i ljudima koji otvaraju vrata.",
            "Ako su aktivni 11. kuća, Jupiter, Venera ili Saturn, razlikovati korisne kontakte, širenje publike, timski rad i selekciju kruga ljudi.",
        ],
        "forbidden_claims": [
            "Ne tvrditi veliki proboj, viralnost, ulazak u važnu organizaciju ili prekid prijateljstva bez direktne potvrde i hard-event dozvole.",
            "Ne predstavljati svaku društvenu aktivaciju kao poslovni uspeh bez veze sa 10/2 kućom.",
        ],
    },
    "hidden_endings_psychology": {
        "primary_manifestation": "subconscious_isolation_hidden_enemies_closure_retreat_and_spiritual_cleanup",
        "supported_claims": [
            "Sme se pisati o podsvesti, tajnama, izolaciji, skrivenim pritiscima, završecima, povlačenju, unutrašnjem čišćenju i potrebi da se osoba odmori od spoljnog pritiska.",
            "Ako su aktivni 12. kuća, Saturn, Neptun, Pluton ili Mesec, razlikovati psihološki proces, umor, tajne, izolaciju i realnu opasnost.",
        ],
        "forbidden_claims": [
            "Ne tvrditi tajnog neprijatelja, bolest, hospitalizaciju, izdaju ili opasnost bez jasnog hard-event dokaza.",
            "Ne koristiti 12. kuću za zastrašivanje; ako nema dokaza, pisati kao unutrašnji proces i potrebu za zaštitom energije.",
        ],
    },
}


def _fmt_contact(row: dict[str, Any]) -> str:
    a = row.get("point_a") or row.get("source") or "tačka"
    b = row.get("point_b") or "natal"
    aspect = row.get("aspect") or "kontakt"
    orb = row.get("orb")
    date = row.get("exact_utc") or row.get("date") or "bez tačnog datuma"
    weight = row.get("evidence_weight") or row.get("orb_class") or "proof"
    return f"{a} {aspect} {b} — orb {orb}, {weight}, {date}"


def _top_rows(rows: list[dict[str, Any]], limit: int = 4) -> list[str]:
    return [_fmt_contact(row) for row in (rows or [])[:limit]]


def _text_blob(block: dict[str, Any]) -> str:
    parts: list[str] = []
    evidence = block.get("evidence", {}) or {}
    for key in ["natal_basis", "progression_support", "solar_arc_support", "transit_timing"]:
        value = evidence.get(key, [])
        if isinstance(value, list):
            parts.extend(str(x) for x in value)
    annual = evidence.get("annual_activation") or {}
    parts.append(str(annual.get("active_house", "")))
    parts.append(str(annual.get("lord_of_year", "")))
    return " | ".join(parts)


def _contains_any(text: str, words: list[str]) -> bool:
    low = text.lower()
    return any(word.lower() in low for word in words)


def _infer_subtypes(theme: str | None, block: dict[str, Any]) -> list[str]:
    text = _text_blob(block)
    subtypes: list[str] = []
    if _contains_any(text, ["MC"]):
        subtypes.append("status_or_public_direction")
    if _contains_any(text, ["ASC"]):
        subtypes.append("personal_positioning")
    if _contains_any(text, ["DSC"]):
        subtypes.append("one_to_one_relation_or_contract")
    if _contains_any(text, ["IC"]):
        subtypes.append("home_private_base_or_family_root")
    if _contains_any(text, ["Merkur"]):
        subtypes.append("communication_papers_decision")
    if _contains_any(text, ["Venera"]):
        subtypes.append("relationship_money_values_or_attraction")
    if _contains_any(text, ["Mars"]):
        subtypes.append("action_conflict_pressure_or_cut")
    if _contains_any(text, ["Saturn"]):
        subtypes.append("delay_responsibility_boundary_or_block")
    if _contains_any(text, ["Jupiter"]):
        subtypes.append("growth_support_law_learning_or_expansion")
    if _contains_any(text, ["Uran"]):
        subtypes.append("sudden_change_disruption_or_freedom_need")
    if _contains_any(text, ["Neptun"]):
        subtypes.append("uncertainty_idealization_fatigue_or_blurred_boundary")
    if _contains_any(text, ["Pluton"]):
        subtypes.append("deep_pressure_power_shift_or_irreversible_process")
    return list(dict.fromkeys(subtypes))


def _manifestation_profile(block: dict[str, Any]) -> dict[str, Any]:
    """Classify the likely life manifestation without inventing an event."""
    theme = block.get("theme")
    level = block.get("astrological_level")
    can_claim = bool(block.get("can_claim_concrete_event"))
    counts = block.get("layer_counts", {}) or {}
    annual = (block.get("evidence", {}) or {}).get("annual_activation", {}) or {}
    active_house = annual.get("active_house")
    lord = annual.get("lord_of_year")
    rule = THEME_MANIFESTATION_RULES.get(str(theme), {})

    profile: dict[str, Any] = {
        "primary_manifestation": rule.get("primary_manifestation", "active_life_theme" if level == "main_narrative_focus" else "background_tendency"),
        "manifestation_subtypes": _infer_subtypes(str(theme), block),
        "concreteness_level": "hard_event" if can_claim else ("active_process" if level == "main_narrative_focus" else "background_pressure"),
        "can_state_as_event": can_claim,
        "must_not_overstate": not can_claim,
        "supported_claims": list(rule.get("supported_claims", [])),
        "forbidden_claims": list(rule.get("forbidden_claims", [])),
        "required_subtopics_to_cover": REQUIRED_REPORT_COVERAGE.get(str(theme), {}).get("must_cover", []),
        "section_writing_rule": REQUIRED_REPORT_COVERAGE.get(str(theme), {}).get("writing_rule"),
        "discrimination_basis": {
            "annual_active_house": active_house,
            "lord_of_year": lord,
            "has_progression": counts.get("primary_progression", 0) > 0,
            "has_solar_arc": counts.get("primary_solar_arc", 0) > 0,
            "has_solar_house_activation": counts.get("solar", 0) > 0,
            "has_annual_activation": counts.get("annual", 0) > 0,
            "has_timing": counts.get("transit", 0) > 0 or counts.get("fast_timing", 0) > 0 or counts.get("lunar", 0) > 0,
        },
    }

    if theme == "career_status":
        text = _text_blob(block)
        if _contains_any(text, ["6", "Merkur", "Mars", "rutina"]):
            profile["manifestation_subtypes"].append("daily_work_or_role_load")
        if _contains_any(text, ["Merkur", "3", "7", "ugovor", "papir"]):
            profile["manifestation_subtypes"].append("contract_papers_or_negotiation_channel")
        if _contains_any(text, ["DSC", "7", "11", "Uran", "Pluton"]):
            profile["manifestation_subtypes"].append("company_team_or_external_party_only_if_confirmed")
        if _contains_any(text, ["MC", "Sunce", "Saturn", "Jupiter"]) and counts.get("annual", 0) > 0 and counts.get("primary_solar_arc", 0) > 0:
            profile["concreteness_level"] = "career_status_process" if not can_claim else "career_hard_event"

    if not profile["supported_claims"]:
        profile["supported_claims"].append("Sme se opisati samo u okviru dodeljenog nivoa: glavna tema, sporedna tendencija ili blokirano.")
    profile["forbidden_claims"].append("Ne tvrditi konkretan događaj ako can_claim_concrete_event nije true.")
    profile["manifestation_subtypes"] = list(dict.fromkeys(profile["manifestation_subtypes"]))
    return profile


def _theme_block(theme_key: str, theme: dict[str, Any]) -> dict[str, Any]:
    status = theme.get("status")
    permission = theme.get("interpretation_permission")
    allowed = status in ALLOWED_STATUSES or permission == "allowed"
    blocked = status in BLOCKED_STATUSES or permission == "blocked"
    block = {
        "theme": theme_key,
        "label": theme.get("label"),
        "status": status,
        "confirmation_score": theme.get("confirmation_score"),
        "raw_confirmation_score": theme.get("raw_confirmation_score"),
        "permission": permission,
        "can_claim_concrete_event": allowed,
        "must_be_cautious": not allowed and not blocked,
        "blocked_for_event_claims": blocked,
        "layer_counts": theme.get("layer_counts"),
        "evidence": {
            "natal_basis": _top_rows(theme.get("natal_basis", []), 3),
            "annual_activation": theme.get("annual_activation"),
            "solar_return_support": theme.get("solar_return_support", [])[:4],
            "progression_support": _top_rows(theme.get("progression_support", []), 4),
            "solar_arc_support": _top_rows(theme.get("solar_arc_support", []), 4),
            "transit_timing": _top_rows(theme.get("transit_timing", []), 6),
            "lunar_triggers": theme.get("lunar_triggers", [])[:4],
        },
    }
    block["manifestation_profile"] = _manifestation_profile(block)
    return block


def _enrich_group_item(item: dict[str, Any], themes: dict[str, Any]) -> dict[str, Any]:
    theme_key = item.get("theme")
    source_theme = themes.get(theme_key, {}) if theme_key else {}
    block = _theme_block(theme_key, source_theme) if theme_key and source_theme else dict(item)
    block.update({k: v for k, v in item.items() if v is not None})
    block["manifestation_profile"] = _manifestation_profile(block)
    return block


def _build_fallback_theme_groups(themes: dict[str, Any], ranked: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    hard_event_blocks: list[dict[str, Any]] = []
    narrative_focus_blocks: list[dict[str, Any]] = []
    supporting_blocks: list[dict[str, Any]] = []
    blocked_blocks: list[dict[str, Any]] = []

    for item in ranked:
        key = item.get("theme")
        if not key or key not in themes:
            continue
        block = _theme_block(key, themes[key])
        counts = block.get("layer_counts") or {}
        score = float(block.get("confirmation_score") or 0)
        structural_layers = sum(1 for layer in ["annual", "solar", "progression", "solar_arc"] if counts.get(layer, 0) > 0)
        has_core_natal = counts.get("core_natal", 0) > 0
        has_annual_or_solar = counts.get("annual", 0) > 0 or counts.get("solar", 0) > 0
        has_direction = counts.get("primary_progression", 0) > 0 or counts.get("primary_solar_arc", 0) > 0
        if block["can_claim_concrete_event"]:
            block["astrological_level"] = "hard_event_allowed"
            block["narrative_mode"] = "concrete_event_allowed"
            block["manifestation_profile"] = _manifestation_profile(block)
            hard_event_blocks.append(block)
        elif has_core_natal and has_annual_or_solar and has_direction and score >= 5.25 and structural_layers >= 2:
            block["astrological_level"] = "main_narrative_focus"
            block["narrative_mode"] = "main_theme_without_event_claim"
            block["wording_rule"] = "Formulisati kao glavnu aktiviranu oblast, proces, pritisak ili potrebu za odlukom; bez tvrdnje da će se događaj sigurno desiti."
            block["manifestation_profile"] = _manifestation_profile(block)
            narrative_focus_blocks.append(block)
        elif not block["blocked_for_event_claims"]:
            block["astrological_level"] = "supporting_tendency"
            block["narrative_mode"] = "brief_tendency_only"
            block["wording_rule"] = "Pomenuti kratko kao sporednu tendenciju ili pozadinski pritisak."
            block["manifestation_profile"] = _manifestation_profile(block)
            supporting_blocks.append(block)
        else:
            blocked_blocks.append({"theme": key, "label": block.get("label"), "status": block.get("status"), "rule": "Do not claim concrete event."})
    return {
        "hard_event_theme_blocks": hard_event_blocks,
        "narrative_focus_theme_blocks": narrative_focus_blocks[:4],
        "supporting_tendency_theme_blocks": narrative_focus_blocks[4:] + supporting_blocks,
        "blocked_theme_blocks": blocked_blocks,
    }


def _cardinal_signature(cautious_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    all_blocks = sorted(cautious_blocks, key=lambda x: float(x.get("confirmation_score") or 0), reverse=True)
    focus = [b for b in all_blocks if b.get("astrological_level") == "main_narrative_focus"]
    supporting = [b for b in all_blocks if b.get("astrological_level") == "supporting_tendency"]
    return {
        "main_life_focus": [
            {
                "theme": block.get("theme"),
                "label": block.get("label"),
                "primary_manifestation": (block.get("manifestation_profile") or {}).get("primary_manifestation"),
                "concreteness_level": (block.get("manifestation_profile") or {}).get("concreteness_level"),
            }
            for block in focus[:4]
        ],
        "background_life_pressures": [
            {
                "theme": block.get("theme"),
                "label": block.get("label"),
                "primary_manifestation": (block.get("manifestation_profile") or {}).get("primary_manifestation"),
            }
            for block in supporting[:6]
        ],
        "writer_instruction": "Pre pisanja izveštaja prvo izvuci ove glavne potpise karte/perioda. Narativ mora da se gradi oko dominantnih tema, a sporedne teme ne smeju pojesti glavni fokus.",
    }


def build_interpretation_payload(data: dict[str, Any], client_name: str | None = None, focus_question: str | None = None) -> dict[str, Any]:
    matrix = data.get("confirmation_matrix") or {}
    themes = matrix.get("themes") or {}
    ranked = matrix.get("ranked_themes") or []
    month_by_month = data.get("month_by_month") or {}

    source_groups = matrix.get("astrological_theme_groups") or {}
    if source_groups:
        hard_event_blocks = [_enrich_group_item(item, themes) for item in source_groups.get("hard_event_theme_blocks", [])]
        narrative_focus_blocks = [_enrich_group_item(item, themes) for item in source_groups.get("narrative_focus_theme_blocks", [])]
        supporting_blocks = [_enrich_group_item(item, themes) for item in source_groups.get("supporting_tendency_theme_blocks", [])]
        blocked_blocks = source_groups.get("blocked_theme_blocks", [])
    else:
        fallback_groups = _build_fallback_theme_groups(themes, ranked)
        hard_event_blocks = fallback_groups["hard_event_theme_blocks"]
        narrative_focus_blocks = fallback_groups["narrative_focus_theme_blocks"]
        supporting_blocks = fallback_groups["supporting_tendency_theme_blocks"]
        blocked_blocks = fallback_groups["blocked_theme_blocks"]

    cautious_blocks = narrative_focus_blocks + supporting_blocks
    months = month_by_month.get("months", []) or []
    top_months = sorted(months, key=lambda m: m.get("month_intensity_score", 0), reverse=True)[:8]

    return {
        "success": True,
        "schema": "ASTRO_ARIES_PREDICTIVE_INTERPRETATION_PAYLOAD_V1",
        "client_name": client_name,
        "focus_question": focus_question,
        "rules": {
            "source": "Interpret only from predictive calculation JSON.",
            "method_hierarchy": "Natal promise first; annual profection and solar return frame the year; progressions and solar arc confirm development; transits and lunar returns time the manifestation only.",
            "allowed": "Concrete event wording allowed only for hard_event_theme_blocks / confirmation_matrix status strong.",
            "manifestation_discrimination": "The writing layer must use manifestation_profile for every life sphere. It must distinguish subtypes such as job/company/position, income/shared money, home/relocation, relationship/marriage/contract, health habit/health event, learning/legal/foreign travel. If a subtype is forbidden, it must not be claimed.",
            "mandatory_coverage": "The writing layer must cover every section and subtopic listed in required_report_coverage. The questions do not need to appear as questions, but every subtopic must be answered inside the appropriate life sphere.",
            "cardinal_signature": "Before writing, identify what carries the chart/period: use chart_signature.main_life_focus as the spine of the report, then add supporting pressures without letting them dominate.",
            "narrative_focus": "Main narrative focus requires natal promise + annual or solar activation + progression/solar-arc direction + at least two structural layers. Write it as an active theme/process, not as a guaranteed event.",
            "supporting_tendency": "Supporting themes may be mentioned briefly as tendencies, background pressure or timing sensitivity only; they are not report headline claims.",
            "insufficient": "Insufficient themes must not be turned into predictions.",
            "transit_rule": "Transits are timing, not standalone proof.",
            "tone": "Serbian, professional astrologer voice, direct but not fatalistic.",
        },
        "required_report_coverage": REQUIRED_REPORT_COVERAGE,
        "chart_signature": _cardinal_signature(cautious_blocks),
        "allowed_theme_blocks": hard_event_blocks[:8],
        "hard_event_theme_blocks": hard_event_blocks[:8],
        "narrative_focus_theme_blocks": narrative_focus_blocks[:4],
        "supporting_tendency_theme_blocks": supporting_blocks[:8],
        "cautious_theme_blocks": cautious_blocks[:10],
        "blocked_theme_blocks": blocked_blocks[:12],
        "top_timing_months": top_months,
        "draft_structure": [
            "0. Uvod: kratak, ljudski, bez tehničkog pretrpavanja i bez dubinskih tvrdnji.",
            "1-12. Natalne životne sfere: svaka sfera mora pokriti sve must_cover podteme iz required_report_coverage, bez taksativnog nabrajanja pitanja.",
            "13. Prediktivna šema: objasniti šta je aktivirano i šta nije dovoljno potvrđeno.",
            "14. Dominanta 12 meseci: chart_signature.main_life_focus + narrative_focus_theme_blocks.",
            "15. Konkretna dešavanja: samo hard_event_theme_blocks; ako su prazni, jasno reći da nema dovoljno tvrdog dokaza.",
            "16. Hronologija: top_timing_months i tranziti kao tajming potvrđenih tema, bez izmišljanja praznog hoda.",
            "17. Direktni odgovori: da/ne/delimično + kada + kako + šta sada; bez lažne nade.",
            "18. Završna reč: potpis izveštaja, bez novih tvrdnji.",
        ],
    }


def interpret_predictive_payload(request: PredictiveInterpretRequest) -> dict[str, Any]:
    payload = build_interpretation_payload(request.predictive_data, request.client_name, request.focus_question)
    return payload
