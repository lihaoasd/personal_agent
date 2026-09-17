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


@router.get("/chat/traces")
def get_traces(session_id: int, limit: int = 100, conn: ConnDep = None):
    """获取 Agent Loop 的 trace 日志。"""
    return repos.list_traces(conn, session_id=session_id, limit=limit)


# ---------- diaries ----------

from pydantic import BaseModel

class DiaryCreateRequest(BaseModel):
    diary_date: str
    title: str = ""
    content: str = ""
    mood: str = ""
    tags: str = ""
    goal_id: int | None = None


class DiaryUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    mood: str | None = None
    tags: str | None = None
    goal_id: int | None = None


@router.get("/diaries")
def list_diaries(start_date: str | None = None, end_date: str | None = None,
                 limit: int = 100, conn: ConnDep = None):
    return repos.list_diaries(conn, start_date=start_date, end_date=end_date, limit=limit)


@router.post("/diaries")
def create_diary(payload: DiaryCreateRequest, conn: ConnDep):
    diary_id = repos.insert_diary(
        conn, diary_date=payload.diary_date, title=payload.title,
        content=payload.content, mood=payload.mood, tags=payload.tags,
        goal_id=payload.goal_id,
    )
    return repos.get_diary(conn, diary_id)


@router.get("/diaries/{diary_id}")
def get_diary(diary_id: int, conn: ConnDep = None):
    d = repos.get_diary(conn, diary_id)
    if not d:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日记不存在")
    return d


@router.put("/diaries/{diary_id}")
def update_diary(diary_id: int, payload: DiaryUpdateRequest, conn: ConnDep = None):
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    repos.update_diary(conn, diary_id, **fields)
    return repos.get_diary(conn, diary_id)


@router.delete("/diaries/{diary_id}")
def delete_diary(diary_id: int, conn: ConnDep = None):
    repos.delete_diary(conn, diary_id)
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
