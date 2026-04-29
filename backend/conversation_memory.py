from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from supabase import create_client


class ConversationMessage(BaseModel):
    conversation_id: str | None = None
    channel: str = "instagram_dm"
    external_user_id: str | None = None
    instagram_username: str | None = None
    client_name: str | None = None
    role: str
    content: str
    metadata: dict[str, Any] = {}


class ConversationLoadRequest(BaseModel):
    conversation_id: str | None = None
    channel: str = "instagram_dm"
    external_user_id: str | None = None
    instagram_username: str | None = None
    limit: int = 12


class ConversationStateUpdate(BaseModel):
    conversation_id: str | None = None
    channel: str = "instagram_dm"
    external_user_id: str | None = None
    instagram_username: str | None = None
    client_name: str | None = None
    state: dict[str, Any] = {}


def _supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase is not configured.")
    return create_client(url, key)


def _sanitize_error(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _conversation_key(request: ConversationLoadRequest | ConversationMessage | ConversationStateUpdate) -> str:
    if request.conversation_id:
        return request.conversation_id
    if request.external_user_id:
        return f"{request.channel}:external:{request.external_user_id}"
    if request.instagram_username:
        return f"{request.channel}:ig:{request.instagram_username.lower().lstrip('@')}"
    raise HTTPException(status_code=400, detail="conversation_id, external_user_id or instagram_username is required.")


def _ensure_conversation(client, key: str, request: ConversationLoadRequest | ConversationMessage | ConversationStateUpdate) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "conversation_id": key,
        "channel": request.channel,
        "external_user_id": getattr(request, "external_user_id", None),
        "instagram_username": getattr(request, "instagram_username", None),
        "client_name": getattr(request, "client_name", None),
        "updated_at": now,
    }
    try:
        existing = client.table("conversations").select("*").eq("conversation_id", key).limit(1).execute()
        if existing.data:
            update_payload = {k: v for k, v in payload.items() if v is not None and k != "conversation_id"}
            client.table("conversations").update(update_payload).eq("conversation_id", key).execute()
            return existing.data[0]
        payload["created_at"] = now
        payload["state"] = {}
        created = client.table("conversations").insert(payload).execute()
        return created.data[0] if created.data else payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Conversation table is not ready.", "supabase_error": _sanitize_error(exc), "required_tables": ["conversations", "conversation_messages"]}) from exc


def save_message(request: ConversationMessage) -> dict[str, Any]:
    client = _supabase()
    key = _conversation_key(request)
    _ensure_conversation(client, key, request)
    payload = {
        "conversation_id": key,
        "channel": request.channel,
        "role": request.role,
        "content": request.content,
        "metadata": request.metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        inserted = client.table("conversation_messages").insert(payload).execute()
        return {"success": True, "conversation_id": key, "message": inserted.data[0] if inserted.data else payload}
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Failed to save conversation message.", "supabase_error": _sanitize_error(exc)}) from exc


def load_conversation(request: ConversationLoadRequest) -> dict[str, Any]:
    client = _supabase()
    key = _conversation_key(request)
    _ensure_conversation(client, key, request)
    try:
        state_res = client.table("conversations").select("*").eq("conversation_id", key).limit(1).execute()
        messages_res = (
            client.table("conversation_messages")
            .select("role,content,metadata,created_at")
            .eq("conversation_id", key)
            .order("created_at", desc=True)
            .limit(max(1, min(request.limit, 50)))
            .execute()
        )
        messages = list(reversed(messages_res.data or []))
        return {"success": True, "conversation_id": key, "conversation": (state_res.data or [{}])[0], "messages": messages}
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Failed to load conversation.", "supabase_error": _sanitize_error(exc)}) from exc


def update_state(request: ConversationStateUpdate) -> dict[str, Any]:
    client = _supabase()
    key = _conversation_key(request)
    _ensure_conversation(client, key, request)
    payload = {
        "state": request.state,
        "client_name": request.client_name,
        "instagram_username": request.instagram_username,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    try:
        updated = client.table("conversations").update(payload).eq("conversation_id", key).execute()
        return {"success": True, "conversation_id": key, "conversation": updated.data[0] if updated.data else payload}
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Failed to update conversation state.", "supabase_error": _sanitize_error(exc)}) from exc
