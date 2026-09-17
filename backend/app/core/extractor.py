"""意图识别与结构化抽取：把用户消息解析为可执行意图。"""
from __future__ import annotations

from datetime import date, datetime

from . import llm
from . import prompts

INTENTS = {"checkin", "template", "backfill", "goal_manage", "schedule", "query", "chat"}


def extract_intent(*, messages: list[dict], goals: list[dict], templates: list[dict], today: date) -> dict:
    """调用 LLM 解析意图，返回规范化后的 JSON。"""
    parsed = llm.chat_json(
        prompts.EXTRACT_SYSTEM,
        prompts.build_extract_user(messages, goals, templates, today),
    )
    return _normalize(parsed, today)


def _normalize(parsed: dict, today: date) -> dict:
    intent = parsed.get("intent", "chat")
    if intent not in INTENTS:
        intent = "chat"

    event = parsed.get("event") if isinstance(parsed.get("event"), dict) else None
    if event is not None:
        event = {
            "event_type": event.get("event_type"),
            "amount": event.get("amount"),
            "unit": event.get("unit"),
        }

    schedule = parsed.get("schedule") if isinstance(parsed.get("schedule"), dict) else None
    if schedule is not None:
        schedule = {
            "title": schedule.get("title"),
            "start_at": schedule.get("start_at"),
            "end_at": schedule.get("end_at"),
        }

    goal = parsed.get("goal") if isinstance(parsed.get("goal"), dict) else None

    happened_on = parsed.get("happened_on")
    if happened_on and _is_future(happened_on, today):
        happened_on = None  # 未来日期按无效处理，交由服务层澄清

    return {
        "intent": intent,
        "goal_id": parsed.get("goal_id"),
        "task_id": parsed.get("task_id"),
        "event": event,
        "happened_on": happened_on,
        "schedule": schedule,
        "goal": goal,
        "need_clarify": parsed.get("need_clarify"),
    }


def _is_future(day: str, today: date) -> bool:
    try:
        return date.fromisoformat(day) > today
    except (ValueError, TypeError):
        return True
