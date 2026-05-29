"""
Per-user chat history, persisted in Supabase.

Each conversation is a single row in public.conversations holding the full
message list as a JSONB blob. Messages carry rich UI data (follow-up
suggestions and the Chunk "sources" used for an answer); the (de)serialization
helpers here convert Chunk objects to/from plain dicts so they round-trip
through JSON cleanly.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.auth import _supabase
from src.indexer import Chunk

CONVERSATIONS_TABLE = "conversations"


# ── Chunk <-> dict serialization ────────────────────────────────────────────

def _chunk_to_dict(c: Chunk) -> dict:
    return {
        "url": c.url,
        "text": c.text,
        "chunk_id": int(getattr(c, "chunk_id", 0)),
        "score": float(getattr(c, "score", 0.0)),
    }


def _dict_to_chunk(d: dict) -> Chunk:
    return Chunk(
        url=d.get("url", ""),
        text=d.get("text", ""),
        chunk_id=int(d.get("chunk_id", 0)),
        score=float(d.get("score", 0.0)),
    )


def _serialize_messages(messages: list[dict]) -> list[dict]:
    """Make a JSON-safe copy of the session message list."""
    out: list[dict] = []
    for m in messages:
        item = {"role": m["role"], "content": m["content"]}
        if m.get("followups"):
            item["followups"] = list(m["followups"])
        if m.get("sources"):
            item["sources"] = [_chunk_to_dict(c) for c in m["sources"]]
        out.append(item)
    return out


def _deserialize_messages(rows: list[dict]) -> list[dict]:
    """Rebuild the session message list, restoring Chunk source objects."""
    out: list[dict] = []
    for m in rows or []:
        item = {"role": m.get("role", ""), "content": m.get("content", "")}
        if m.get("followups"):
            item["followups"] = list(m["followups"])
        if m.get("sources"):
            item["sources"] = [_dict_to_chunk(d) for d in m["sources"]]
        out.append(item)
    return out


def history_from_messages(messages: list[dict]) -> list[dict]:
    """Rebuild the plain role/content list the LLM uses for context."""
    return [{"role": m["role"], "content": m["content"]} for m in messages]


def _title_from_messages(messages: list[dict]) -> str:
    """Derive a short conversation title from the first user message."""
    for m in messages:
        if m.get("role") == "user" and m.get("content"):
            t = m["content"].strip().replace("\n", " ")
            return (t[:48] + "…") if len(t) > 48 else t
    return "New chat"


# ── Public API ──────────────────────────────────────────────────────────────

def list_conversations(user_id: int) -> list[dict]:
    """Return [{id, title, updated_at}, …] for a user, newest first."""
    resp = (
        _supabase()
        .table(CONVERSATIONS_TABLE)
        .select("id, title, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return resp.data or []


def load_conversation(conv_id: str) -> list[dict]:
    """Load a conversation's messages (with Chunk sources restored)."""
    resp = (
        _supabase()
        .table(CONVERSATIONS_TABLE)
        .select("messages")
        .eq("id", conv_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return []
    return _deserialize_messages(rows[0].get("messages"))


def save_conversation(user_id: int, conv_id: str | None, messages: list[dict]) -> str:
    """
    Upsert a conversation and return its id.

    If conv_id is None a new conversation row is created (titled from the first
    user message); otherwise the existing row's messages/title/updated_at are
    updated.
    """
    payload = {
        "user_id": user_id,
        "title": _title_from_messages(messages),
        "messages": _serialize_messages(messages),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    client = _supabase()
    if conv_id is None:
        resp = client.table(CONVERSATIONS_TABLE).insert(payload).execute()
        return resp.data[0]["id"]

    client.table(CONVERSATIONS_TABLE).update(payload).eq("id", conv_id).execute()
    return conv_id


def delete_conversation(conv_id: str) -> None:
    _supabase().table(CONVERSATIONS_TABLE).delete().eq("id", conv_id).execute()
