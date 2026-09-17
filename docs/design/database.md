# 个人成长管理助手 Agent — 数据库设计

- 版本：v0.3
- 日期：2026-09-12
- 存储：SQLite 单文件；所有时间存 ISO 8601 字符串（时区 Asia/Shanghai）

## 1. 表结构

```sql
-- 目标（含学习计划目标，用 category 区分）
CREATE TABLE goals (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  category    TEXT NOT NULL DEFAULT 'general',  -- general | learning | health | habit
  status      TEXT NOT NULL DEFAULT 'active',   -- active | paused | done | abandoned
  target_date TEXT,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

-- 子任务（学习计划步骤用 item_type 区分 课程/书籍/实践）
CREATE TABLE tasks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  goal_id      INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
  title        TEXT NOT NULL,
  item_type    TEXT NOT NULL DEFAULT 'task',    -- task | course | book | practice
  status       TEXT NOT NULL DEFAULT 'todo',    -- todo | doing | done
  planned_date TEXT,
  done_at      TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX idx_tasks_goal ON tasks(goal_id);

-- 打卡事件（统一记录层：阅读/健康/习惯/学习，用 event_type 区分）
CREATE TABLE events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  goal_id     INTEGER REFERENCES goals(id) ON DELETE SET NULL,
  task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  content     TEXT NOT NULL,                    -- 用户原文 / 模板文案
  event_type  TEXT,                             -- reading | exercise | sleep | study | habit | ...
  amount      REAL,
  unit        TEXT,
  source      TEXT NOT NULL DEFAULT 'chat',     -- chat | template | backfill | auto(P1)
  happened_on TEXT NOT NULL,                    -- YYYY-MM-DD（补记用过去日期）
  created_at  TEXT NOT NULL
);
CREATE INDEX idx_events_goal ON events(goal_id);
CREATE INDEX idx_events_date ON events(happened_on);

-- 日程管理
CREATE TABLE schedules (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  start_at    TEXT NOT NULL,
  end_at      TEXT,
  goal_id     INTEGER REFERENCES goals(id) ON DELETE SET NULL,
  task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  remind_at   TEXT,
  status      TEXT NOT NULL DEFAULT 'upcoming', -- upcoming | done | cancelled
  created_at  TEXT NOT NULL
);
CREATE INDEX idx_schedules_start ON schedules(start_at);

-- 快捷模板（防疲劳：一键打卡）
CREATE TABLE quick_templates (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  label      TEXT NOT NULL,                     -- 如「读书 30 页」
  event_type TEXT NOT NULL,
  amount     REAL,
  unit       TEXT,
  goal_id    INTEGER REFERENCES goals(id) ON DELETE SET NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

-- 对话消息（短期对话历史）
CREATE TABLE chat_messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  role       TEXT NOT NULL,
  content    TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- 复盘（含心理维度）
CREATE TABLE reviews (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  period_type  TEXT NOT NULL,                   -- weekly | monthly
  period_start TEXT NOT NULL,
  period_end   TEXT NOT NULL,
  content      TEXT NOT NULL,                   -- Markdown 复盘正文
  stats_json   TEXT,                            -- 生成时统计快照
  created_at   TEXT NOT NULL
);

-- 用户档案（长期记忆基础）+ 应用状态（主动问询标记）
CREATE TABLE profile (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
-- profile 键约定：checkin_time（问询时间）、low_density（低密度模式 0/1）、last_ask_date、active_goal_ids 等

CREATE TABLE app_state (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
-- app_state 键约定：checkin_pending = "1"/"0"
```

## 2. 字段口径与约束

- `goals.category`：general / learning / health / habit；学习计划即 `category=learning` 的目标
- `tasks.item_type`：task / course / book / practice；学习计划拆解时按类型生成
- `events.source`：chat（对话）/ template（快捷打卡）/ backfill（补记）；P1 增加 auto
- `events.happened_on` 允许过去日期（补记）；不允许未来日期（接口层校验）
- `schedules.status`：upcoming / done / cancelled；remind_at 为空则无提醒
- 宽容统计口径：看板与统计**使用「本周 X/7 天」，不使用「连续 N 天」**，中断不惩罚（需求 §6）
- 删除目标：级联删子任务，事件与日程置空关联（保留历史）

## 3. 关键查询

- 目标进度：`COUNT(tasks where done) / COUNT(tasks)`，按 goal 聚合
- 周打卡率：`COUNT(DISTINCT happened_on WHERE 本周) / 7`
- 中断判定：最近一次事件距今天数 ≥ 3 → 触发温和重启话术
- 主动问询：读 `app_state.checkin_pending`；今日已完成记录则不再问
- 周复盘输入：`events WHERE happened_on BETWEEN 上周一 AND 上周日` + goals 进度
