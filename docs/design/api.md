# 个人成长管理助手 Agent — 接口设计

- 版本：v0.3
- 日期：2026-09-12
- Base：`/api`；统一 JSON；错误码见 §3

## 1. 接口列表

### 1.1 对话 / 打卡 / 补记

**POST `/api/chat`**

请求：

```json
{ "message": "今天读完《系统设计》第 3 章，背了 20 个单词" }
```

响应：

```json
{
  "reply": "已记录：读完系统设计第 3 章、背单词 20 个。目标『9 月完成系统设计学习』进度 3/5，按当前节奏预计提前 2 周完成。",
  "message_id": 128,
  "created_event_ids": [12, 13]
}
```

行为：意图识别（打卡 / 目标 / 学习计划 / 日程 / 快捷打卡 / 补记 / 查询 / 闲聊）→ 心理学策略判定 → 业务执行 → 反馈生成。补记通过消息中时间表述识别（如"昨天读了 20 页"→ `happened_on=昨天`）。

**POST `/api/checkin/backfill`** — 显式补记：

```json
{ "content": "读了 20 页", "happened_on": "2026-09-11", "goal_id": 1 }
```

### 1.2 目标与学习计划

**GET `/api/goals?category=learning`** → 目标列表（含进度与子任务）：

```json
[
  {
    "id": 1, "title": "9 月完成系统设计学习", "category": "learning",
    "status": "active", "target_date": "2026-09-30",
    "progress": { "done_tasks": 3, "total_tasks": 5 },
    "tasks": [ { "id": 11, "title": "读完第 3 章", "item_type": "book", "status": "done" } ]
  }
]
```

**POST `/api/goals`** — 请求：`{ "title", "category"?, "description"?, "target_date"? }`，响应：目标对象

**PATCH `/api/goals/{id}`** — 请求：`{ "status" | "title" | "category" | "description" | "target_date" }`

**POST `/api/goals/{id}/tasks`** — 请求：`{ "title", "item_type"?, "planned_date"? }`

**PATCH `/api/tasks/{id}`** — 请求：`{ "status": "done" | "todo" | "doing" }`

### 1.3 日程管理

**GET `/api/schedules?start=2026-09-14&end=2026-09-20`** → 区间日程列表（日历视图数据）

**POST `/api/schedules`** — 请求：`{ "title", "start_at", "end_at"?, "goal_id"?, "task_id"?, "remind_at"? }`

**PATCH `/api/schedules/{id}`** — 请求：`{ "status" | "title" | "start_at" | "end_at" | "remind_at" }`

### 1.4 快捷模板

**GET `/api/templates`** → 模板列表；**POST `/api/templates`**（`{ "label", "event_type", "amount"?, "unit"?, "goal_id"? }`）；**DELETE `/api/templates/{id}`**

### 1.5 主动问询（防疲劳）

**GET `/api/checkin/status`** → 响应：

```json
{ "pending": true, "today_done": false, "last_ask_date": "2026-09-12", "week_days": 5 }
```

**POST `/api/checkin/dismiss`** — 标记本次问询已处理（不记录业务数据）

### 1.6 复盘

**GET `/api/reviews?period_type=weekly&limit=10`**；**POST `/api/reviews/generate`**（手动触发）

### 1.7 看板统计（宽容口径）

**GET `/api/stats/dashboard`** — 响应：

```json
{
  "today_checkins": 2,
  "week_days": 5,
  "week_checkin_rate": 0.71,
  "goal_progress": [ { "goal_id": 1, "title": "...", "category": "learning", "done_tasks": 3, "total_tasks": 5 } ],
  "event_type_breakdown": [ { "event_type": "reading", "count": 8 } ],
  "recent_events": [ { "happened_on": "2026-09-12", "content": "...", "source": "chat", "goal_title": "..." } ]
}
```

> 说明：不提供「连续打卡 N 天」指标（需求 §6 宽容机制）；如需趋势用周粒度。

### 1.8 对话历史

**GET `/api/messages?limit=50`**

### 1.9 模型配置（v0.4 新增）

**GET `/api/settings/model`** — 读取当前模型配置（Key 脱敏）

```json
{ "base_url": "https://...", "api_key_set": true, "api_key_masked": "sk****78", "model": "doubao-pro-32k", "provider_ready": true }
```

**POST `/api/settings/model`** — 保存并立即热更新提供商（无需重启）

- body：`{ "base_url"?, "api_key"?, "model"? }`
- 校验：base_url 与 model 必填（否则 400）
- `api_key` 为空时**保留已存值**（仅可增改，不可经此清空）
- 存储：数据库 `app_state` 表（键 `llm_base_url` / `llm_api_key` / `llm_model`），优先级高于 `.env`
- 保存后调用 `llm.set_provider` 热切换；无 key 时置空（对话返回可读错误）

**POST `/api/settings/model/test`** — 用当前提供商做一次最小调用

- 成功：`{ "ok": true, "latency_ms": 123, "reply": "..." }`
- 失败：`{ "ok": false, "error": "..." }`（HTTP 200，前端展示）

## 2. 心理学相关行为约定

- **中断干预**：最近事件距今 ≥ 3 天时，`/api/chat` 回复附带温和重启话术（由 psychology 策略库判定）
- **即时正反馈**：每次打卡回复包含进度与鼓励（非惩罚性语言）
- 以上行为内嵌于回复文本，接口结构不变

## 3. 错误码

| 状态码 | 含义 | 说明 |
|---|---|---|
| 400 | 参数错误 | 必填缺失 / 非法枚举 / 未来日期补记 |
| 404 | 资源不存在 | goal / task / schedule / template 不存在 |
| 502 | LLM 不可用 | 调用失败或超时，可重试 |
| 500 | 服务异常 | 数据库等内部错误 |

统一错误体：`{ "detail": "人类可读信息" }`
