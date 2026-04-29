import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
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
    "natal_predikcije": {"label": "Natalna karta + predikcije", "price_rsd": 3300},
    "natal": {"label": "Natalna karta", "price_rsd": 2000},
    "sinastrija": {"label": "Sinastrija", "price_rsd": 2400},
    "predikcije": {"label": "Predikcije", "price_rsd": 1500},
    "tri_pitanja": {"label": "3 pitanja", "price_rsd": 900},
    "pet_pitanja": {"label": "5 pitanja", "price_rsd": 1400},
    "deset_pitanja": {"label": "10 pitanja", "price_rsd": 2700},
}

PAYMENT_REPLY = "Uplata ide tek kada potvrdimo porudžbinu i podatke. Tada šaljem instrukcije za uplatu."
DELIVERY_REPLY = "Rok izrade je do 5 radnih dana od potvrde uplate i kompletnih podataka."


class OrderRequest(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    instagram_username: Optional[str] = None
    order_source: Optional[str] = None
    source: Optional[str] = None
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
        contact_fields = [self.email, (self.phone or "").strip(), (self.instagram_username or "").strip()]
        if not any(contact_fields):
            raise ValueError("At least one contact field is required: email, phone, or instagram_username")
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
        raise HTTPException(status_code=500, detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    return create_client(supabase_url, service_role_key)


def _sanitize_error_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _missing_column_from_error(exc: Exception) -> Optional[str]:
    match = re.search(r"Could not find the '([^']+)' column", _sanitize_error_message(exc))
    return match.group(1) if match else None


def _env_is_set(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _get_openai_client() -> OpenAI:
    if not _env_is_set("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI is not configured. Set OPENAI_API_KEY.")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _normalize_text(value: str) -> str:
    text = value.lower()
    for src, dst in {"č": "c", "ć": "c", "š": "s", "đ": "dj", "ž": "z"}.items():
        text = text.replace(src, dst)
    return text


def _has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _client_prefix(name: Optional[str]) -> str:
    clean = (name or "").strip()
    return f"{clean}, " if clean else ""


def _short_price_line(service: Optional[dict[str, Any]]) -> str:
    if service:
        return f"{service['label']} je {int(service['price_rsd'])} RSD."
    return "Natalna je 2.000 RSD, Natal + predikcije 3.300 RSD, sinastrija 2.400 RSD, predikcije 1.500 RSD."


def _config_status_payload() -> dict[str, Any]:
    checks = {
        "SUPABASE_URL": _env_is_set("SUPABASE_URL"),
        "SUPABASE_SERVICE_ROLE_KEY": _env_is_set("SUPABASE_SERVICE_ROLE_KEY"),
        "OPENAI_API_KEY": _env_is_set("OPENAI_API_KEY"),
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
            "ai": checks["OPENAI_API_KEY"],
            "meta": checks["META_PAGE_TOKEN"] and checks["META_APP_SECRET"],
            "email": checks["GMAIL_ADDRESS"] and checks["GMAIL_APP_PASSWORD"],
        },
    }


def _source_label(order: OrderRequest) -> Optional[str]:
    return (order.order_source or order.source or "").strip() or None


def _build_order_payload(order: OrderRequest) -> dict[str, Any]:
    source_label = _source_label(order)
    message = order.message
    if source_label:
        source_line = f"Izvor porudžbine: {source_label}"
        message = f"{source_line}\n{message}" if message else source_line
    payload = {
        "first_name": order.first_name,
        "last_name": order.last_name,
        "email": str(order.email) if order.email else None,
        "phone": order.phone,
        "instagram_username": order.instagram_username,
        "order_source": source_label,
        "source": source_label,
        "service_name": order.service_name,
        "price_rsd": order.price_rsd,
        "birth_date": order.birth_date,
        "birth_time": order.birth_time,
        "birth_place": order.birth_place,
        "partner_birth_data": order.partner_birth_data,
        "questions": order.questions,
        "message": message,
        "status": order.status or "received",
    }
    return {key: value for key, value in payload.items() if value is not None}


def _insert_order_payload(supabase: Client, payload: dict[str, Any]) -> dict[str, Any]:
    working_payload = dict(payload)
    removed_columns: list[str] = []
    for _ in range(12):
        try:
            response = supabase.table("orders").insert(working_payload).execute()
            inserted_record = response.data[0] if response.data else working_payload
            return {"success": True, "message": "Order saved successfully.", "order": inserted_record, "removed_columns": removed_columns}
        except Exception as exc:
            missing_column = _missing_column_from_error(exc)
            if missing_column and missing_column in working_payload:
                removed_columns.append(missing_column)
                working_payload.pop(missing_column, None)
                continue
            raise HTTPException(status_code=500, detail={"message": "Failed to save order to Supabase.", "supabase_error": _sanitize_error_message(exc), "removed_columns": removed_columns}) from exc
    raise HTTPException(status_code=500, detail={"message": "Failed to save order to Supabase after schema fallback retries.", "removed_columns": removed_columns})


def _create_order(order: OrderRequest) -> dict[str, Any]:
    if not order.first_name.strip():
        raise HTTPException(status_code=400, detail="first_name is required")
    if not order.service_name.strip():
        raise HTTPException(status_code=400, detail="service_name is required")
    return _insert_order_payload(get_supabase_client(), _build_order_payload(order))


def _service_from_message(text: str) -> Optional[dict[str, Any]]:
    if _has_any(text, ["sinastr", "upored", "partner", "veza", "ljubav"]):
        return SERVICE_PRICES["sinastrija"]
    if _has_any(text, ["natal", "karta", "licni horoskop"]):
        return SERVICE_PRICES["natal"]
    if _has_any(text, ["predikc", "godis", "buduc", "tranzit", "period"]):
        return SERVICE_PRICES["natal_predikcije"]
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
    prefix = _client_prefix(request.client_name)
    intent = "general"
    priority = "normal"
    action = "reply_only"
    if _has_any(text, ["cena", "koliko", "kosta", "cenovnik", "paket"]):
        intent = "pricing"
        reply = f"{prefix}{_short_price_line(service)} Za izradu mi trebaju datum, tačno vreme i mesto rođenja. Ako želite samo osnovu ličnosti, dovoljna je natalna. Ako želite i šta vas čeka u narednom periodu, bolja je opcija Natal + predikcije."
    elif _has_any(text, ["poruc", "naruc", "hoc", "zelim", "kup", "radila bih", "radio bih", "uzela bih", "uzeo bih"]):
        intent = "order_intent"
        priority = "high"
        action = "collect_birth_data"
        chosen = service or SERVICE_PRICES["natal_predikcije"]
        reply = f"{prefix}može. Za {chosen['label']} cena je {int(chosen['price_rsd'])} RSD. Pošaljite mi datum rođenja, tačno vreme i mesto rođenja. Kada imam te podatke, potvrđujem porudžbinu i šaljem instrukcije za uplatu."
    elif _has_any(text, ["plat", "uplata", "racun", "paypal", "western", "payoneer", "kartic"]):
        intent = "payment"
        priority = "high"
        action = "send_payment_instructions_after_confirmation"
        reply = f"{prefix}{PAYMENT_REPLY} Prvo mi napišite koju analizu želite, pa odmah završavamo porudžbinu."
    elif _has_any(text, ["kada", "stize", "gotov", "rok", "isporuk", "cekam"]):
        intent = "delivery_status"
        priority = "high"
        action = "check_order_status"
        reply = f"{prefix}{DELIVERY_REPLY} Ako je porudžbina već poslata, pošaljite ime ili profil pod kojim ste poručili, pa proveravam status."
    elif _has_any(text, ["podaci", "sta treba", "sta saljem", "vreme rodjenja", "mesto rodjenja"]):
        intent = "required_data"
        action = "collect_birth_data"
        reply = f"{prefix}trebaju mi datum rođenja, tačno vreme rođenja i mesto rođenja. Za sinastriju šaljete iste podatke za obe osobe. Ako vreme nije potpuno sigurno, napišite mi približno i naglasite da nije sigurno."
    else:
        reply = f"{prefix}mogu da vam pogledam natal, predikcije, sinastriju ili konkretna pitanja. Napišite mi šta vas najviše zanima i pošaljite datum, vreme i mesto rođenja, pa vam kažem koja opcija je najbolja."
    return {"success": True, "agent": "client_intake.respond", "intent": intent, "priority": priority, "recommended_action": action, "detected_service": service, "reply": reply, "safe_to_send": True, "channel": request.channel, "original_message": original}


def _client_intake_ai_response(request: ClientIntakeRequest) -> dict[str, Any]:
    client = _get_openai_client()
    system_prompt = """
Ti si specijalizovani AI DM prodajni asistent za ASTRO ARIES STUDIO. Pišeš kao Daniel, profesionalni astrolog i vlasnik studija.

CILJ: razumi poruku klijenta, prepoznaj nameru, napiši kratak, ljudski, topao, precizan i prodajno jasan odgovor za Instagram DM ili komentar.

STIL:
- srpski, ekavica, prirodno, bez AI tona
- bez fraza: "hvala na upitu", "naravno, cene su", "kao AI", "drago mi je što ste se javili"
- ne zvuči kao cenovnik, ne nabrajaj sve cene osim ako korisnik traži cenovnik
- odgovori kao čovek: 1-4 kratke rečenice
- uvek vodi na sledeći korak
- ne obećavaj ono što ne znaš
- ne izmišljaj bankovne podatke, linkove, popuste ili rokove

ZVANIČNE USLUGE I CENE:
- Natalna karta: 2.000 RSD
- Natalna karta + predikcije: 3.300 RSD
- Predikcije: 1.500 RSD
- Sinastrija: 2.400 RSD
- 3 pitanja: 900 RSD
- 5 pitanja: 1.400 RSD
- 10 pitanja: 2.700 RSD

PODACI ZA IZRADU:
- datum rođenja
- tačno vreme rođenja
- mesto rođenja
- za sinastriju isti podaci za obe osobe

ROK: do 5 radnih dana od potvrde uplate i kompletnih podataka.
PLAĆANJE: instrukcije za uplatu se šalju tek nakon potvrde porudžbine i podataka.

Vrati isključivo JSON objekat sa ključevima:
intent, priority, recommended_action, detected_service, reply, safe_to_send, needs_human_review.
Intent može biti: pricing, order_intent, payment, delivery_status, required_data, astrology_question, complaint, unclear, general.
Priority može biti: low, normal, high.
Recommended_action može biti: reply_only, collect_birth_data, create_order_draft, check_order_status, human_review.
""".strip()
    user_payload = {"message": request.message, "client_name": request.client_name, "instagram_username": request.instagram_username, "channel": request.channel}
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}],
            temperature=0.55,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "AI client intake failed.", "error": _sanitize_error_message(exc)}) from exc
    return {"success": True, "agent": "client_intake.ai_respond", "intent": data.get("intent", "unclear"), "priority": data.get("priority", "normal"), "recommended_action": data.get("recommended_action", "reply_only"), "detected_service": data.get("detected_service"), "reply": data.get("reply", ""), "safe_to_send": bool(data.get("safe_to_send", False)), "needs_human_review": bool(data.get("needs_human_review", True)), "channel": request.channel, "original_message": request.message}


