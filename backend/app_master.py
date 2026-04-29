from pathlib import Path

from fastapi.responses import FileResponse

try:
    from backend.app import app
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
    from app import app
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

BASE_DIR = Path(__file__).resolve().parent.parent


@app.post("/assistant/respond")
def assistant_respond(request: AssistantRequest):
    extraction = extract_payload(
        ExtractRequest(
            message=request.message,
            channel=request.channel,
            conversation_history=request.conversation_history,
            current_state=request.context.get("state", {}) if request.context else {},
        )
    )
    merged_state = merge_state(request.context.get("state", {}) if request.context else {}, extraction)
    enriched_context = dict(request.context or {})
    enriched_context["extraction"] = extraction
    enriched_context["state"] = merged_state
    enriched_request = AssistantRequest(
        message=request.message,
        channel=request.channel,
        client_name=request.client_name,
        instagram_username=request.instagram_username,
        conversation_history=request.conversation_history,
        context=enriched_context,
    )
    response = assistant_respond_payload(enriched_request)
    response["extraction"] = extraction
    response["state"] = merged_state
    return response


@app.post("/intent/extract")
def intent_extract(request: ExtractRequest):
    extraction = extract_payload(request)
    extraction["state"] = merge_state(request.current_state, extraction)
    return extraction


@app.post("/memory/message")
def memory_save_message(request: ConversationMessage):
    return save_message(request)


@app.post("/memory/load")
def memory_load(request: ConversationLoadRequest):
    return load_conversation(request)


@app.post("/memory/state")
def memory_update_state(request: ConversationStateUpdate):
    return update_state(request)


@app.get("/master")
def master_panel() -> FileResponse:
    panel_path = BASE_DIR / "master_panel.html"
    return FileResponse(panel_path)
