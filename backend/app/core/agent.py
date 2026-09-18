"""Agent 编排主流程：支持简单模式和 Agent Loop 模式。"""
from __future__ import annotations

import json
from datetime import date, timedelta
from sqlite3 import Connection

from ..db import repos
from . import extractor, llm, prompts, psychology

SOURCE_BY_INTENT = {"checkin": "chat", "template": "template", "backfill": "backfill"}

# Agent Loop 模式的工具定义
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "record_checkin",
            "description": "记录用户的打卡/事件/运动/阅读等行为",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "记录内容，比如'跑步30分钟'"},
                    "goal_title": {"type": "string", "description": "关联的目标名称，可选"},
                    "happened_on": {"type": "string", "description": "日期 YYYY-MM-DD，默认今天"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": "创建新目标。必须提供目标标题和设立理由（初衷）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "目标标题，比如'3个月跑完半马'"},
                    "reason": {"type": "string", "description": "设立目标的初衷/理由，为什么想做这件事"},
                },
                "required": ["title", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_schedule",
            "description": "创建日程/安排提醒。必须提供标题和开始时间。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "日程标题，比如'下午3点开会'"},
                    "start_at": {"type": "string", "description": "开始时间，格式 YYYY-MM-DD HH:MM"},
                    "note": {"type": "string", "description": "备注，可选"},
                },
                "required": ["title", "start_at"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_diary",
            "description": "写一篇日记。必须提供日记内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "日记内容，markdown 格式"},
                    "mood": {"type": "string", "description": "心情 emoji，比如 😊 😌 😢，可选"},
                    "diary_date": {"type": "string", "description": "日期 YYYY-MM-DD，默认今天"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_review",
            "description": "写一篇复盘。必须提供复盘内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "复盘内容，markdown 格式"},
                    "period_type": {"type": "string", "enum": ["weekly", "monthly"], "description": "周期类型，默认 weekly"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal",
            "description": "修改目标的所有字段：标题、理由、状态等。必须指定目标 ID（先查询获取）。注意：调用前必须先向用户说明要改什么。",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer", "description": "要修改的目标 ID（从 query_status 结果中获取）"},
                    "new_title": {"type": "string", "description": "新的目标标题，可选"},
                    "reason": {"type": "string", "description": "新的初衷/理由，可选"},
                    "category": {"type": "string", "enum": ["general", "learning", "health", "habit"], "description": "新的分类，可选"},
                    "status": {"type": "string", "enum": ["active", "completed", "abandoned"], "description": "新的状态，可选"},
                    "abandon_reason": {"type": "string", "description": "放弃理由，如果状态是 abandoned 必填"},
                },
                "required": ["goal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_schedule",
            "description": "修改日程的所有字段：标题、时间、备注、状态等。必须指定日程 ID（先查询获取）。注意：调用前必须先向用户说明要改什么。",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {"type": "integer", "description": "要修改的日程 ID（从 query_status 结果中获取）"},
                    "new_title": {"type": "string", "description": "新的标题，可选"},
                    "new_start_at": {"type": "string", "description": "新的开始时间，格式 YYYY-MM-DD HH:MM，可选"},
                    "note": {"type": "string", "description": "新的备注，可选"},
                    "duration_min": {"type": "integer", "description": "新的时长（分钟），可选"},
                    "status": {"type": "string", "enum": ["pending", "done", "cancelled"], "description": "新的状态，可选"},
                },
                "required": ["schedule_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_diary",
            "description": "修改日记的所有字段：内容、心情、标签等。必须指定日记 ID（先查询获取）。注意：调用前必须先向用户说明要改什么。",
            "parameters": {
                "type": "object",
                "properties": {
                    "diary_id": {"type": "integer", "description": "要修改的日记 ID（从 query_status 结果中获取）"},
                    "new_content": {"type": "string", "description": "新的内容，可选"},
                    "new_mood": {"type": "string", "description": "新的心情 emoji，可选"},
                    "new_tags": {"type": "string", "description": "新的标签（逗号分隔），可选"},
                },
                "required": ["diary_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_goal",
            "description": "删除目标。注意：删除前必须先向用户确认！confirmed 参数必须为 true 才会真正执行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_title": {"type": "string", "description": "要删除的目标名称"},
                    "confirmed": {"type": "boolean", "description": "用户是否已确认，必须为 true 才会真正执行"},
                },
                "required": ["goal_title", "confirmed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_schedule",
            "description": "删除日程。注意：删除前必须先向用户确认！confirmed 参数必须为 true 才会真正执行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_title": {"type": "string", "description": "要删除的日程标题"},
                    "confirmed": {"type": "boolean", "description": "用户是否已确认，必须为 true 才会真正执行"},
                },
                "required": ["schedule_title", "confirmed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_diary",
            "description": "删除日记。注意：删除前必须先向用户确认！confirmed 参数必须为 true 才会真正执行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "diary_date": {"type": "string", "description": "要删除的日记日期 YYYY-MM-DD"},
                    "confirmed": {"type": "boolean", "description": "用户是否已确认，必须为 true 才会真正执行"},
                },
                "required": ["diary_date", "confirmed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_status",
            "description": "查询用户的目标进度、打卡记录、日程、日记等数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["goals", "checkins", "schedules", "diaries", "reviews", "all"],
                        "description": "查询类型",
                    },
                },
                "required": ["query_type"],
            },
        },
    },
]


