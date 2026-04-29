from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
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
    limit: int = 25
    include_tests: bool = False


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


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _add_business_days(start: datetime, days: int) -> datetime:
    current = start
    added = 0
    while added < days:
        current = current + timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _computed_deadline(order: dict[str, Any]) -> datetime | None:
    explicit = _parse_dt(order.get("deadline_at"))
    if explicit:
        return explicit
    anchor = _parse_dt(order.get("payment_confirmed_at")) or _parse_dt(order.get("created_at"))
    if not anchor:
        return None
    return _add_business_days(anchor, 5)


def _is_done(order: dict[str, Any]) -> bool:
    status = (order.get("status") or "").lower()
    return bool(order.get("completed_at")) or status in {"completed", "done", "finished", "delivered"}


def _is_test_order(order: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(order.get(k) or "")
        for k in ["status", "email", "first_name", "last_name", "service_name", "message", "birth_place"]
    ).lower()
    return any(token in haystack for token in ["test", "auto_test", "automation test", "agent control panel"])


def _about_user(order: dict[str, Any]) -> str | None:
    pieces: list[str] = []
    questions = order.get("questions")
    message = order.get("message")
    admin_notes = order.get("admin_notes")
    ai_response = order.get("ai_response")
    marital_status = order.get("marital_status")
    employment = order.get("employment")

    if marital_status:
        pieces.append(f"Bračni status: {marital_status}")
    if employment:
        pieces.append(f"Posao: {employment}")
    if questions:
        pieces.append(f"Pitanja/tema: {questions}")
    if message:
        pieces.append(f"Poruka: {message}")
    if admin_notes:
        pieces.append(f"Beleška: {admin_notes}")
    if ai_response:
        pieces.append(f"AI napomena: {ai_response}")
    if not pieces:
        return None
    return " | ".join(pieces)


def _order_next_step(order: dict[str, Any]) -> str:
    status = (order.get("status") or "").lower()
    if _is_done(order):
        return "Izveštaj je završen / isporučen."
    if order.get("analysis_started_at") or status in {"in_progress", "analysis_started", "processing"}:
        return "Analiza je u izradi."
    if not order.get("payment_confirmed_at") and status not in {"paid", "payment_confirmed", "in_progress", "completed"}:
        return "Čeka se potvrda uplate ili ručna provera."
    if order.get("payment_confirmed_at") or status in {"paid", "payment_confirmed"}:
        return "Uplata je potvrđena; analiza čeka početak ili je u redu za izradu."
    return "Potrebna je ručna provera statusa."


def _priority(order: dict[str, Any]) -> str:
    if _is_done(order):
        return "closed"
    status = (order.get("status") or "").lower()
    deadline = _computed_deadline(order)
    now = datetime.now(timezone.utc)
    if deadline:
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        days_left = (deadline.date() - now.date()).days
        if days_left < 0:
            return "overdue"
        if days_left <= 1:
            return "urgent"
        if days_left <= 3:
            return "high"
    if not order.get("payment_confirmed_at") and status not in {"paid", "payment_confirmed"}:
        return "waiting_payment"
    return "normal"


def _delay_info(order: dict[str, Any]) -> dict[str, Any]:
    deadline = _computed_deadline(order)
    if not deadline:
        return {"deadline_at_computed": None, "is_late": False, "days_late": 0, "days_left": None}
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days_delta = (deadline.date() - now.date()).days
    if _is_done(order):
        return {"deadline_at_computed": deadline.isoformat(), "is_late": False, "days_late": 0, "days_left": days_delta}
    return {
        "deadline_at_computed": deadline.isoformat(),
        "is_late": days_delta < 0,
        "days_late": abs(days_delta) if days_delta < 0 else 0,
        "days_left": days_delta,
    }


