from pathlib import Path

from fastapi.responses import FileResponse

try:
    from backend.app import app
    from backend.assistant_turn import AssistantTurnRequest, assistant_turn_payload
    from backend.astro_confirmation import build_confirmation_matrix
    from backend.astro_dignity import enhance_with_dignities
    from backend.astro_engine import NatalCalculationRequest, calculate_natal
    from backend.astro_predictive import PredictiveCalculationRequest, calculate_predictive
    from backend.astro_rules import enhance_with_rules
    from backend.astro_timeline import enhance_with_timeline
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
    from backend.order_actions import OrderDeleteRequest, OrderStatusUpdateRequest, delete_order, update_order_status
    from backend.order_status import OrderLookupRequest, lookup_orders
except ModuleNotFoundError:
    from app import app
    from assistant_turn import AssistantTurnRequest, assistant_turn_payload
    from astro_confirmation import build_confirmation_matrix
    from astro_dignity import enhance_with_dignities
    from astro_engine import NatalCalculationRequest, calculate_natal
    from astro_predictive import PredictiveCalculationRequest, calculate_predictive
    from astro_rules import enhance_with_rules
    from astro_timeline import enhance_with_timeline
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
    from order_actions import OrderDeleteRequest, OrderStatusUpdateRequest, delete_order, update_order_status
    from order_status import OrderLookupRequest, lookup_orders

BASE_DIR = Path(__file__).resolve().parent.parent


def _safe_astro_natal(request: NatalCalculationRequest):
    result = calculate_natal(request)
    try:
        result = enhance_with_dignities(result)
    except Exception as exc:
        warning = f"Dignity/dispositor layer failed and was skipped: {exc.__class__.__name__}: {str(exc)}"
        result.setdefault("quality_warnings", []).append(warning)
        if isinstance(result.get("book_of_data"), dict):
            result["book_of_data"]["quality_warnings"] = result["quality_warnings"]
            result["book_of_data"]["dignities"] = None
            result["book_of_data"]["planetary_condition"] = None
            result["book_of_data"]["dispositor_chains"] = None
        result["dignities"] = None
        result["planetary_condition"] = None
        result["dispositor_chains"] = None
        result["dignity_layer_error"] = warning
    try:
        result = enhance_with_rules(result)
    except Exception as exc:
        warning = f"Astro rules/orb classification layer failed and was skipped: {exc.__class__.__name__}: {str(exc)}"
        result.setdefault("quality_warnings", []).append(warning)
        if isinstance(result.get("book_of_data"), dict):
            result["book_of_data"]["quality_warnings"] = result["quality_warnings"]
            result["book_of_data"]["proof_book"] = None
        result["proof_book"] = None
        result["rules_layer_error"] = warning
    return result


def _safe_astro_predictive(request: PredictiveCalculationRequest):
    result = calculate_predictive(request)
    natal_request = NatalCalculationRequest(
        birth_date=request.birth_date,
        birth_time=request.birth_time,
        birth_place=request.birth_place,
        calculation_date=request.calculation_date or request.prediction_start,
        house_system=request.house_system,
        zodiac=request.zodiac,
    )
    try:
        natal = _safe_astro_natal(natal_request)
        result["natal_book_of_data"] = natal.get("book_of_data")
        result["natal_proof_book"] = natal.get("proof_book")
        result["natal_aspect_sets"] = natal.get("aspect_sets")
        result.setdefault("quality_warnings", []).append("Natal Book of Data inside predictive package was reprocessed through astro_rules and includes natal_proof_book.")
    except Exception as exc:
        warning = f"Predictive natal reprocessing failed and original natal_book_of_data was kept: {exc.__class__.__name__}: {str(exc)}"
        result.setdefault("quality_warnings", []).append(warning)
        result["natal_reprocess_error"] = warning
    try:
        # First pass cleans invalid lunar returns before confirmation_matrix uses them.
        result = enhance_with_timeline(result)
    except Exception as exc:
        warning = f"Initial lunar cleanup failed before confirmation matrix: {exc.__class__.__name__}: {str(exc)}"
        result.setdefault("quality_warnings", []).append(warning)
    try:
        result["confirmation_matrix"] = build_confirmation_matrix(result)
        result.setdefault("quality_warnings", []).append("confirmation_matrix added: concrete event claims require moderate or strong confirmation status.")
    except Exception as exc:
        warning = f"Confirmation matrix failed and was skipped: {exc.__class__.__name__}: {str(exc)}"
        result.setdefault("quality_warnings", []).append(warning)
        result["confirmation_matrix"] = None
        result["confirmation_matrix_error"] = warning
    try:
        # Second pass rebuilds month_by_month with theme hits from the completed confirmation_matrix.
        result = enhance_with_timeline(result)
    except Exception as exc:
        warning = f"Month-by-month timeline failed and was skipped: {exc.__class__.__name__}: {str(exc)}"
        result.setdefault("quality_warnings", []).append(warning)
        result["month_by_month"] = None
        result["month_by_month_error"] = warning
    return result


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


@app.post("/assistant/turn")
def assistant_turn(request: AssistantTurnRequest):
    return assistant_turn_payload(request)


@app.post("/astro/natal")
def astro_natal(request: NatalCalculationRequest):
    return _safe_astro_natal(request)


@app.post("/astro/predictive")
def astro_predictive(request: PredictiveCalculationRequest):
    return _safe_astro_predictive(request)


@app.post("/intent/extract")
def intent_extract(request: ExtractRequest):
    extraction = extract_payload(request)
    extraction["state"] = merge_state(request.current_state, extraction)
    return extraction


@app.post("/orders/lookup")
def orders_lookup(request: OrderLookupRequest):
    return lookup_orders(request)


@app.post("/orders/status")
def orders_status_update(request: OrderStatusUpdateRequest):
    return update_order_status(request)


@app.post("/orders/delete")
def orders_delete(request: OrderDeleteRequest):
    return delete_order(request)


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
