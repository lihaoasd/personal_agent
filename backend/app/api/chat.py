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


# ---------- 执行确认操作 ----------

class ConfirmActionRequest(BaseModel):
    action_type: str
    action_args: dict


@router.post("/chat/execute-action")
def execute_action(payload: ConfirmActionRequest, session_id: int, conn: ConnDep):
    """用户确认后，执行修改/删除操作，并让模型生成回复。"""
    from app.core.agent import _execute_tool
    from datetime import date
    today = date.today()
    result = _execute_tool(conn, payload.action_type, payload.action_args, today, skip_confirm=True)

    # 执行成功后，让模型基于结果生成回复
    if result.get("ok"):
        # 调用模型生成友好回复
        from ..core import llm, prompts
        action_type = payload.action_type
        args = payload.action_args
        action_desc = {
            "update_goal": "修改目标",
            "delete_goal": "删除目标",
            "update_schedule": "修改日程",
            "delete_schedule": "删除日程",
            "update_diary": "修改日记",
            "delete_diary": "删除日记",
        }.get(action_type, "操作")

        # 把操作内容整理成自然语言
        detail_parts = []
        if action_type == "update_goal":
            if args.get("new_title"): detail_parts.append(f"标题改成了「{args['new_title']}」")
            if args.get("reason"): detail_parts.append(f"初衷改成了「{args['reason']}」")
            if args.get("status"): detail_parts.append(f"状态改成了「{args['status']}」")
        elif action_type == "update_schedule":
            if args.get("new_title"): detail_parts.append(f"标题改成了「{args['new_title']}」")
            if args.get("new_start_at"): detail_parts.append(f"时间改成了「{args['new_start_at']}」")
            if args.get("note"): detail_parts.append(f"备注改成了「{args['note']}」")
            if args.get("status"): detail_parts.append(f"状态改成了「{args['status']}」")
        elif action_type == "delete_goal":
            detail_parts.append("已经把这个目标删除了")
        elif action_type == "delete_schedule":
            detail_parts.append("已经把这个日程删除了")
        elif action_type == "update_diary":
            if args.get("new_content"): detail_parts.append("内容更新了")
            if args.get("new_mood"): detail_parts.append(f"心情改成了「{args['new_mood']}」")
        elif action_type == "delete_diary":
            detail_parts.append("已经把这篇日记删除了")

        detail_text = "，".join(detail_parts) if detail_parts else result.get("message", "成功")

        messages = [
            {"role": "system", "content": prompts.CHAT_SYSTEM},
            {"role": "user", "content": f"用户确认了{action_desc}操作。具体修改：{detail_text}。请用一句简短可爱的话告诉用户结果，像朋友一样自然，1-2句话就行，不要太正式。"},
        ]
        try:
            resp = llm.chat_messages(messages)
            reply = resp.get("choices", [{}])[0].get("message", {}).get("content", f"好的～{action_desc}完成啦 🌱")
        except Exception:
            reply = f"好的～{detail_text} 🌱"
    else:
        reply = f"操作失败：{result.get('error', '未知错误')}"

    # 保存消息
    repos.insert_message(conn, role="assistant", content=reply, session_id=session_id)

    # 记录：审批完成
    repos.insert_trace(
        conn, session_id=session_id, user_message="（用户确认操作）", step=99,
        role="system", content=f"用户已确认，{action_desc}执行完成",
    )

    return {"reply": reply, "result": result}


@router.post("/chat/cancel-action")
def cancel_action(action_desc: str, session_id: int, conn: ConnDep):
    """用户取消操作，记录到 trace。"""
    repos.insert_trace(
        conn, session_id=session_id, user_message="（用户取消操作）", step=98,
        role="system", content=f"用户已取消：{action_desc}",
    )
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