def _format_order(order: dict[str, Any]) -> dict[str, Any]:
    delay = _delay_info(order)
    return {
        "id": order.get("id"),
        "created_at": order.get("created_at"),
        "client": " ".join(part for part in [order.get("first_name"), order.get("last_name")] if part).strip() or None,
        "first_name": order.get("first_name"),
        "last_name": order.get("last_name"),
        "email": order.get("email"),
        "phone": order.get("phone"),
        "service_id": order.get("service_id"),
        "service_name": order.get("service_name"),
        "price_rsd": order.get("price_rsd"),
        "birth_date": order.get("birth_date"),
        "birth_time": order.get("birth_time"),
        "birth_place": order.get("birth_place"),
        "status": order.get("status"),
        "priority": _priority(order),
        "payment_confirmed_at": order.get("payment_confirmed_at"),
        "analysis_started_at": order.get("analysis_started_at"),
        "completed_at": order.get("completed_at"),
        "deadline_at": order.get("deadline_at"),
        **delay,
        "admin_notes": order.get("admin_notes"),
        "message": order.get("message"),
        "questions": order.get("questions"),
        "marital_status": order.get("marital_status"),
        "employment": order.get("employment"),
        "about_user": _about_user(order),
        "is_test": _is_test_order(order),
        "next_step": _order_next_step(order),
    }


def _summary(orders: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"total": len(orders), "overdue": 0, "urgent": 0, "waiting_payment": 0, "in_progress": 0, "completed": 0}
    for order in orders:
        if order.get("priority") == "overdue":
            summary["overdue"] += 1
        if order.get("priority") == "urgent":
            summary["urgent"] += 1
        if order.get("priority") == "waiting_payment":
            summary["waiting_payment"] += 1
        if (order.get("status") or "").lower() in {"in_progress", "analysis_started", "processing"}:
            summary["in_progress"] += 1
        if order.get("completed_at") or (order.get("status") or "").lower() in {"completed", "done", "finished", "delivered"}:
            summary["completed"] += 1
    return summary


def lookup_orders(request: OrderLookupRequest) -> dict[str, Any]:
    email = _clean(request.email)
    phone = _clean(request.phone)
    first_name = _clean(request.first_name)
    last_name = _clean(request.last_name)
    query = _clean(request.query)
    limit = max(1, min(request.limit, 100))

    client = _supabase()
    try:
        q = client.table("orders").select("*")

        if email:
            q = q.ilike("email", email)
        if phone:
            q = q.ilike("phone", f"%{phone}%")
        if first_name:
            q = q.ilike("first_name", f"%{first_name}%")
        if last_name:
            q = q.ilike("last_name", f"%{last_name}%")
        if query and not any([email, phone, first_name, last_name]):
            safe_query = query.replace(",", " ").replace("%", "")
            q = q.or_(
                f"first_name.ilike.%{safe_query}%,last_name.ilike.%{safe_query}%,email.ilike.%{safe_query}%,phone.ilike.%{safe_query}%,service_name.ilike.%{safe_query}%,birth_place.ilike.%{safe_query}%,message.ilike.%{safe_query}%,status.ilike.%{safe_query}%"
            )

        result = q.order("created_at", desc=True).limit(limit).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to lookup orders.", "supabase_error": _sanitize_error(exc)},
        ) from exc

    raw_orders = result.data or []
    all_count = len(raw_orders)
    formatted_all = [_format_order(order) for order in raw_orders]
    hidden_tests = len([o for o in formatted_all if o.get("is_test")])
    orders = formatted_all if request.include_tests else [o for o in formatted_all if not o.get("is_test")]
    orders.sort(key=lambda item: {"overdue": 0, "urgent": 1, "high": 2, "waiting_payment": 3, "normal": 4, "closed": 5}.get(item.get("priority"), 9))
    search_mode = "latest" if not any([email, phone, first_name, last_name, query]) else "filtered"
    return {
        "success": True,
        "search_mode": search_mode,
        "count": len(orders),
        "all_count_before_test_filter": all_count,
        "hidden_test_orders": 0 if request.include_tests else hidden_tests,
        "summary": _summary(orders),
        "orders": orders,
        "message": "No matching orders found." if not orders else "Orders returned.",
    }
