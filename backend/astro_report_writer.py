from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PredictiveReportWriteRequest(BaseModel):
    interpretation_payload: dict[str, Any]
    client_context: dict[str, Any] | None = None
    report_type: str = "predictive_12_months"


def _clean(text: Any) -> str:
    return str(text or "").strip()


def _join_labels(blocks: list[dict[str, Any]]) -> str:
    labels = [_clean(block.get("label")) for block in blocks if _clean(block.get("label"))]
    if not labels:
        return "nema izdvojenih tema"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " i " + labels[-1]


def _client_phrase(context: dict[str, Any] | None) -> str:
    if not context:
        return ""
    name = _clean(context.get("name") or context.get("client_name"))
    if name:
        return f" za {name}"
    return ""


def _claim_lines(block: dict[str, Any], limit: int = 2) -> str:
    profile = block.get("manifestation_profile") or {}
    claims = profile.get("supported_claims") or []
    return " ".join(_clean(item) for item in claims[:limit] if _clean(item))


def _forbidden_lines(block: dict[str, Any], limit: int = 2) -> str:
    profile = block.get("manifestation_profile") or {}
    claims = profile.get("forbidden_claims") or []
    return " ".join(_clean(item) for item in claims[:limit] if _clean(item))


def _evidence_summary(block: dict[str, Any]) -> str:
    evidence = block.get("evidence") or {}
    annual = evidence.get("annual_activation") or {}
    score = block.get("confirmation_score")
    raw = block.get("raw_confirmation_score")
    profile = block.get("manifestation_profile") or {}
    primary = profile.get("primary_manifestation") or "aktivna tema"
    subtypes = profile.get("manifestation_subtypes") or []
    subtype_text = ", ".join(subtypes[:4]) if subtypes else "bez dodatnog podtipa"
    annual_text = "godišnja aktivacija postoji" if annual.get("activated") else "bez godišnje aktivacije"
    return f"Tehnički nivo: {primary}; {annual_text}; potvrda {score} / sirovo {raw}; podtipovi: {subtype_text}."


def _write_intro(payload: dict[str, Any], context: dict[str, Any] | None) -> str:
    focus = payload.get("chart_signature", {}).get("main_life_focus", []) or []
    focus_labels = _join_labels(focus)
    client = _client_phrase(context)
    return (
        f"Ovaj prediktivni pregled{client} nije zamišljen kao opšti horoskop, niti kao tekst koji svima može da se zalepi bez razlike. "
        f"Ovde se ne kreće od želje da nešto zvuči lepo, već od onoga što je karta zaista aktivirala. "
        f"Glavni ton perioda se gradi oko sledećih oblasti: {focus_labels}. "
        "Sve što nije dovoljno potvrđeno biće imenovano kao oprez, pritisak ili pozadinska tema, a ne kao siguran događaj."
    )


def _write_dominant_themes(payload: dict[str, Any]) -> str:
    blocks = payload.get("narrative_focus_theme_blocks") or []
    if not blocks:
        return (
            "U ovom paketu nema dovoljno izdvojenih glavnih narativnih tema koje bi smele da nose ceo izveštaj. "
            "To ne znači da se ništa ne dešava, već da sistem ne sme da pravi veliku priču tamo gde nema dovoljno slojeva potvrde."
        )
    paragraphs: list[str] = []
    for block in blocks:
        label = _clean(block.get("label"))
        evidence = _evidence_summary(block)
        supported = _claim_lines(block)
        forbidden = _forbidden_lines(block, 1)
        paragraphs.append(
            f"{label} je jedna od glavnih osa perioda. {evidence} "
            f"U tumačenju se ova oblast sme opisati kao aktivan proces, pritisak i tema kroz koju osoba mora jasnije da se postavi. {supported} "
            f"Granica je jasna: {forbidden}"
        )
    return "\n\n".join(paragraphs)


def _write_hard_events(payload: dict[str, Any]) -> str:
    blocks = payload.get("hard_event_theme_blocks") or []
    if not blocks:
        return (
            "Za ovaj prediktivni paket trenutno nema tema koje su prošle prag za tvrd hard-event zaključak. "
            "Zato se ne sme pisati da se nešto sigurno dešava, niti se sme izmišljati događaj samo zato što postoji jaka atmosfera ili više tranzitnih okidača. "
            "Ovo je važan profesionalni deo izveštaja: karta pokazuje aktivne procese, ali ne daje dovoljno dozvole za rečenice tipa 'sigurno menjaš posao', 'sigurno se seliš', 'sigurno ulaziš u brak' ili 'sigurno dobijaš novac'."
        )
    paragraphs: list[str] = []
    for block in blocks:
        label = _clean(block.get("label"))
        supported = _claim_lines(block, 3)
        evidence = _evidence_summary(block)
        paragraphs.append(f"{label}: ovde je dozvoljena konkretnija formulacija događaja. {evidence} {supported}")
    return "\n\n".join(paragraphs)


def _write_supporting_tendencies(payload: dict[str, Any]) -> str:
    blocks = payload.get("supporting_tendency_theme_blocks") or []
    if not blocks:
        return "Sporedne tendencije nisu posebno naglašene u ovom paketu. Glavni fokus ostaje na temama koje su već izdvojene kao noseće."
    paragraphs: list[str] = []
    for block in blocks[:8]:
        label = _clean(block.get("label"))
        evidence = _evidence_summary(block)
        supported = _claim_lines(block, 1)
        forbidden = _forbidden_lines(block, 1)
        paragraphs.append(
            f"{label} postoji kao sporedni pritisak, ali ne kao glavna tvrdnja izveštaja. {evidence} {supported} "
            f"Zato se ovde ne ide dalje od oprezne formulacije: {forbidden}"
        )
    return "\n\n".join(paragraphs)


