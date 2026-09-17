"""Agent 编排主流程：意图 → 心理学策略 → 业务执行 → 反馈生成。"""
from __future__ import annotations

from datetime import date, timedelta
from sqlite3 import Connection

from ..db import repos
from . import extractor, llm, prompts, psychology

SOURCE_BY_INTENT = {"checkin": "chat", "template": "template", "backfill": "backfill"}


def handle_chat(conn: Connection, message: str, today: date | None = None,
                session_id: int = 1) -> dict:
    """处理一条用户消息，返回回复文本与产生的记录。消息落库由本函数负责。"""
    today = today or date.today()
    today_str = today.isoformat()
    history = repos.recent_messages(conn, 10, session_id=session_id)
    goals = repos.active_goals(conn)
    for g in goals:
        g["tasks"] = repos.list_tasks(conn, g["id"])
    templates = repos.list_templates(conn)

    parsed = extractor.extract_intent(
        messages=history + [{"role": "user", "content": message}],
        goals=goals, templates=templates, today=today,
    )
    intent = parsed["intent"]
    # 心理学基调需基于「本次消息之前」的连续中断状态判定
    tone = psychology.decide_tone(conn, today_str, intent)

    created_ids: list[int] = []
    reply: str

    if intent in ("checkin", "template", "backfill"):
        reply = _handle_record(conn, message, parsed, today, tone, created_ids)
    elif intent == "goal_manage":
        reply = _handle_goal(conn, parsed)
    elif intent == "schedule":
        reply = _handle_schedule(conn, parsed)
    elif intent == "query":
        reply = _handle_query(conn, message, today)
    else:
        reply = llm.chat_text(prompts.CHAT_SYSTEM, message)

    repos.insert_message(conn, role="user", content=message, session_id=session_id)
    repos.insert_message(conn, role="assistant", content=reply, session_id=session_id)
    return {"reply": reply, "created_event_ids": created_ids, "intent": intent}


def _handle_record(conn: Connection, message: str, parsed: dict, today: date,
                   tone: str, created_ids: list[int]) -> str:
    goal_id = parsed.get("goal_id")
    if goal_id and not repos.get_goal(conn, goal_id):
        return _clarify(parsed)

    happened_on = parsed.get("happened_on") or today.isoformat()
    if happened_on > today.isoformat():
        return "补记日期不能是未来，请确认一下日期～"

    task_id = parsed.get("task_id")
    if task_id and not repos.get_task(conn, task_id):
        task_id = None

    event = parsed.get("event") or {}
    event_id = repos.insert_event(
        conn, goal_id=goal_id, task_id=task_id, content=message,
        event_type=event.get("event_type"), amount=event.get("amount"), unit=event.get("unit"),
        source=SOURCE_BY_INTENT[parsed["intent"]], happened_on=happened_on,
    )
    created_ids.append(event_id)

    task = repos.get_task(conn, task_id) if task_id else None
    if task and task["status"] != "done":
        repos.update_task(conn, task_id, status="done")

    goal = repos.get_goal(conn, goal_id) if goal_id else None
    progress = repos.goal_progress(conn, goal_id) if goal_id else None
    milestone = psychology.milestone_info(conn, event.get("event_type"))
    extra = f"用户刚完成同一类型记录第 {milestone['count']} 次，请给予简短里程碑庆祝。" if milestone else ""
    user = prompts.build_feedback_user(goal, progress, tone, today, user_message=message)
    if extra:
        user += "\n" + extra
    return llm.chat_text(prompts.CHAT_SYSTEM, user)


def _handle_goal(conn: Connection, parsed: dict) -> str:
    goal = parsed.get("goal") or {}
    title = (goal.get("title") or "").strip()
    if not title:
        return "你想设定什么目标？告诉我一句话就行，比如「9 月完成系统设计学习」。"
    gid = repos.insert_goal(conn, title=title, category=goal.get("category") or "general")
    return f"已创建目标「{title}」。可以到「目标」页用 AI 拆解子任务，或直接说「帮我拆解」。"


def _handle_schedule(conn: Connection, parsed: dict) -> str:
    s = parsed.get("schedule") or {}
    title = (s.get("title") or "").strip()
    if not title or not s.get("start_at"):
        return "收到，不过时间或事项不完整，请到「日程」页创建，或再说清楚一点，比如「明天下午 3 点健身」。"
    sid = repos.insert_schedule(conn, title=title, start_at=s["start_at"], end_at=s.get("end_at"))
    return f"已安排：{title}（{s['start_at']}）。"


def _handle_query(conn: Connection, message: str, today: date) -> str:
    week_start = today - timedelta(days=today.weekday())
    week_days = repos.distinct_days_between(conn, week_start.isoformat(), today.isoformat())
    goals = repos.active_goals(conn)
    goal_lines = []
    for g in goals:
        p = repos.goal_progress(conn, g["id"])
        goal_lines.append(f"「{g['title']}」{p['done_tasks']}/{p['total_tasks']}")
    recent = repos.recent_events(conn, 3)
    data = (
        f"本周已打卡 {week_days} 天。\n"
        f"目标进度：{'；'.join(goal_lines) if goal_lines else '暂无进行中目标'}。\n"
        f"最近记录：{'；'.join(e['content'] for e in recent) if recent else '暂无'}。"
    )
    return llm.chat_text(prompts.CHAT_SYSTEM, f"用户问题：{message}\n\n可用的真实数据：\n{data}\n请基于数据回答，数据不足就明说。")


def _clarify(parsed: dict) -> str:
    hint = parsed.get("need_clarify")
    return f"我没法确定这次记录关联哪个目标（{hint or '请补充目标'}）。你可以说「帮我记到『9 月学完系统设计』」，或者我直接记成无关联的习惯记录，回「直接记」即可。"
