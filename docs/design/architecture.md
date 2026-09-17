# 个人成长管理助手 Agent — 技术设计

- 版本：v0.3
- 日期：2026-09-12
- 关联：`../requirements/requirements.md`（v0.3）

## 1. 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 桌面壳 | Electron（窗口 / 托盘 / 系统通知） | 生态成熟，与 Vue3 栈无缝；Tauri 留作后续瘦身选项 |
| 后端 | Python 3.11 + FastAPI + Uvicorn（localhost 服务） | 异步轻量、生态成熟 |
| Agent 编排 | 轻量编排（LLM 结构化输出 + 业务流程函数 + 心理学策略库） | MVP 流程线性；LangGraph 在状态复杂化后再评估 |
| 存储 | SQLite（标准库 sqlite3 + 轻量封装） | 单用户零运维 |
| LLM | OpenAI 兼容 Chat Completions（base_url / api_key / model 可配） | 兼容豆包、DeepSeek、本地 Ollama |
| 定时任务 | APScheduler：每晚主动问询 + 每周日周复盘 | 进程内调度，零外部依赖 |
| 前端 | Vue3 + Vite + TypeScript + Element Plus | 用户偏好 Vue3，组件库减少样式工作量 |
| 测试 | pytest + httpx + mock LLM | 确定性验证，不依赖真实模型 |

## 2. 模块划分与目录结构

```
personal_agent/
├── desktop/                   # Electron 壳
│   ├── main.js                # 主进程：窗口 / 托盘 / 系统通知
│   ├── preload.js
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口、路由注册、调度器启动
│   │   ├── config.py          # 配置加载（.env）
│   │   ├── api/               # 表现层
│   │   │   ├── chat.py        # 对话 / 打卡 / 补记
│   │   │   ├── goals.py       # 目标、学习计划、子任务
│   │   │   ├── schedules.py   # 日程管理
│   │   │   ├── templates.py   # 快捷模板
│   │   │   ├── checkin.py     # 主动问询状态
│   │   │   ├── reviews.py     # 复盘
│   │   │   └── stats.py       # 看板统计
│   │   ├── core/              # 领域核心逻辑
│   │   │   ├── agent.py       # Agent 编排主流程
│   │   │   ├── extractor.py   # LLM 意图识别与结构化抽取
│   │   │   ├── planner.py     # 目标 / 学习计划拆解
│   │   │   ├── reviewer.py    # 周复盘生成（含心理维度）
│   │   │   ├── psychology.py  # 心理学策略库（习惯引擎/中断干预/反馈）
│   │   │   └── prompts.py     # Prompt 模板与输出 schema
│   │   ├── services/          # 应用层
│   │   │   ├── chat_service.py
│   │   │   └── checkin_service.py
│   │   ├── db/                # 基础设施
│   │   │   ├── database.py
│   │   │   └── repos.py
│   │   └── schemas/           # Pydantic 模型
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Vue3 单页应用
│   ├── src/
│   │   ├── views/             # ChatView / GoalsView / SchedulesView / ReviewsView / DashboardView
│   │   └── api/client.ts
│   ├── vite.config.ts
│   └── package.json
├── docs/                      # 见 docs/README.md 索引
└── README.md
```

分层约定：`api` → `services` → `core`（含心理学策略库）→ `db`；核心逻辑不依赖 FastAPI / sqlite3 具体实现。

## 3. 数据流

### 3.1 对话打卡（主链路）

```
用户消息 → POST /api/chat → chat_service
  1. 取最近 N 轮消息为上下文
  2. LLM#1：意图识别 + 结构化抽取（JSON）
  3. 心理学策略判定：是否命中中断干预 / 目标进度反馈
  4. 业务执行：写 event（含 source）→ 更新 task/goal 进度（事务）
  5. LLM#2：生成反馈（注入档案 + 进度 + 心理学策略）
  6. 消息落库，返回 reply
```

### 3.2 主动问询（记录防疲劳核心）

```
APScheduler 每晚 21:00 → checkin_service 设置 pending 状态
  → 前端轮询 GET /api/checkin/status（每 60s）
  → pending=true 时 Electron 弹系统通知「今天过得怎么样？」
  → 用户回复 → 走 3.1 打卡链路 → 清除 pending
```

### 3.3 周复盘（含心理维度）

```
APScheduler 周日 20:00（或手动）→ 聚合本周事件 + 目标进度
  → psychology.review_framing（过程归因 / 自我慈悲）
  → LLM 生成 Markdown 复盘 → 写 reviews（stats_json 快照）
```

## 4. 外部依赖

- LLM API（必配）：`OPENAI_BASE_URL` / `OPENAI_API_KEY` / `LLM_MODEL`
- Electron（桌面壳）、无数据库服务、无消息中间件

## 5. 异常策略

| 场景 | 处理 |
|---|---|
| LLM 调用失败 | 返回友好错误（502），消息不落库，可重试 |
| LLM 返回非合法 JSON | 重试 1 次，仍失败降级为普通文本回复 |
| 抽取的目标/任务不存在 | 回复澄清追问，不写入事件 |
| 主动问询无回复 | pending 保留至次日，不重复打扰 |
| 补记日期非法（未来日期） | 400 拒绝，提示修正 |
| 周复盘区间无数据 | 生成「本周无记录」复盘，不报错 |

## 6. 部署方式

- 开发：`uvicorn` 后端 + `vite dev` 前端 + `electron .` 壳
- 生产：Electron 打包（backend 内嵌启动），数据存用户目录 `~/.personal_agent/`
- 仅限本机访问，无鉴权（单用户假设 D2）

## 7. 设计取舍记录

| 取舍 | 结论 | 理由 / 回补条件 |
|---|---|---|
| SQLite vs PostgreSQL | SQLite | 单用户零运维；仓储层已隔离，可迁移 |
| Electron vs Tauri | Electron | 生态成熟；包体积问题后续可评估 Tauri |
| 轻量编排 vs LangGraph | 轻量编排 | 主流程线性；状态复杂后引入 |
| 主动问询用轮询 vs WebSocket | 轮询（60s） | MVP 简单可靠；需要实时推送时再升级 |
| 学习计划复用目标底座 | 复用 goals+tasks | 用 category/item_type 区分，不建独立模块 |
| 心理学层独立策略库 | psychology.py | 干预规则可测试、可演进，与 Prompt 解耦 |
