from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from supabase import create_client


class OrderLookupRequest(BaseModel):
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    query: str | None = None
    limit: int = 5


def _supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase is not configured.")
    return create_client(url, key)


def _sanitize_error(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _order_next_step(order: dict[str, Any]) -> str:
    status = (order.get("status") or "").lower()
    if order.get("completed_at") or status in {"completed", "done", "finished"}:
        return "Izveštaj je završen."
    if order.get("analysis_started_at") or status in {"in_progress", "analysis_started", "processing"}:
        return "Analiza je u izradi."
    if not order.get("payment_confirmed_at") and status not in {"paid", "payment_confirmed", "in_progress", "completed"}:
        return "Čeka se potvrda uplate ili ručna provera."
    if order.get("payment_confirmed_at") or status in {"paid", "payment_confirmed"}:
        return "Uplata je potvrđena; analiza čeka početak ili je u redu za izradu."
    return "Potrebna je ručna provera statusa."


def _format_order(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": order.get("id"),
        "created_at": order.get("created_at"),
        "client": " ".join(part for part in [order.get("first_name"), order.get("last_name")] if part).strip() or None,
        "email": order.get("email"),
        "phone": order.get("phone"),
        "service_name": order.get("service_name"),
        "price_rsd": order.get("price_rsd"),
        "birth_date": order.get("birth_date"),
        "birth_time": order.get("birth_time"),
        "birth_place": order.get("birth_place"),
        "status": order.get("status"),
        "payment_confirmed_at": order.get("payment_confirmed_at"),
        "analysis_started_at": order.get("analysis_started_at"),
        "completed_at": order.get("completed_at"),
        "deadline_at": order.get("deadline_at"),
        "admin_notes": order.get("admin_notes"),
        "next_step": _order_next_step(order),
    }


def lookup_orders(request: OrderLookupRequest) -> dict[str, Any]:
    email = _clean(request.email)
    phone = _clean(request.phone)
    first_name = _clean(request.first_name)
    last_name = _clean(request.last_name)
    query = _clean(request.query)
    limit = max(1, min(request.limit, 20))

    if not any([email, phone, first_name, last_name, query]):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one lookup field: email, phone, first_name, last_name or query.",
        )

    client = _supabase()
    try:
        q = client.table("orders").select("*")
        if email:
            q = q.eq("email", email)
        if phone:
            q = q.eq("phone", phone)
        if first_name:
            q = q.ilike("first_name", f"%{first_name}%")
        if last_name:
            q = q.ilike("last_name", f"%{last_name}%")
        if query and not any([email, phone, first_name, last_name]):
            q = q.or_(
                f"first_name.ilike.%{query}%,last_name.ilike.%{query}%,email.ilike.%{query}%,phone.ilike.%{query}%,service_name.ilike.%{query}%"
            )
        result = q.order("created_at", desc=True).limit(limit).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to lookup orders.", "supabase_error": _sanitize_error(exc)},
        ) from exc

    orders = [_format_order(order) for order in (result.data or [])]
    return {
        "success": True,
        "count": len(orders),
        "orders": orders,
        "message": "No matching orders found." if not orders else "Matching orders found.",
    }
