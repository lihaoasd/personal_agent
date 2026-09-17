"""SQLite 连接管理与建表。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  reason      TEXT NOT NULL DEFAULT '',
  category    TEXT NOT NULL DEFAULT 'general',
  status      TEXT NOT NULL DEFAULT 'active',
  abandon_reason TEXT NOT NULL DEFAULT '',
  target_date TEXT,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  goal_id      INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
  title        TEXT NOT NULL,
  item_type    TEXT NOT NULL DEFAULT 'task',
  status       TEXT NOT NULL DEFAULT 'todo',
  planned_date TEXT,
  done_at      TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_goal ON tasks(goal_id);

CREATE TABLE IF NOT EXISTS events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  goal_id     INTEGER REFERENCES goals(id) ON DELETE SET NULL,
  task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  content     TEXT NOT NULL,
  event_type  TEXT,
  amount      REAL,
  unit        TEXT,
  source      TEXT NOT NULL DEFAULT 'chat',
  happened_on TEXT NOT NULL,
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_goal ON events(goal_id);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(happened_on);

CREATE TABLE IF NOT EXISTS schedules (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  start_at    TEXT NOT NULL,
  end_at      TEXT,
  note        TEXT NOT NULL DEFAULT '',
  duration_min INTEGER NOT NULL DEFAULT 30,
  goal_id     INTEGER REFERENCES goals(id) ON DELETE SET NULL,
  task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  remind_at   TEXT,
  status      TEXT NOT NULL DEFAULT 'upcoming',
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_schedules_start ON schedules(start_at);

CREATE TABLE IF NOT EXISTS quick_templates (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  label      TEXT NOT NULL,
  event_type TEXT NOT NULL,
  amount     REAL,
  unit       TEXT,
  goal_id    INTEGER REFERENCES goals(id) ON DELETE SET NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  role       TEXT NOT NULL,
  content    TEXT NOT NULL,
  session_id INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  title      TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  title        TEXT NOT NULL DEFAULT '',
  period_type  TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end   TEXT NOT NULL,
  content      TEXT NOT NULL,
  stats_json   TEXT,
  created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_state (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- 日记
CREATE TABLE IF NOT EXISTS diaries (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  diary_date  TEXT NOT NULL,
  title       TEXT NOT NULL DEFAULT '',
  content     TEXT NOT NULL DEFAULT '',
  mood        TEXT NOT NULL DEFAULT '',
  tags        TEXT NOT NULL DEFAULT '',
  goal_id     INTEGER REFERENCES goals(id) ON DELETE SET NULL,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_diaries_date ON diaries(diary_date);

-- Agent Loop 执行 trace
CREATE TABLE IF NOT EXISTS agent_traces (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   INTEGER NOT NULL,
  user_message TEXT NOT NULL,
  step         INTEGER NOT NULL,
  role         TEXT NOT NULL,
  content      TEXT NOT NULL,
  tool_name    TEXT NOT NULL DEFAULT '',
  tool_args    TEXT NOT NULL DEFAULT '',
  tool_result  TEXT NOT NULL DEFAULT '',
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_traces_session ON agent_traces(session_id, created_at);
"""


def connect(db_path: str) -> sqlite3.Connection:
    """打开连接并启用外键与行映射。

    check_same_thread=False：FastAPI 的同步依赖/端点在线程池中运行，同一请求的
    连接创建与使用可能落在不同工作线程；每个请求持有独立连接、无并发共享，因此安全。
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # 迁移：旧库补 reason 列
    cols = [r[1] for r in conn.execute("PRAGMA table_info(goals)").fetchall()]
    if "reason" not in cols:
        conn.execute("ALTER TABLE goals ADD COLUMN reason TEXT NOT NULL DEFAULT ''")
    # 迁移：chat_messages 加 session_id
    msg_cols = [r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()]
    if "session_id" not in msg_cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN session_id INTEGER NOT NULL DEFAULT 1")
    # 迁移：chat_sessions 加 title
    sess_cols = [r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()]
    if "title" not in sess_cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN title TEXT NOT NULL DEFAULT ''")
    # 迁移：schedules 加 note 和 duration_min
    sched_cols = [r[1] for r in conn.execute("PRAGMA table_info(schedules)").fetchall()]
    if "note" not in sched_cols:
        conn.execute("ALTER TABLE schedules ADD COLUMN note TEXT NOT NULL DEFAULT ''")
    if "duration_min" not in sched_cols:
        conn.execute("ALTER TABLE schedules ADD COLUMN duration_min INTEGER NOT NULL DEFAULT 30")
    # 迁移：goals 加 abandon_reason
    goal_cols = [r[1] for r in conn.execute("PRAGMA table_info(goals)").fetchall()]
    if "abandon_reason" not in goal_cols:
        conn.execute("ALTER TABLE goals ADD COLUMN abandon_reason TEXT NOT NULL DEFAULT ''")
    # 迁移：reviews 加 title
    review_cols = [r[1] for r in conn.execute("PRAGMA table_info(reviews)").fetchall()]
    if "title" not in review_cols:
        conn.execute("ALTER TABLE reviews ADD COLUMN title TEXT NOT NULL DEFAULT ''")
    conn.commit()