def _run_agent_task(task_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task_name == "orders.create":
        return _create_order(OrderRequest(**payload))
    if task_name == "client_intake.respond":
        return _client_intake_response(ClientIntakeRequest(**payload))
    if task_name == "client_intake.ai_respond":
        return _client_intake_ai_response(ClientIntakeRequest(**payload))
    return orchestrator.run(task_name, payload)


def _default_test_order() -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return {"first_name": "AUTO_TEST", "last_name": "Orchestrator", "email": f"auto-test-{stamp}@example.com", "phone": "+38160000000", "instagram_username": "auto_test_astro", "order_source": "system_test", "service_name": "Automation test order", "price_rsd": 0, "birth_date": "08.05.1967", "birth_time": "10:10", "birth_place": "Split, Hrvatska", "message": f"Setup runner test order {stamp}", "status": "test"}


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
        steps.append(_step("orders.payload_validation", "passed", _build_order_payload(validated)))
    except Exception as exc:
        steps.append(_step("orders.payload_validation", "failed", _sanitize_error_message(exc)))
        return {"success": False, "mode": "dry_run" if request.dry_run else "live", "steps": steps}
    if request.create_test_order and not request.dry_run:
        try:
            steps.append(_step("orders.create_test_order", "passed", _create_order(validated)))
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


@app.post("/client-intake/ai-respond")
def client_intake_ai_respond(request: ClientIntakeRequest) -> dict[str, Any]:
    return _client_intake_ai_response(request)


@app.post("/setup/run")
def run_setup(request: SetupRunRequest) -> dict[str, Any]:
    return _run_setup_sequence(request)


@app.post("/order")
def create_order(order: OrderRequest) -> dict[str, Any]:
    return _create_order(order)


@app.post("/orders")
def create_orders(order: OrderRequest) -> dict[str, Any]:
    return _create_order(order)
