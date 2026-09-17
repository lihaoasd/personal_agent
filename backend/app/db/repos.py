"""数据访问层：所有 SQL 集中在仓储函数中，函数接收连接作为首个参数。"""
from __future__ import annotations

import json
from datetime import datetime
from sqlite3 import Connection

_ZERO = datetime.min.isoformat()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _row(row) -> dict | None:
    return dict(row) if row is not None else None


# ---------- goals ----------

def insert_goal(conn: Connection, *, title: str, description: str = "", reason: str = "",
                category: str = "general", target_date: str | None = None) -> int:
    now = _now_iso()
    cur = conn.execute(
        "INSERT INTO goals (title, description, reason, category, status, target_date, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 'active', ?, ?, ?)",
        (title, description, reason, category, target_date, now, now),
    )
    return cur.lastrowid


def get_goal(conn: Connection, goal_id: int) -> dict | None:
    return _row(conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone())


def delete_goal(conn: Connection, goal_id: int) -> bool:
    cur = conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    conn.commit()
    return cur.rowcount > 0


def list_goals(conn: Connection, category: str | None = None, status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM goals"
    conds, args = [], []
    if category:
        conds.append("category = ?"); args.append(category)
    if status:
        conds.append("status = ?"); args.append(status)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id DESC"
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def active_goals(conn: Connection) -> list[dict]:
    return list_goals(conn, status="active")


def update_goal(conn: Connection, goal_id: int, **fields) -> dict | None:
    allowed = {"title", "description", "category", "status", "target_date"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_goal(conn, goal_id)
    updates["updated_at"] = _now_iso()
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE goals SET {sets} WHERE id = ?", (*updates.values(), goal_id))
    return get_goal(conn, goal_id)


def goal_progress(conn: Connection, goal_id: int) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done FROM tasks WHERE goal_id = ?",
        (goal_id,),
    ).fetchone()
    total = row["total"] or 0
    done = row["done"] or 0
    return {"done_tasks": done, "total_tasks": total}


# ---------- tasks ----------

def insert_task(conn: Connection, *, goal_id: int, title: str, item_type: str = "task",
                planned_date: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO tasks (goal_id, title, item_type, status, planned_date, created_at) VALUES (?, ?, ?, 'todo', ?, ?)",
        (goal_id, title, item_type, planned_date, _now_iso()),
    )
    return cur.lastrowid


def list_tasks(conn: Connection, goal_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM tasks WHERE goal_id = ? ORDER BY id", (goal_id,)).fetchall()]


def get_task(conn: Connection, task_id: int) -> dict | None:
    return _row(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())


def update_task(conn: Connection, task_id: int, *, title: str | None = None,
                status: str | None = None) -> dict | None:
    task = get_task(conn, task_id)
    if task is None:
        return None
    if title is not None and title != task["title"]:
        conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (title, task_id))
    if status is not None and status != task["status"]:
        done_at = _now_iso() if status == "done" else None
        conn.execute("UPDATE tasks SET status = ?, done_at = ? WHERE id = ?", (status, done_at, task_id))
    conn.commit()
    return get_task(conn, task_id)


def delete_task(conn: Connection, task_id: int) -> bool:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cur.rowcount > 0


# ---------- events ----------

def insert_event(conn: Connection, *, goal_id: int | None, task_id: int | None, content: str,
                 event_type: str | None, amount: float | None, unit: str | None,
                 source: str, happened_on: str) -> int:
    cur = conn.execute(
        "INSERT INTO events (goal_id, task_id, content, event_type, amount, unit, source, happened_on, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (goal_id, task_id, content, event_type, amount, unit, source, happened_on, _now_iso()),
    )
    return cur.lastrowid


def has_event_on(conn: Connection, day: str) -> bool:
    row = conn.execute("SELECT 1 FROM events WHERE happened_on = ? LIMIT 1", (day,)).fetchone()
    return row is not None


def events_between(conn: Connection, start: str, end: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT e.*, g.title AS goal_title FROM events e LEFT JOIN goals g ON e.goal_id = g.id "
        "WHERE e.happened_on BETWEEN ? AND ? ORDER BY e.happened_on DESC, e.id DESC",
        (start, end)).fetchall()]


def days_since_last_event(conn: Connection, today: str) -> int | None:
    """距最近一次打卡的天数；无任何记录返回 None。"""
    row = conn.execute("SELECT MAX(happened_on) AS last FROM events").fetchone()
    if not row or not row["last"]:
        return None
    from datetime import date
    last = date.fromisoformat(row["last"])
    return (date.fromisoformat(today) - last).days


def recent_events(conn: Connection, limit: int = 20) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT e.*, g.title AS goal_title FROM events e LEFT JOIN goals g ON e.goal_id = g.id "
        "ORDER BY e.happened_on DESC, e.id DESC LIMIT ?", (limit,)).fetchall()]


def event_type_breakdown(conn: Connection, start: str | None = None, end: str | None = None) -> list[dict]:
    sql = "SELECT event_type, COUNT(*) AS count FROM events"
    conds, args = [], []
    if start:
        conds.append("happened_on >= ?"); args.append(start)
    if end:
        conds.append("happened_on <= ?"); args.append(end)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " GROUP BY event_type ORDER BY count DESC"
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def distinct_days_between(conn: Connection, start: str, end: str) -> int:
    row = conn.execute(
        "SELECT COUNT(DISTINCT happened_on) AS n FROM events WHERE happened_on BETWEEN ? AND ?",
        (start, end)).fetchone()
    return row["n"] or 0