def _write_timeline(payload: dict[str, Any]) -> str:
    months = payload.get("top_timing_months") or []
    if not months:
        return (
            "U dostavljenom payload-u nema dovoljno izdvojenih mesečnih blokova za pouzdanu hronologiju. "
            "U tom slučaju se ne izmišljaju datumi: piše se samo o glavnim aktiviranim temama, bez lažne preciznosti."
        )
    lines: list[str] = []
    for month in months[:8]:
        label = _clean(month.get("month") or month.get("label") or month.get("month_label"))
        score = month.get("month_intensity_score")
        if not label:
            label = _clean(month.get("start") or month.get("date") or "period")
        lines.append(
            f"{label}: ovaj period ima intenzitet {score}. Koristi se kao vremenski marker, ne kao samostalan dokaz događaja. "
            "Tumači se samo u vezi sa glavnim i sporednim temama koje su već potvrđene u payload-u."
        )
    return "\n\n".join(lines)


def _write_direct_answers(payload: dict[str, Any], context: dict[str, Any] | None) -> str:
    questions = []
    if context:
        raw = context.get("questions") or context.get("direct_questions") or []
        if isinstance(raw, str):
            questions = [raw]
        elif isinstance(raw, list):
            questions = [str(q) for q in raw if str(q).strip()]
    if not questions:
        return (
            "Direktna pitanja klijenta nisu posebno dostavljena u ovom pozivu. Kada postoje, svaki odgovor mora početi jasno: da, ne ili delimično. "
            "Zatim se navodi vremenski okvir ako postoji, mehanizam dešavanja i praktična preporuka. Ako payload ne potvrđuje pitanje, odgovor mora reći da nema dovoljno dokaza."
        )
    answers: list[str] = []
    for question in questions:
        answers.append(
            f"Pitanje: {question}\n"
            "Odgovor mora biti izveden isključivo iz hard_event_theme_blocks, narrative_focus_theme_blocks i manifestation_profile pravila. "
            "Ako za ovo pitanje ne postoji direktna potvrda, ne daje se utešna verzija, već se jasno kaže da karta za ovaj period ne daje dovoljno dokaza za tvrdnju."
        )
    return "\n\n".join(answers)


def _write_final_word(payload: dict[str, Any]) -> str:
    focus = payload.get("chart_signature", {}).get("main_life_focus", []) or []
    labels = _join_labels(focus)
    return (
        f"Završna poruka ovog pregleda je jednostavna: period se ne čita kroz sve oblasti jednako, već kroz ono što zaista nosi kartu — {labels}. "
        "Tu treba uložiti najviše svesti, discipline i odluke. Sporedne teme ne treba ignorisati, ali ne smeju preuzeti glavnu scenu ako za to nemaju dokaz. "
        "Ovaj izveštaj zato ne obećava ono što karta ne potvrđuje; njegova vrednost je u tome što odvaja stvarni signal od astrološke buke."
    )


def _coverage_check(payload: dict[str, Any]) -> dict[str, Any]:
    coverage = payload.get("required_report_coverage") or {}
    return {
        "required_section_count": len(coverage),
        "required_sections": list(coverage.keys()),
        "rule": "Every must_cover item must be addressed in the final long-form report. This first writer version exposes the map and drafts major predictive sections.",
        "missing_policy": "If a subtopic has no support in the supplied data, the report must explicitly say it is not confirmed instead of silently skipping it.",
    }


def write_predictive_report_payload(request: PredictiveReportWriteRequest) -> dict[str, Any]:
    payload = request.interpretation_payload or {}
    context = request.client_context or {}
    sections = {
        "intro": _write_intro(payload, context),
        "dominant_period_themes": _write_dominant_themes(payload),
        "hard_event_claims": _write_hard_events(payload),
        "supporting_tendencies": _write_supporting_tendencies(payload),
        "timing_overview": _write_timeline(payload),
        "direct_answers": _write_direct_answers(payload, context),
        "final_word": _write_final_word(payload),
    }
    full_text = "\n\n".join(
        [
            "UVOD\n" + sections["intro"],
            "DOMINANTNE TEME PERIODA\n" + sections["dominant_period_themes"],
            "KONKRETNA DEŠAVANJA\n" + sections["hard_event_claims"],
            "SPOREDNE TENDENCIJE\n" + sections["supporting_tendencies"],
            "VREMENSKI PREGLED\n" + sections["timing_overview"],
            "DIREKTNI ODGOVORI\n" + sections["direct_answers"],
            "ZAVRŠNA REČ\n" + sections["final_word"],
        ]
    )
    return {
        "success": True,
        "schema": "ASTRO_ARIES_WRITTEN_PREDICTIVE_REPORT_V1",
        "report_type": request.report_type,
        "sections": sections,
        "full_text": full_text,
        "qa": _coverage_check(payload),
        "source_payload_schema": payload.get("schema"),
        "note": "First controlled writer layer. It writes from the interpretation payload only and does not create new astrological claims.",
    }
