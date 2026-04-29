from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from openai import OpenAI
from pydantic import BaseModel


class ExtractRequest(BaseModel):
    message: str
    channel: str = "instagram_dm"
    conversation_history: list[dict[str, str]] = []
    current_state: dict[str, Any] = {}


def _env_is_set(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _sanitize_error(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _client() -> OpenAI:
    if not _env_is_set("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI is not configured. Set OPENAI_API_KEY.")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


EXTRACTOR_PROMPT = """
Ti si strogi parser za ASTRO ARIES STUDIO. Ne pišeš odgovor klijentu. Tvoj posao je da iz poruke i istorije izvučeš podatke i stanje razgovora.

Vrati isključivo JSON objekat.

Polja:
- intent: pricing | order_intent | payment | delivery_status | birth_data | astrology_question | relationship_marriage_question | consultation_question | discount | free_reading | complaint | unclear | general
- service: natal | natal_predikcije | predikcije | sinastrija | questions | unknown | null
- topic: marriage | love | children | career | money | health | relocation | general | null
- birth_date: string ili null
- birth_time: string ili null
- birth_place: string ili null
- partner_birth_date: string ili null
- partner_birth_time: string ili null
- partner_birth_place: string ili null
- country_or_region: serbia | abroad | unknown
- email: string ili null
- wants_to_pay: boolean
- wants_to_order: boolean
- user_confirmed: boolean
- asked_same_topic_again: boolean
- missing_data: array
- extracted_facts: object
- next_action: collect_birth_data | collect_partner_data | explain_price | explain_payment | create_order_draft | answer_ethically | route_to_astro_engine | human_review | reply_only

Pravila:
- Ako korisnik pošalje samo grad/mesto, tretiraj to kao birth_place ako kontekst govori o natalu/podacima.
- Ako korisnik pita o braku, udaji, ženidbi, partneru ili vezi, intent je relationship_marriage_question, topic marriage/love.
- Ako nema preciznih natalnih podataka, missing_data mora sadržati birth_date, birth_time, birth_place.
- Ako korisnik već pita istu temu drugi put, asked_same_topic_again true.
- Ne izmišljaj podatke.
""".strip()


def extract_payload(request: ExtractRequest) -> dict[str, Any]:
    payload = {
        "message": request.message,
        "channel": request.channel,
        "conversation_history": request.conversation_history[-12:],
        "current_state": request.current_state,
        "current_server_time_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        response = _client().chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": EXTRACTOR_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Intent extraction failed.", "error": _sanitize_error(exc)}) from exc

    defaults = {
        "intent": "unclear",
        "service": None,
        "topic": None,
        "birth_date": None,
        "birth_time": None,
        "birth_place": None,
        "partner_birth_date": None,
        "partner_birth_time": None,
        "partner_birth_place": None,
        "country_or_region": "unknown",
        "email": None,
        "wants_to_pay": False,
        "wants_to_order": False,
        "user_confirmed": False,
        "asked_same_topic_again": False,
        "missing_data": [],
        "extracted_facts": {},
        "next_action": "reply_only",
    }
    defaults.update(data)
    return {"success": True, "agent": "intent.extract", **defaults}


def merge_state(current_state: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    state = dict(current_state or {})
    for key in [
        "service",
        "topic",
        "birth_date",
        "birth_time",
        "birth_place",
        "partner_birth_date",
        "partner_birth_time",
        "partner_birth_place",
        "country_or_region",
        "email",
    ]:
        value = extraction.get(key)
        if value not in (None, "", "unknown"):
            state[key] = value
    state["last_intent"] = extraction.get("intent")
    state["last_next_action"] = extraction.get("next_action")
    state["last_missing_data"] = extraction.get("missing_data", [])
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return state
