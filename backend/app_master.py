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
    from master_assistant import AssistantRequest, assistant_respond_payload

BASE_DIR = Path(__file__).resolve().parent.parent


@app.post("/assistant/respond")
def assistant_respond(request: AssistantRequest):
    return assistant_respond_payload(request)


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
