from pathlib import Path

from fastapi.responses import FileResponse

try:
    from backend.app import app
    from backend.master_assistant import AssistantRequest, assistant_respond_payload
except ModuleNotFoundError:
    from app import app
    from master_assistant import AssistantRequest, assistant_respond_payload

BASE_DIR = Path(__file__).resolve().parent.parent


@app.post("/assistant/respond")
def assistant_respond(request: AssistantRequest):
    return assistant_respond_payload(request)


@app.get("/master")
def master_panel() -> FileResponse:
    panel_path = BASE_DIR / "master_panel.html"
    return FileResponse(panel_path)
