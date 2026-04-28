import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, model_validator
from supabase import Client, create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

app = FastAPI(title="ASTRO ARIES STUDIO Automation")


class OrderRequest(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    service_name: str
    price_rsd: Optional[float] = None
    birth_date: str
    birth_time: str
    birth_place: str
    marital_status: Optional[str] = None
    questions: Optional[Any] = None
    message: Optional[str] = None
    source: Optional[str] = None
    entry_method: Optional[str] = None
    external_conversation_id: Optional[str] = None
    external_user_id: Optional[str] = None
    username: Optional[str] = None
    contact_preference: Optional[str] = None
    internal_notes: Optional[str] = None
    order_status: str = "received"

    @model_validator(mode="after")
    def validate_fields(self) -> "OrderRequest":
        allowed_sources = {"instagram_dm", "whatsapp", "website", "email", "manual"}
        allowed_entry_methods = {"automatic", "manual"}

        if self.source is not None and self.source not in allowed_sources:
            raise ValueError("source must be one of: instagram_dm, whatsapp, website, email, manual")

        if self.entry_method is not None and self.entry_method not in allowed_entry_methods:
            raise ValueError("entry_method must be one of: automatic, manual")

        contact_fields = [
            self.email,
            (self.phone or "").strip(),
            (self.username or "").strip(),
            (self.external_user_id or "").strip(),
        ]

        if not any(contact_fields):
            raise ValueError("At least one contact field is required: email, phone, username, or external_user_id")

        return self


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )

    return create_client(supabase_url, service_role_key)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/order")
def create_order(order: OrderRequest) -> dict[str, Any]:
    if not order.first_name.strip():
        raise HTTPException(status_code=400, detail="first_name is required")

    if not order.service_name.strip():
        raise HTTPException(status_code=400, detail="service_name is required")

    supabase = get_supabase_client()
    payload = order.model_dump(exclude_none=True)

    try:
        response = supabase.table("orders").insert(payload).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save order to Supabase.")

    inserted_record = response.data[0] if response.data else payload

    return {
        "success": True,
        "message": "Order saved successfully.",
        "order": inserted_record,
    }
