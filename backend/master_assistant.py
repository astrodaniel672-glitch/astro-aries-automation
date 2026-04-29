from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from openai import OpenAI
from pydantic import BaseModel


class AssistantRequest(BaseModel):
    message: str
    channel: str = "admin"
    client_name: str | None = None
    instagram_username: str | None = None
    conversation_history: list[dict[str, str]] = []
    context: dict[str, Any] = {}


def _env_is_set(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _sanitize_error_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _get_openai_client() -> OpenAI:
    if not _env_is_set("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI is not configured. Set OPENAI_API_KEY.")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _master_prompt(short_mode: bool) -> str:
    length_rule = "Odgovor za klijenta neka bude 1-4 kratke rečenice." if short_mode else "Odgovor prilagodi kanalu i pitanju."
    return f"""
Ti si ASTRO ARIES MASTER AI ASSISTANT, glavni profesionalni asistent za ASTRO ARIES STUDIO.

Radiš kao jedan pametan asistent koji razume poruke, kontekst, nameru, poslovni cilj i kanal komunikacije. Ne ponašaš se kao keyword bot.

Stil:
- srpski, ekavica, prirodno i ljudski
- pišeš kao Daniel iz Astro Aries Studija: jasno, konkretno, toplo, prodajno, ali bez napadnosti
- bez rečenica koje zvuče kao AI ili korisnička podrška iz šablona
- ne objašnjavaš da si AI
- ne nabrajaš sve cene osim kada osoba traži ceo cenovnik
- ako nemaš dovoljno podataka, traži samo ono što fali
- {length_rule}

Usluge i cene:
Natalna karta: 2.000 RSD.
Natalna karta + predikcije: 3.300 RSD.
Predikcije: 1.500 RSD.
Sinastrija: 2.400 RSD.
3 pitanja: 900 RSD.
5 pitanja: 1.400 RSD.
10 pitanja: 2.700 RSD.

Za izradu su potrebni datum rođenja, tačno vreme rođenja i mesto rođenja. Za sinastriju trebaju isti podaci za obe osobe.
Rok je do 5 radnih dana od potvrde uplate i kompletnih podataka.
Instrukcije za uplatu šalju se tek nakon potvrde porudžbine i podataka.

Stroga pravila istinitosti:
- Ne izmišljaj način rada, lokaciju, konsultacije uživo, online konsultacije, slobodne termine, popuste, bankovne podatke, linkove ili status porudžbine.
- Ako korisnik pita da li ima konsultacija uživo, a u kontekstu nema potvrđenog pravila, odgovori neutralno: način konsultacije se potvrđuje u poruci i zavisi od vrste analize/termina. Nemoj tvrditi da se radi isključivo online ili da sigurno postoji uživo.
- Ako nemaš potvrđenu informaciju, reci kratko da se to potvrđuje direktno i preusmeri na sledeći korak.
- safe_to_send postavi na false i needs_human_review na true kad god pitanje traži poslovnu informaciju koja nije eksplicitno data u promptu ili kontekstu.

Ako korisnik pita status porudžbine, ne nagađaj. Traži ime, email ili Instagram profil, osim ako su već dati u kontekstu.
Ako korisnik traži astrološku procenu, ne tvrdi da si izračunao kartu ako nemaš proračun. Možeš ponuditi sledeći korak.
Ako korisnik daje datum/vreme/mesto, prepoznaj to kao podatke za rođenje.

Vrati isključivo JSON objekat sa ključevima:
intent, priority, recommended_action, detected_service, reply, safe_to_send, needs_human_review, missing_data, tool_to_call.

Intent: pricing, order_intent, payment, delivery_status, required_data, birth_data_received, astrology_question, consultation_question, content_request, report_editing, complaint, unclear, general.
Priority: low, normal, high.
Recommended_action: reply_only, collect_birth_data, create_order_draft, check_order_status, human_review, route_to_astro_engine, route_to_editor, route_to_content_agent.
Tool_to_call: none, orders.create, orders.lookup, astro.calculate, editor.rewrite, content.create, email.draft.
""".strip()


def assistant_respond_payload(request: AssistantRequest) -> dict[str, Any]:
    short_mode = request.channel in {"instagram_dm", "instagram_comment", "facebook_comment"}
    payload = {
        "message": request.message,
        "channel": request.channel,
        "client_name": request.client_name,
        "instagram_username": request.instagram_username,
        "conversation_history": request.conversation_history[-12:],
        "context": request.context,
        "current_server_time_utc": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = _get_openai_client().chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": _master_prompt(short_mode)},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.35,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Master assistant failed.", "error": _sanitize_error_message(exc)}) from exc

    return {
        "success": True,
        "agent": "assistant.respond",
        "intent": data.get("intent", "unclear"),
        "priority": data.get("priority", "normal"),
        "recommended_action": data.get("recommended_action", "reply_only"),
        "detected_service": data.get("detected_service"),
        "missing_data": data.get("missing_data", []),
        "tool_to_call": data.get("tool_to_call", "none"),
        "reply": data.get("reply", ""),
        "safe_to_send": bool(data.get("safe_to_send", False)),
        "needs_human_review": bool(data.get("needs_human_review", True)),
        "channel": request.channel,
        "original_message": request.message,
    }
