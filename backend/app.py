import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, model_validator
from supabase import Client, create_client

try:
    from backend.orchestrator import create_default_orchestrator
except ModuleNotFoundError:
    from orchestrator import create_default_orchestrator

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="ASTRO ARIES STUDIO Automation")
orchestrator = create_default_orchestrator()

SERVICE_PRICES = {
    "natal_predikcije": {"label": "Natalna Karta + Predikcije", "price_rsd": 3300},
    "natal": {"label": "Natalna Karta", "price_rsd": 2000},
    "sinastrija": {"label": "Sinastrija", "price_rsd": 2400},
    "predikcije": {"label": "Predikcije", "price_rsd": 1500},
    "tri_pitanja": {"label": "3 Pitanja", "price_rsd": 900},
    "pet_pitanja": {"label": "5 Pitanja", "price_rsd": 1400},
    "deset_pitanja": {"label": "10 Pitanja", "price_rsd": 2700},
}

PAYMENT_REPLY = (
    "Plaćanje se dogovara nakon potvrde porudžbine. Kada izaberete uslugu i pošaljete podatke, "
    "šaljem vam tačne instrukcije za uplatu i potvrdu termina izrade."
)

DELIVERY_REPLY = "Rok izrade je do 5 radnih dana od potvrde uplate i kompletnih podataka."


class OrderRequest(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    instagram_username: Optional[str] = None
    service_name: str
    price_rsd: Optional[float] = None
    birth_date: str
    birth_time: str
    birth_place: str
    partner_birth_data: Optional[str] = None
    questions: Optional[Any] = None
    message: Optional[str] = None
    status: str = "received"

    @model_validator(mode="after")
    def validate_fields(self) -> "OrderRequest":
        contact_fields = [
            self.email,
            (self.phone or "").strip(),
            (self.instagram_username or "").strip(),
        ]

        if not any(contact_fields):
            raise ValueError(
                "At least one contact field is required: email, phone, or instagram_username"
            )

        return self


class AgentRunRequest(BaseModel):
    task_name: str
    payload: dict[str, Any] = {}


class SetupRunRequest(BaseModel):
    create_test_order: bool = False
    dry_run: bool = True
    test_order: Optional[dict[str, Any]] = None


class ClientIntakeRequest(BaseModel):
    message: str
    client_name: Optional[str] = None
    instagram_username: Optional[str] = None
    channel: str = "instagram_dm"


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )

    return create_client(supabase_url, service_role_key)


def _sanitize_error_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _missing_column_from_error(exc: Exception) -> Optional[str]:
    message = _sanitize_error_message(exc)
    match = re.search(r"Could not find the '([^']+)' column", message)
    if match:
        return match.group(1)
    return None


def _env_is_set(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _normalize_text(value: str) -> str:
    text = value.lower()
    replacements = {"č": "c", "ć": "c", "š": "s", "đ": "dj", "ž": "z"}
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _config_status_payload() -> dict[str, Any]:
    checks = {
        "SUPABASE_URL": _env_is_set("SUPABASE_URL"),
        "SUPABASE_SERVICE_ROLE_KEY": _env_is_set("SUPABASE_SERVICE_ROLE_KEY"),
        "META_PAGE_TOKEN": _env_is_set("META_PAGE_TOKEN"),
        "META_APP_SECRET": _env_is_set("META_APP_SECRET"),
        "GMAIL_ADDRESS": _env_is_set("GMAIL_ADDRESS"),
        "GMAIL_APP_PASSWORD": _env_is_set("GMAIL_APP_PASSWORD"),
    }

    return {
        "success": True,
        "configured": checks,
        "ready": {
            "orders": checks["SUPABASE_URL"] and checks["SUPABASE_SERVICE_ROLE_KEY"],
            "meta": checks["META_PAGE_TOKEN"] and checks["META_APP_SECRET"],
            "email": checks["GMAIL_ADDRESS"] and checks["GMAIL_APP_PASSWORD"],
        },
    }


def _build_order_payload(order: OrderRequest) -> dict[str, Any]:
    payload = {
        "first_name": order.first_name,
        "last_name": order.last_name,
        "email": str(order.email) if order.email else None,
        "phone": order.phone,
        "instagram_username": order.instagram_username,
        "service_name": order.service_name,
        "price_rsd": order.price_rsd,
        "birth_date": order.birth_date,
        "birth_time": order.birth_time,
        "birth_place": order.birth_place,
        "partner_birth_data": order.partner_birth_data,
        "questions": order.questions,
        "message": order.message,
        "status": order.status or "received",
    }

    return {key: value for key, value in payload.items() if value is not None}


def _insert_order_payload(supabase: Client, payload: dict[str, Any]) -> dict[str, Any]:
    working_payload = dict(payload)
    removed_columns: list[str] = []

    for _ in range(8):
        try:
            response = supabase.table("orders").insert(working_payload).execute()
            inserted_record = response.data[0] if response.data else working_payload
            return {
                "success": True,
                "message": "Order saved successfully.",
                "order": inserted_record,
                "removed_columns": removed_columns,
            }
        except Exception as exc:
            missing_column = _missing_column_from_error(exc)
            if missing_column and missing_column in working_payload:
                removed_columns.append(missing_column)
                working_payload.pop(missing_column, None)
                continue

            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Failed to save order to Supabase.",
                    "supabase_error": _sanitize_error_message(exc),
                    "removed_columns": removed_columns,
                },
            ) from exc

    raise HTTPException(
        status_code=500,
        detail={
            "message": "Failed to save order to Supabase after schema fallback retries.",
            "removed_columns": removed_columns,
        },
    )


