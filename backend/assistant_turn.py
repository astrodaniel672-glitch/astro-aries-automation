from __future__ import annotations

from typing import Any

from pydantic import BaseModel

try:
    from backend.conversation_memory import (
        ConversationLoadRequest,
        ConversationMessage,
        ConversationStateUpdate,
        load_conversation,
        save_message,
        update_state,
    )
    from backend.intent_extractor import ExtractRequest, extract_payload, merge_state
    from backend.master_assistant import AssistantRequest, assistant_respond_payload
except ModuleNotFoundError:
    from conversation_memory import (
        ConversationLoadRequest,
        ConversationMessage,
        ConversationStateUpdate,
        load_conversation,
        save_message,
        update_state,
    )
    from intent_extractor import ExtractRequest, extract_payload, merge_state
    from master_assistant import AssistantRequest, assistant_respond_payload


class AssistantTurnRequest(BaseModel):
    message: str
    channel: str = "instagram_dm"
    conversation_id: str | None = None
    external_user_id: str | None = None
    instagram_username: str | None = None
    client_name: str | None = None
    context: dict[str, Any] = {}


def _history_for_ai(memory: dict[str, Any]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for item in memory.get("messages", []):
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history[-12:]


def _missing_fields(state: dict[str, Any], extraction: dict[str, Any]) -> list[str]:
    intent = extraction.get("intent") or state.get("last_intent")
    service = state.get("service") or extraction.get("service")
    needs_birth = intent in {
        "birth_data",
        "astrology_question",
        "relationship_marriage_question",
        "order_intent",
        "payment",
    } or service in {"natal", "natal_predikcije", "predikcije", "questions", "sinastrija"}

    missing: list[str] = []
    if needs_birth:
        if not state.get("birth_date"):
            missing.append("birth_date")
        if not state.get("birth_time"):
            missing.append("birth_time")
        if not state.get("birth_place"):
            missing.append("birth_place")

    if service == "sinastrija":
        if not state.get("partner_birth_date"):
            missing.append("partner_birth_date")
        if not state.get("partner_birth_time"):
            missing.append("partner_birth_time")
        if not state.get("partner_birth_place"):
            missing.append("partner_birth_place")

    return missing


def _next_step(state: dict[str, Any], extraction: dict[str, Any], missing: list[str]) -> str:
    intent = extraction.get("intent")
    if missing:
        return "collect_missing_data"
    if intent in {"relationship_marriage_question", "astrology_question"}:
        return "offer_service_or_human_review"
    if intent == "payment" or extraction.get("wants_to_pay"):
        return "prepare_payment_instructions"
    if extraction.get("wants_to_order"):
        return "create_order_draft"
    return extraction.get("next_action") or "reply_only"


def assistant_turn_payload(request: AssistantTurnRequest) -> dict[str, Any]:
    memory = load_conversation(
        ConversationLoadRequest(
            conversation_id=request.conversation_id,
            channel=request.channel,
            external_user_id=request.external_user_id,
            instagram_username=request.instagram_username,
            limit=12,
        )
    )
    conversation = memory.get("conversation") or {}
    current_state = dict(conversation.get("state") or {})
    history = _history_for_ai(memory)

    extraction = extract_payload(
        ExtractRequest(
            message=request.message,
            channel=request.channel,
            conversation_history=history,
            current_state=current_state,
        )
    )
    state = merge_state(current_state, extraction)
    missing = _missing_fields(state, extraction)
    state["missing_fields"] = missing
    state["next_step"] = _next_step(state, extraction, missing)

    enriched_context = dict(request.context or {})
    enriched_context["state"] = state
    enriched_context["extraction"] = extraction
    enriched_context["backend_truth"] = {
        "missing_fields": missing,
        "next_step": state["next_step"],
        "do_not_ask_for_existing_fields": True,
    }

    response = assistant_respond_payload(
        AssistantRequest(
            message=request.message,
            channel=request.channel,
            client_name=request.client_name,
            instagram_username=request.instagram_username,
            conversation_history=history,
            context=enriched_context,
        )
    )

    conversation_id = memory["conversation_id"]
    save_message(
        ConversationMessage(
            conversation_id=conversation_id,
            channel=request.channel,
            external_user_id=request.external_user_id,
            instagram_username=request.instagram_username,
            client_name=request.client_name,
            role="user",
            content=request.message,
            metadata={"extraction": extraction},
        )
    )
    save_message(
        ConversationMessage(
            conversation_id=conversation_id,
            channel=request.channel,
            external_user_id=request.external_user_id,
            instagram_username=request.instagram_username,
            client_name=request.client_name,
            role="assistant",
            content=response.get("reply", ""),
            metadata={"response": response},
        )
    )
    update_state(
        ConversationStateUpdate(
            conversation_id=conversation_id,
            channel=request.channel,
            external_user_id=request.external_user_id,
            instagram_username=request.instagram_username,
            client_name=request.client_name,
            state=state,
        )
    )

    response["conversation_id"] = conversation_id
    response["state"] = state
    response["extraction"] = extraction
    response["memory_saved"] = True
    return response