def count_events_between(conn: Connection, start: str, end: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE happened_on BETWEEN ? AND ?", (start, end)).fetchone()
    return row["n"] or 0


def count_events(conn: Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()
    return row["n"] or 0


# ---------- schedules ----------

def insert_schedule(conn: Connection, *, title: str, start_at: str, end_at: str | None = None,
                    note: str = '', duration_min: int = 30,
                    goal_id: int | None = None, task_id: int | None = None,
                    remind_at: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO schedules (title, start_at, end_at, note, duration_min, goal_id, task_id, remind_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (title, start_at, end_at, note, duration_min, goal_id, task_id, remind_at, _now_iso()),
    )
    return cur.lastrowid


def get_schedule(conn: Connection, schedule_id: int) -> dict | None:
    return _row(conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone())


def list_schedules_between(conn: Connection, start: str, end: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM schedules WHERE start_at >= ? AND start_at < ? ORDER BY start_at", (start, end)).fetchall()]


def update_schedule(conn: Connection, schedule_id: int, **fields) -> dict | None:
    allowed = {"title", "start_at", "end_at", "remind_at", "status", "note", "duration_min"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_schedule(conn, schedule_id)
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE schedules SET {sets} WHERE id = ?", (*updates.values(), schedule_id))
    return get_schedule(conn, schedule_id)


def delete_schedule(conn: Connection, schedule_id: int) -> bool:
    cur = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    return cur.rowcount > 0


# ---------- quick templates ----------

def list_templates(conn: Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM quick_templates ORDER BY sort_order, id").fetchall()]


def insert_template(conn: Connection, *, label: str, event_type: str, amount: float | None = None,
                    unit: str | None = None, goal_id: int | None = None, sort_order: int = 0) -> int:
    cur = conn.execute(
        "INSERT INTO quick_templates (label, event_type, amount, unit, goal_id, sort_order, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (label, event_type, amount, unit, goal_id, sort_order, _now_iso()),
    )
    return cur.lastrowid


def delete_template(conn: Connection, template_id: int) -> bool:
    cur = conn.execute("DELETE FROM quick_templates WHERE id = ?", (template_id,))
    return cur.rowcount > 0


# ---------- messages ----------

def insert_message(conn: Connection, *, role: str, content: str, session_id: int = 1) -> int:
    cur = conn.execute("INSERT INTO chat_messages (role, content, session_id, created_at) VALUES (?, ?, ?, ?)",
                       (role, content, session_id, _now_iso()))
    return cur.lastrowid


def recent_messages(conn: Connection, limit: int = 10, session_id: int = 1) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM (SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id",
        (session_id, limit)).fetchall()
    return [dict(r) for r in rows]


def list_messages(conn: Connection, limit: int = 50, session_id: int = 1,
                  before_id: int | None = None) -> list[dict]:
    """获取会话消息，before_id 用于分页加载更早的消息。"""
    if before_id:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM chat_messages WHERE session_id = ? AND id < ? ORDER BY id DESC LIMIT ?) ORDER BY id",
            (session_id, before_id, limit)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id",
            (session_id, limit)).fetchall()
    return [dict(r) for r in rows]


def list_sessions(conn: Connection, limit: int = 500) -> list[dict]:
    """获取所有会话列表（按最新消息时间倒序），标题优先用用户自定义，否则取第一条用户消息前 20 字。"""
    rows = conn.execute("""
        SELECT s.id, s.title, s.created_at,
               (SELECT content FROM chat_messages WHERE session_id = s.id AND role = 'user' ORDER BY id LIMIT 1) as first_user_msg,
               (SELECT content FROM chat_messages WHERE session_id = s.id ORDER BY id DESC LIMIT 1) as last_message,
               (SELECT COUNT(*) FROM chat_messages WHERE session_id = s.id) as msg_count
        FROM chat_sessions s
        ORDER BY s.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # 优先用用户自定义标题，否则用第一条用户消息
        if not d.get('title'):
            first_msg = d.get('first_user_msg') or ''
            d['title'] = first_msg[:20] if first_msg else '新对话'
        result.append(d)
    return result


def update_session_title(conn: Connection, session_id: int, title: str) -> None:
    """更新会话标题。"""
    conn.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (title, session_id))


def delete_session(conn: Connection, session_id: int) -> None:
    """删除会话及其所有消息。"""
    conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))


def create_session(conn: Connection) -> int:
    """创建新会话，返回 session_id。"""
    now = _now_iso()
    cur = conn.execute("INSERT INTO chat_sessions (created_at) VALUES (?)", (now,))
    return cur.lastrowid


# ---------- reviews ----------

def insert_review(conn: Connection, *, period_type: str, period_start: str, period_end: str,
                  content: str, stats: dict) -> int:
    cur = conn.execute(
        "INSERT INTO reviews (period_type, period_start, period_end, content, stats_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (period_type, period_start, period_end, content, json.dumps(stats, ensure_ascii=False), _now_iso()),
    )
    return cur.lastrowid


def list_reviews(conn: Connection, period_type: str = "weekly", limit: int = 10) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM reviews WHERE period_type = ? ORDER BY period_start DESC LIMIT ?",
        (period_type, limit)).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["stats"] = json.loads(item.pop("stats_json") or "{}")
        out.append(item)
    return out


def review_exists(conn: Connection, period_type: str, period_start: str, period_end: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM reviews WHERE period_type=? AND period_start=? AND period_end=? LIMIT 1",
        (period_type, period_start, period_end)).fetchone()
    return row is not None


# ---------- profile / app_state ----------

def profile_get(conn: Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM profile WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def profile_set(conn: Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO profile (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, _now_iso()))


def state_get(conn: Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def state_set(conn: Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_state (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, _now_iso()))