def _create_order(order: OrderRequest) -> dict[str, Any]:
    if not order.first_name.strip():
        raise HTTPException(status_code=400, detail="first_name is required")

    if not order.service_name.strip():
        raise HTTPException(status_code=400, detail="service_name is required")

    payload = _build_order_payload(order)
    supabase = get_supabase_client()
    return _insert_order_payload(supabase, payload)


def _price_text() -> str:
    return (
        "Cene su: Natalna karta 2.000 RSD, Natalna karta + predikcije 3.300 RSD, "
        "Predikcije 1.500 RSD, Sinastrija 2.400 RSD, 3 pitanja 900 RSD, "
        "5 pitanja 1.400 RSD i 10 pitanja 2.700 RSD."
    )


def _service_from_message(text: str) -> Optional[dict[str, Any]]:
    if _has_any(text, ["sinastr", "upored", "partner", "veza"]):
        return SERVICE_PRICES["sinastrija"]
    if _has_any(text, ["predikc", "godis", "buduc", "tranzit"]):
        return SERVICE_PRICES["natal_predikcije"]
    if _has_any(text, ["natal", "karta", "horoskop"]):
        return SERVICE_PRICES["natal"]
    if _has_any(text, ["3 pitanja", "tri pitanja"]):
        return SERVICE_PRICES["tri_pitanja"]
    if _has_any(text, ["5 pitanja", "pet pitanja"]):
        return SERVICE_PRICES["pet_pitanja"]
    if _has_any(text, ["10 pitanja", "deset pitanja"]):
        return SERVICE_PRICES["deset_pitanja"]
    return None


def _client_intake_response(request: ClientIntakeRequest) -> dict[str, Any]:
    original = request.message.strip()
    text = _normalize_text(original)
    service = _service_from_message(text)
    client = (request.client_name or "").strip()
    greeting = f"{client}, " if client else ""

    intent = "general"
    priority = "normal"
    action = "reply_only"

    if _has_any(text, ["cena", "koliko", "kosta", "cenovnik", "paket"]):
        intent = "pricing"
        reply = (
            f"{greeting}naravno. {_price_text()} "
            "Za porudžbinu su mi potrebni datum, tačno vreme i mesto rođenja. "
            "Ako želite najkompletniju opciju, preporuka je Natalna karta + predikcije jer daje i osnovu karaktera i konkretan period pred vama."
        )
    elif _has_any(text, ["poruc", "naruc", "hoc", "zelim", "kup", "radila bih", "radio bih"]):
        intent = "order_intent"
        priority = "high"
        action = "collect_birth_data"
        chosen = service["label"] if service else "analizu"
        price = f" Cena za ovu uslugu je {int(service['price_rsd'])} RSD." if service else ""
        reply = (
            f"{greeting}može, upisaću porudžbinu za {chosen}.{price} "
            "Pošaljite mi datum rođenja, tačno vreme rođenja i mesto rođenja. "
            "Ako je sinastrija, pošaljite iste podatke i za drugu osobu. Nakon toga potvrđujem porudžbinu i šaljem instrukcije za uplatu."
        )
    elif _has_any(text, ["plat", "uplata", "racun", "paypal", "western", "payoneer"]):
        intent = "payment"
        priority = "high"
        action = "send_payment_instructions_after_confirmation"
        reply = f"{greeting}{PAYMENT_REPLY}"
    elif _has_any(text, ["kada", "stize", "gotov", "rok", "isporuk", "cekam"]):
        intent = "delivery_status"
        priority = "high"
        action = "check_order_status"
        reply = (
            f"{greeting}{DELIVERY_REPLY} Ako ste već poručili, pošaljite mi ime pod kojim je porudžbina ili email/Instagram profil, pa proveravam status."
        )
    elif _has_any(text, ["podaci", "sta treba", "sta saljem", "vreme rodjenja", "mesto rodjenja"]):
        intent = "required_data"
        action = "collect_birth_data"
        reply = (
            f"{greeting}za izradu su potrebni: datum rođenja, tačno vreme rođenja i mesto rođenja. "
            "Za sinastriju trebaju isti podaci za obe osobe. Ako vreme nije potpuno sigurno, napišite približno i obavezno naglasite da nije sigurno."
        )
    else:
        reply = (
            f"{greeting}hvala vam na poruci. Mogu da vam pomognem oko natalne karte, predikcija, sinastrije ili konkretnih pitanja. "
            "Najbrže je da napišete šta želite da poručite i pošaljete datum, vreme i mesto rođenja."
        )

    return {
        "success": True,
        "agent": "client_intake.respond",
        "intent": intent,
        "priority": priority,
        "recommended_action": action,
        "detected_service": service,
        "reply": reply,
        "safe_to_send": True,
        "channel": request.channel,
        "original_message": original,
    }


