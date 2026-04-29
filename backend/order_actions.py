from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from supabase import create_client


class OrderStatusUpdateRequest(BaseModel):
    order_id: str
    action: str


class OrderDeleteRequest(BaseModel):
    order_id: str
    reason: str | None = None


def _supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase is not configured.")
    return create_client(url, key)


def _sanitize_error(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _add_business_days(start: datetime, days: int) -> datetime:
    current = start
    added = 0
    while added < days:
        current = current + timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _deadline_from_now() -> str:
    return _add_business_days(datetime.now(timezone.utc), 5).isoformat()


def _missing_column_from_error(error: str) -> str | None:
    import re
    match = re.search(r"Could not find the '([^']+)' column", error)
    return match.group(1) if match else None


def _safe_update(client, order_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    working = dict(payload)
    removed_columns: list[str] = []
    for _ in range(8):
        try:
            result = client.table("orders").update(working).eq("id", order_id).execute()
            if not result.data:
                raise HTTPException(status_code=404, detail="Order not found.")
            return {"success": True, "order": result.data[0], "removed_columns": removed_columns}
        except HTTPException:
            raise
        except Exception as exc:
            message = _sanitize_error(exc)
            missing = _missing_column_from_error(message)
            if missing and missing in working:
                removed_columns.append(missing)
                working.pop(missing, None)
                continue
            raise HTTPException(status_code=500, detail={"message": "Failed to update order.", "supabase_error": message, "removed_columns": removed_columns}) from exc
    raise HTTPException(status_code=500, detail={"message": "Failed to update order after fallback retries.", "removed_columns": removed_columns})


def update_order_status(request: OrderStatusUpdateRequest) -> dict[str, Any]:
    action = request.action.strip().lower()
    client = _supabase()

    if action in {"confirm_payment", "paid", "payment_confirmed"}:
        payload = {
            "status": "paid",
            "payment_confirmed_at": _now(),
            "deadline_at": _deadline_from_now(),
        }
        label = "Uplata potvrđena."
    elif action in {"start", "start_analysis", "in_progress"}:
        payload = {
            "status": "in_progress",
            "analysis_started_at": _now(),
        }
        label = "Izrada je pokrenuta."
    elif action in {"complete", "completed", "finish", "done"}:
        payload = {
            "status": "completed",
            "completed_at": _now(),
        }
        label = "Porudžbina je završena."
    elif action in {"received", "reset"}:
        payload = {
            "status": "received",
            "payment_confirmed_at": None,
            "analysis_started_at": None,
            "completed_at": None,
            "deadline_at": None,
        }
        label = "Porudžbina je vraćena na received."
    else:
        raise HTTPException(status_code=400, detail="Unknown order action.")

    result = _safe_update(client, request.order_id, payload)
    result["message"] = label
    result["action"] = action
    return result


def delete_order(request: OrderDeleteRequest) -> dict[str, Any]:
    client = _supabase()
    try:
        existing = client.table("orders").select("*").eq("id", request.order_id).limit(1).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Order not found.")
        deleted = client.table("orders").delete().eq("id", request.order_id).execute()
        return {
            "success": True,
            "message": "Porudžbina je obrisana.",
            "reason": request.reason,
            "deleted_order": deleted.data[0] if deleted.data else existing.data[0],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Failed to delete order.", "supabase_error": _sanitize_error(exc)}) from exc
