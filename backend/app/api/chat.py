"""对话 / 打卡 / 补记接口。"""
from __future__ import annotations

from datetime import date
from sqlite3 import Connection
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core import llm
from ..db import repos
from ..schemas.models import BackfillRequest, ChatRequest
from ..services import chat_service
from .deps import get_conn

router = APIRouter(prefix="/api", tags=["chat"])
ConnDep = Annotated[Connection, Depends(get_conn)]


class ChatSendRequest(BaseModel):
    message: str
    session_id: int = 1


class SessionTitleRequest(BaseModel):
    title: str


@router.post("/chat")
def chat(payload: ChatSendRequest, conn: ConnDep):
    try:
        return chat_service.handle_message(conn, payload.message, date.today(), payload.session_id)
    except llm.LLMError as exc:
        conn.rollback()
        raise HTTPException(status_code=502, detail=f"LLM 不可用：{exc}")


@router.get("/chat/sessions")
def chat_sessions(conn: ConnDep, limit: int = 500):
    limit = max(1, min(limit, 1000))
    return repos.list_sessions(conn, limit=limit)


@router.post("/chat/new")
def chat_new(conn: ConnDep):
    session_id = repos.create_session(conn)
    return {"session_id": session_id}


@router.get("/chat/messages")
def chat_messages(session_id: int = 1, limit: int = 500, before_id: int | None = None, conn: ConnDep = None):
    limit = max(1, min(limit, 1000))
    return repos.list_messages(conn, limit=limit, session_id=session_id, before_id=before_id)


@router.patch("/chat/sessions/{session_id}")
def update_session(session_id: int, payload: SessionTitleRequest, conn: ConnDep):
    repos.update_session_title(conn, session_id, payload.title.strip())
    return {"ok": True}


@router.delete("/chat/sessions/{session_id}")
def delete_session(session_id: int, conn: ConnDep):
    repos.delete_session(conn, session_id)
    return {"ok": True}


@router.post("/checkin/backfill")
def backfill(payload: BackfillRequest, conn: ConnDep):
    today = date.today()
    if payload.happened_on > today.isoformat():
        raise HTTPException(status_code=400, detail="补记日期不能是未来日期")
    goal_id = payload.goal_id
    if goal_id and not repos.get_goal(conn, goal_id):
        raise HTTPException(status_code=404, detail="目标不存在")
    event_id = repos.insert_event(
        conn, goal_id=goal_id, task_id=None, content=payload.content,
        event_type=None, amount=None, unit=None, source="backfill",
        happened_on=payload.happened_on,
    )
    repos.state_set(conn, "checkin_pending", "0")
    return {"event_id": event_id}


@router.get("/messages")
def list_messages(conn: ConnDep, limit: int = 50):
    limit = max(1, min(limit, 100))
    return repos.list_messages(conn, limit)