def _run_agent_task(task_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task_name == "orders.create":
        return _create_order(OrderRequest(**payload))
    if task_name == "client_intake.respond":
        return _client_intake_response(ClientIntakeRequest(**payload))

    return orchestrator.run(task_name, payload)


def _default_test_order() -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return {
        "first_name": "AUTO_TEST",
        "last_name": "Orchestrator",
        "email": f"auto-test-{stamp}@example.com",
        "phone": "+38160000000",
        "instagram_username": "auto_test_astro",
        "service_name": "Automation test order",
        "price_rsd": 0,
        "birth_date": "08.05.1967",
        "birth_time": "10:10",
        "birth_place": "Split, Hrvatska",
        "message": f"Setup runner test order {stamp}",
        "status": "test",
    }


def _step(name: str, status: str, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "status": status, "detail": detail}


def _run_setup_sequence(request: SetupRunRequest) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    steps.append(_step("health", "passed", {"status": "ok"}))

    config = _config_status_payload()
    steps.append(_step("config.status", "passed", config))

    agents = orchestrator.list_tasks()
    steps.append(_step("agents.list", "passed", {"count": len(agents), "agents": agents}))

    if not config["ready"]["orders"]:
        steps.append(_step("orders.ready", "blocked", "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the runtime environment."))
        return {"success": False, "mode": "dry_run" if request.dry_run else "live", "steps": steps}

    steps.append(_step("orders.ready", "passed", "Supabase order environment is configured."))

    test_payload = request.test_order or _default_test_order()
    try:
        validated = OrderRequest(**test_payload)
        safe_payload = _build_order_payload(validated)
        steps.append(_step("orders.payload_validation", "passed", safe_payload))
    except Exception as exc:
        steps.append(_step("orders.payload_validation", "failed", _sanitize_error_message(exc)))
        return {"success": False, "mode": "dry_run" if request.dry_run else "live", "steps": steps}

    if request.create_test_order and not request.dry_run:
        try:
            created = _create_order(validated)
            steps.append(_step("orders.create_test_order", "passed", created))
        except HTTPException as exc:
            steps.append(_step("orders.create_test_order", "failed", exc.detail))
            return {"success": False, "mode": "live", "steps": steps}
    else:
        steps.append(_step("orders.create_test_order", "skipped", "Dry run only. Send create_test_order=true and dry_run=false for live Supabase insert."))

    return {"success": True, "mode": "dry_run" if request.dry_run else "live", "steps": steps}


@app.get("/admin")
def admin_panel() -> FileResponse:
    panel_path = BASE_DIR / "admin_panel.html"
    if not panel_path.exists():
        raise HTTPException(status_code=404, detail="Admin panel file not found.")
    return FileResponse(panel_path)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config/status")
def config_status() -> dict[str, Any]:
    return _config_status_payload()


@app.get("/agents")
def list_agents() -> list[dict[str, Any]]:
    return orchestrator.list_tasks()


@app.post("/agents/run")
def run_agent(request: AgentRunRequest) -> dict[str, Any]:
    return _run_agent_task(request.task_name, request.payload)


@app.post("/client-intake/respond")
def client_intake_respond(request: ClientIntakeRequest) -> dict[str, Any]:
    return _client_intake_response(request)


@app.post("/setup/run")
def run_setup(request: SetupRunRequest) -> dict[str, Any]:
    return _run_setup_sequence(request)


@app.post("/order")
def create_order(order: OrderRequest) -> dict[str, Any]:
    return _create_order(order)


@app.post("/orders")
def create_orders(order: OrderRequest) -> dict[str, Any]:
    return _create_order(order)