def handle_chat(conn: Connection, message: str, today: date | None = None,
                session_id: int = 1) -> dict:
    """处理一条用户消息，根据用户选择的模式走简单模式或 Agent Loop。"""
    today = today or date.today()
    # 读取用户选择的模式
    mode = repos.state_get(conn, "chat_mode") or "simple"
    if mode == "agent":
        return _handle_agent_loop(conn, message, today, session_id)
    return _handle_simple(conn, message, today, session_id)


def _handle_simple(conn: Connection, message: str, today: date, session_id: int) -> dict:
    """原来的简单模式：意图分流。"""
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
    return {"reply": reply, "created_event_ids": created_ids, "intent": intent, "mode": "simple"}


def _handle_agent_loop(conn: Connection, message: str, today: date, session_id: int) -> dict:
    """Agent Loop 模式：模型自己决定调用工具，循环执行。所有过程记录到 trace。"""
    today_str = today.isoformat()
    history = repos.recent_messages(conn, 20, session_id=session_id)
    
    # 构建 messages
    system_prompt = prompts.CHAT_SYSTEM + f"""

当前时间：{today_str}（{['周一','周二','周三','周四','周五','周六','周日'][today.weekday()]}）

【操作规则】
1. 创建类操作（创建目标、日程、日记、复盘）：信息完整就直接执行，不用反复确认
2. 修改类操作（修改目标、日程、日记）：
   - 必须先调用 query_status 查询，拿到对应的 id
   - 然后再调用 update_xxx 工具，传对应的 id
   - 不要瞎编 id，必须从查询结果里拿
3. 删除类操作（删除目标、日程、日记）：
   - 必须先调用 query_status 查询，拿到对应的 id
   - 然后再调用 delete_xxx 工具，传对应的 id
   - 不要瞎编 id，必须从查询结果里拿
4. 查询类操作：直接执行，不用确认

【重要】修改和删除工具都需要传 id（goal_id / schedule_id / diary_id），这个 id 必须从 query_status 的查询结果里拿，不能自己编！"""
    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    created_ids: list[int] = []
    max_loops = 5  # 最多循环 5 次，防止死循环
    step = 0

    # 记录用户消息
    step += 1
    repos.insert_trace(
        conn, session_id=session_id, user_message=message, step=step,
        role="user", content=message,
    )
    # 记录系统提示词和上下文
    repos.insert_trace(
        conn, session_id=session_id, user_message=message, step=step,
        role="system", content=f"系统提示词长度：{len(system_prompt)} 字\n历史消息：{len(history)} 条\n工具数量：{len(AGENT_TOOLS)} 个",
        tool_name="system_prompt",
    )

    import time
    for _ in range(max_loops):
        step += 1
        step += 1
        t0 = time.perf_counter()
        resp_data = llm.chat_messages(messages, tools=AGENT_TOOLS)
        elapsed = int((time.perf_counter() - t0) * 1000)
        resp = resp_data.get("choices", [{}])[0].get("message", {})
        usage = resp_data.get("usage", {})
        model_name = resp_data.get("model", "")
        
        # 记录模型输出：思考一条，回复一条
        tool_names = ",".join(t["function"]["name"] for t in resp.get("tool_calls", []))
        reasoning = resp.get("reasoning_content", "")
        final_content = resp.get("content", "")

        # 模型思考
        if reasoning:
            repos.insert_trace(
                conn, session_id=session_id, user_message=message, step=step,
                role="assistant", content=reasoning,
            )
            step += 1

        # 模型回复
        if final_content:
            repos.insert_trace(
                conn, session_id=session_id, user_message=message, step=step,
                role="assistant", content=final_content,
                tool_name=tool_names,
            )
            step += 1
        
        # 没有工具调用，直接输出回复
        if not resp.get("tool_calls"):
            reply = resp.get("content", "")
            repos.insert_message(conn, role="user", content=message, session_id=session_id)
            repos.insert_message(conn, role="assistant", content=reply, session_id=session_id)
            return {"reply": reply, "created_event_ids": created_ids, "intent": "agent_loop", "mode": "agent"}

        # 把 assistant 的工具调用加进 messages
        messages.append({
            "role": "assistant",
            "content": resp.get("content", ""),
            "tool_calls": resp["tool_calls"],
        })

        # 执行每个工具调用
        pending_action = None
        for tool_call in resp["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            args_str = tool_call["function"]["arguments"] or "{}"
            args = json.loads(args_str)
            result = _execute_tool(conn, tool_name, args, today)
            created_ids.extend(result.get("event_ids", []))
            
            # 工具调用 + 返回结果 合并成一条
            repos.insert_trace(
                conn, session_id=session_id, user_message=message, step=step,
                role="tool", content=f"调用工具：{tool_name}",
                tool_name=tool_name, tool_args=args_str,
                tool_result=json.dumps(result, ensure_ascii=False),
            )
            step += 1
            
            # 检查是否有待确认操作
            if result.get("pending_confirmation"):
                pending_action = result
                break
            
            # 把工具结果加进 messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })
        
        # 有待确认操作，直接返回给前端
        if pending_action:
            # 记录：发起审批
            step += 1
            repos.insert_trace(
                conn, session_id=session_id, user_message=message, step=step,
                role="system", content=f"待确认操作：{pending_action['action_desc']}「{pending_action.get('display_name', '')}」",
            )
            repos.insert_message(conn, role="user", content=message, session_id=session_id)
            return {
                "reply": "",
                "created_event_ids": created_ids,
                "intent": "agent_loop",
                "mode": "agent",
                "pending_action": pending_action,
            }

    # 超过最大循环次数，直接问模型要最终回复
    step += 1
    messages.append({"role": "user", "content": "请基于以上信息直接回复我。"})
    t0 = time.perf_counter()
    resp_data = llm.chat_messages(messages)
    elapsed = int((time.perf_counter() - t0) * 1000)
    resp = resp_data.get("choices", [{}])[0].get("message", {})
    usage = resp_data.get("usage", {})
    reply = resp.get("content", "好的～")
    reasoning = resp.get("reasoning_content", "")
    # 模型思考
    if reasoning:
        repos.insert_trace(
            conn, session_id=session_id, user_message=message, step=step,
            role="assistant", content=reasoning,
        )
        step += 1
    # 模型回复
    repos.insert_trace(
        conn, session_id=session_id, user_message=message, step=step,
        role="assistant", content=reply,
    )
    repos.insert_message(conn, role="user", content=message, session_id=session_id)
    repos.insert_message(conn, role="assistant", content=reply, session_id=session_id)
    return {"reply": reply, "created_event_ids": created_ids, "intent": "agent_loop", "mode": "agent"}


def _execute_tool(conn: Connection, name: str, args: dict, today: date, skip_confirm: bool = False) -> dict:
    """执行 Agent 工具调用。"""
    today_str = today.isoformat()

    # 修改/删除类工具必须前端确认（除非 skip_confirm=True，用户已确认）
    confirm_tools = {
        "update_goal": "修改目标",
        "update_schedule": "修改日程",
        "update_diary": "修改日记",
        "delete_goal": "删除目标",
        "delete_schedule": "删除日程",
        "delete_diary": "删除日记",
    }
    if name in confirm_tools and not skip_confirm:
        # 查一下要修改/删除的标题，方便前端显示
        display_name = ""
        if name in ("update_goal", "delete_goal") and args.get("goal_id"):
            goals = repos.list_goals(conn)
            for g in goals:
                if g["id"] == args["goal_id"]:
                    display_name = g["title"]
                    break
        elif name in ("update_schedule", "delete_schedule") and args.get("schedule_id"):
            from datetime import timedelta
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = (today + timedelta(days=90)).isoformat()
            schedules = repos.list_schedules_between(conn, start_date, end_date)
            for s in schedules:
                if s["id"] == args["schedule_id"]:
                    display_name = s["title"]
                    break
        elif name in ("update_diary", "delete_diary") and args.get("diary_id"):
            diaries = repos.list_diaries(conn, limit=200)
            for d in diaries:
                if d["id"] == args["diary_id"]:
                    display_name = d.get("title", d["diary_date"])
                    break
        return {
            "pending_confirmation": True,
            "action_type": name,
            "action_desc": confirm_tools[name],
            "action_args": args,
            "display_name": display_name,
            "message": f"待确认：{confirm_tools[name]}「{display_name}」，请向用户展示确认弹窗",
        }

    if name == "record_checkin":
        content = args.get("content", "")
        happened_on = args.get("happened_on") or today_str
        goal_title = args.get("goal_title")
        goal_id = None
        # 找目标
        if goal_title:
            goals = repos.active_goals(conn)
            for g in goals:
                if goal_title in g["title"] or g["title"] in goal_title:
                    goal_id = g["id"]
                    break
        event_id = repos.insert_event(
            conn, goal_id=goal_id, task_id=None, content=content,
            event_type=None, amount=None, unit=None,
            source="chat", happened_on=happened_on,
        )
        return {"ok": True, "event_ids": [event_id], "message": f"已记录：{content}"}

    elif name == "create_goal":
        title = args.get("title", "")
        reason = args.get("reason", "")
        gid = repos.insert_goal(conn, title=title, category="general")
        if reason:
            # 更新目标理由
            conn.execute("UPDATE goals SET reason = ? WHERE id = ?", (reason, gid))
            conn.commit()
        return {"ok": True, "goal_id": gid, "message": f"已创建目标：{title}"}

    elif name == "create_schedule":
        title = args.get("title", "")
        start_at = args.get("start_at", "")
        note = args.get("note", "")
        sid = repos.insert_schedule(conn, title=title, start_at=start_at)
        if note:
            conn.execute("UPDATE schedules SET note = ? WHERE id = ?", (note, sid))
            conn.commit()
        return {"ok": True, "schedule_id": sid, "message": f"已安排日程：{title}"}

    elif name == "create_diary":
        diary_date = args.get("diary_date") or today_str
        diary_content = args.get("content", "")
        mood = args.get("mood", "")
        did = repos.insert_diary(conn, diary_date=diary_date, content=diary_content, mood=mood)
        return {"ok": True, "diary_id": did, "message": "日记已保存"}

    elif name == "create_review":
        review_content = args.get("content", "")
        period_type = args.get("period_type", "weekly")
        # 计算周期
        if period_type == "weekly":
            period_start = (today - timedelta(days=today.weekday())).isoformat()
            period_end = today_str
        else:
            period_start = today.replace(day=1).isoformat()
            period_end = today_str
        rid = repos.insert_review(
            conn, period_type=period_type,
            period_start=period_start, period_end=period_end,
            content=review_content,
        )
        return {"ok": True, "review_id": rid, "message": "复盘已保存"}

    elif name == "update_goal":
        gid = args.get("goal_id")
        if not gid:
            return {"ok": False, "error": "缺少 goal_id"}
        updates = {}
        if args.get("new_title"):
            updates["title"] = args["new_title"]
        if args.get("reason"):
            updates["reason"] = args["reason"]
        if args.get("category"):
            updates["category"] = args["category"]
        if args.get("status"):
            updates["status"] = args["status"]
            if args["status"] == "abandoned" and args.get("abandon_reason"):
                updates["abandon_reason"] = args["abandon_reason"]
        if updates:
            repos.update_goal(conn, gid, **updates)
        return {"ok": True, "goal_id": gid, "message": "已更新目标"}

    elif name == "update_schedule":
        sid = args.get("schedule_id")
        if not sid:
            return {"ok": False, "error": "缺少 schedule_id"}
        updates = {}
        if args.get("new_title"):
            updates["title"] = args["new_title"]
        if args.get("new_start_at"):
            updates["start_at"] = args["new_start_at"]
        if args.get("note"):
            updates["note"] = args["note"]
        if args.get("duration_min"):
            updates["duration_min"] = args["duration_min"]
        if args.get("status"):
            updates["status"] = args["status"]
        if updates:
            repos.update_schedule(conn, sid, **updates)
        return {"ok": True, "schedule_id": sid, "message": "已更新日程"}

    elif name == "update_diary":
        did = args.get("diary_id")
        if not did:
            return {"ok": False, "error": "缺少 diary_id"}
        updates = {}
        if args.get("new_content"):
            updates["content"] = args["new_content"]
        if args.get("new_mood"):
            updates["mood"] = args["new_mood"]
        if args.get("new_tags"):
            updates["tags"] = args["new_tags"]
        if updates:
            repos.update_diary(conn, did, **updates)
        return {"ok": True, "diary_id": did, "message": "日记已更新"}

    elif name == "delete_goal":
        goal_title = args.get("goal_title", "")
        goals = repos.active_goals(conn)
        target = None
        for g in goals:
            if goal_title in g["title"] or g["title"] in goal_title:
                target = g
                break
        if not target:
            return {"ok": False, "error": f"没找到目标：{goal_title}"}
        repos.delete_goal(conn, target["id"])
        return {"ok": True, "message": f"已删除目标：{target['title']}"}

    elif name == "delete_schedule":
        schedule_title = args.get("schedule_title", "")
        from datetime import timedelta
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = (today + timedelta(days=90)).isoformat()
        schedules = repos.list_schedules_between(conn, start_date, end_date)
        target = None
        for s in schedules:
            if schedule_title in s["title"] or s["title"] in schedule_title:
                target = s
                break
        if not target:
            return {"ok": False, "error": f"没找到日程：{schedule_title}"}
        repos.delete_schedule(conn, target["id"])
        return {"ok": True, "message": f"已删除日程：{target['title']}"}

    elif name == "delete_diary":
        diary_date = args.get("diary_date", "")
        diaries = repos.list_diaries(conn, limit=200)
        target = None
        for d in diaries:
            if d["diary_date"] == diary_date:
                target = d
                break
        if not target:
            return {"ok": False, "error": f"没找到 {diary_date} 的日记"}
        repos.delete_diary(conn, target["id"])
        return {"ok": True, "message": f"已删除 {diary_date} 的日记"}

    elif name == "query_status":
        qtype = args.get("query_type", "all")
        result = {}
        if qtype in ("goals", "all"):
            goals = repos.list_goals(conn)
            goal_list = []
            for g in goals:
                p = repos.goal_progress(conn, g["id"])
                goal_list.append({
                    "id": g["id"],
                    "title": g["title"],
                    "category": g.get("category", "general"),
                    "status": g["status"],
                    "reason": g.get("reason", ""),
                    "abandon_reason": g.get("abandon_reason", ""),
                    "progress": f"{p['done_tasks']}/{p['total_tasks']}",
                })
            result["goals"] = goal_list
        if qtype in ("checkins", "all"):
            week_start = today - timedelta(days=today.weekday())
            days = repos.distinct_days_between(conn, week_start.isoformat(), today_str)
            result["week_checkin_days"] = days
        if qtype in ("schedules", "all"):
            start_date = (today - timedelta(days=7)).isoformat()
            end_date = (today + timedelta(days=30)).isoformat()
            schedules = repos.list_schedules_between(conn, start_date, end_date)
            schedule_list = []
            for s in schedules:
                schedule_list.append({
                    "id": s["id"],
                    "title": s["title"],
                    "start_at": s["start_at"],
                    "end_at": s.get("end_at", ""),
                    "note": s.get("note", ""),
                    "duration_min": s.get("duration_min", ""),
                    "status": s["status"],
                })
            result["schedules"] = schedule_list
        if qtype in ("diaries", "all"):
            diaries = repos.list_diaries(conn, limit=10)
            diary_list = []
            for d in diaries:
                diary_list.append({
                    "id": d["id"],
                    "title": d.get("title", ""),
                    "diary_date": d["diary_date"],
                    "mood": d.get("mood", ""),
                    "tags": d.get("tags", ""),
                    "content_preview": d.get("content", "")[:100] + ("..." if len(d.get("content", "")) > 100 else ""),
                })
            result["diaries"] = diary_list
        if qtype in ("reviews", "all"):
            reviews = repos.list_reviews(conn, period_type="all", limit=5)
            review_list = []
            for r in reviews:
                review_list.append({
                    "id": r["id"],
                    "title": r.get("title", ""),
                    "period_type": r["period_type"],
                    "period_start": r.get("period_start", ""),
                    "period_end": r.get("period_end", ""),
                })
            result["reviews"] = review_list
        return {"ok": True, "data": result}

    return {"ok": False, "message": f"未知工具：{name}"}


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
