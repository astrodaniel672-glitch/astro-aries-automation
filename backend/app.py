import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, model_validator
from supabase import Client, create_client

try:
    from backend.orchestrator import create_default_orchestrator
except ModuleNotFoundError:
    from orchestrator import create_default_orchestrator

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

app = FastAPI(title="ASTRO ARIES STUDIO Automation")
orchestrator = create_default_orchestrator()


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


def _create_order(order: OrderRequest) -> dict[str, Any]:
    if not order.first_name.strip():
        raise HTTPException(status_code=400, detail="first_name is required")

    if not order.service_name.strip():
        raise HTTPException(status_code=400, detail="service_name is required")

    payload = _build_order_payload(order)
    supabase = get_supabase_client()

    try:
        response = supabase.table("orders").insert(payload).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to save order to Supabase.",
                "supabase_error": _sanitize_error_message(exc),
            },
        ) from exc

    inserted_record = response.data[0] if response.data else payload

    return {
        "success": True,
        "message": "Order saved successfully.",
        "order": inserted_record,
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/agents")
def list_agents() -> list[dict[str, Any]]:
    return orchestrator.list_tasks()


@app.post("/agents/run")
def run_agent(request: AgentRunRequest) -> dict[str, Any]:
    return orchestrator.run(request.task_name, request.payload)


@app.post("/order")
def create_order(order: OrderRequest) -> dict[str, Any]:
    return _create_order(order)


@app.post("/orders")
def create_orders(order: OrderRequest) -> dict[str, Any]:
    return _create_order(order)
