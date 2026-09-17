"""目标拆解：LLM 生成目标标题与子任务。"""
from __future__ import annotations

from . import llm, prompts

ALLOWED_TYPES = ("course", "book", "practice", "task")


def plan_tasks(description: str) -> dict:
    """根据目标描述生成 {title, target_date, tasks}，失败时返回空 tasks。"""
    try:
        parsed = llm.chat_json(prompts.PLAN_SYSTEM, prompts.build_plan_user(description))
    except llm.LLMError:
        return {"title": None, "target_date": None, "tasks": []}
    tasks = []
    for t in parsed.get("tasks") or []:
        title = (t.get("title") or "").strip()
        if not title:
            continue
        item_type = t.get("item_type") or "task"
        if item_type not in ALLOWED_TYPES:
            item_type = "task"
        tasks.append({"title": title, "item_type": item_type})
    return {
        "title": (parsed.get("title") or "").strip() or None,
        "target_date": parsed.get("target_date") or None,
        "tasks": tasks,
    }


def create_goal_with_plan(conn, *, description: str, category: str = "general", reason: str = "") -> dict:
    """拆解并落库目标与子任务（单事务由调用方保证）。"""
    from ..db import repos

    plan = plan_tasks(description)
    title = plan["title"] or description[:40]
    goal_id = repos.insert_goal(conn, title=title, description=description, reason=reason,
                                category=category, target_date=plan["target_date"])
    for t in plan["tasks"]:
        repos.insert_task(conn, goal_id=goal_id, title=t["title"], item_type=t["item_type"])
    return {"goal_id": goal_id, "title": title, "tasks": plan["tasks"]}
