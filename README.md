# 个人成长管理助手（Personal Agent）

以「长期记忆 + 心理学方法 + Agent Loop」为核心的桌面端个人成长管理助手。对话即记录，AI 帮你完成目标、学习计划、日程、健康习惯的沉淀与复盘，并用宽容机制对抗记录疲劳。

> 设计文档索引见 [docs/README.md](docs/README.md)。

## 功能

| 模块 | 说明 |
| --- | --- |
| **对话打卡（双模式）** | 自然语言记录「今天读了 30 页书」，自动归属目标并更新任务<br>支持**简单模式**（快速回复）和 **Agent Loop 模式**（模型自主调用工具） |
| **Agent Loop 模式** | 13 个工具：查询/创建/修改/删除目标、日程、日记、复盘<br>开启 think 推理模式，思考过程完整记录 |
| **前端强制确认** | 修改/删除操作必须用户在前端点确认按钮，模型无法绕过 |
| **Agent Trace 日志** | 完整记录：用户消息、模型思考、模型回复、工具调用、审批流程 |
| 目标 / 学习计划 | AI 拆解目标为课程/书籍/实践子任务<br>支持初衷、放弃理由、进度追踪 |
| 日程 | 周/月视图，农历节日显示，创建/完成/取消/删除 |
| 日记 | 三种写作模板：自由书写 / 情绪觉察 / 三省吾身<br>引导式分步问答，自动生成 Markdown |
| 周复盘 | 每周日自动生成，Markdown 渲染，可手动触发 |
| 心理学管理 | 执行意图、微小习惯、习惯回路、自我慈悲、成长型思维、自我决定 |
| 防疲劳机制 | 每晚主动问询、宽容统计、中断温和重启、快捷模板、允许补记 |
| 看板 | 今日记录 / 周打卡 / 目标进度 / 心情分布 / 最近记录 |

## 目录结构

```text
personal_agent/
├─ backend/          FastAPI 后端（数据层 + Agent 核心 + API）
│  ├─ app/
│  │  ├─ api/        接口层（chat / settings / diaries / traces）
│  │  ├─ core/       Agent Loop + LLM + Prompts
│  │  └─ db/         SQLite 数据层 + 仓储
│  ├─ tests/         pytest 用例
│  └─ .env.example   环境配置模板
├─ frontend/         Vue3 + Vite + Element Plus 前端
│  └─ src/
│     ├─ views/       Dashboard / Chat / Goals / Schedules / Reviews / Diaries
│     └─ components/ 组件
├─ desktop/          Electron 桌面壳（窗口/托盘/启动器）
└─ docs/             需求 / 设计 / 方案 / 修改记录
```

## 快速启动

### 前置要求

- Python 3.11+
- Node.js 18+

### 开发模式（前后端分离）

```powershell
# 1. 首次：安装依赖
cd backend; python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt
cd ..\frontend; npm install

# 2. 配置 LLM（backend\.env，参照 .env.example）
#    OPENAI_API_KEY=你的密钥

# 3. 启动
cd ..\backend; .\.venv\Scripts\python -m uvicorn app.main:app --port 8000 --host 127.0.0.1   # 终端 1
cd ..\frontend; npm run dev -- --port 5174                                                # 终端 2
```

访问：http://localhost:5174

### 一键启动（桌面端）

```powershell
cd desktop; npm install; npm start
```

`desktop\scripts\start.js` 会自动拉起后端（127.0.0.1:8000）再打开桌面窗口，关闭窗口后驻留托盘。

## 核心设计

### Agent Loop 工具集（13 个）

| 类型 | 工具 | 说明 |
| --- | --- | --- |
| **查询** | `query_status` | 查询目标/日程/日记/复盘完整信息（含 id） |
| **创建** | `record_checkin` | 记录打卡 |
| | `create_goal` | 创建目标（含初衷） |
| | `create_schedule` | 创建日程 |
| | `create_diary` | 创建日记 |
| | `create_review` | 创建复盘 |
| **修改** | `update_goal` | 修改目标所有字段（标题/理由/状态） |
| | `update_schedule` | 修改日程所有字段（时间/备注/时长） |
| | `update_diary` | 修改日记所有字段（内容/心情/标签） |
| **删除** | `delete_goal` | 删除目标（前端确认） |
| | `delete_schedule` | 删除日程（前端确认） |
| | `delete_diary` | 删除日记（前端确认） |
| | `generate_review` | 生成周复盘 |

### 安全确认机制

```
用户："把减肥目标删了吧"
    ↓
模型调用 delete_goal(goal_id=13)
    ↓
后端：不执行，返回 pending_action
    ↓
前端弹出确认框（ElMessageBox）
    ↓
用户点【确定】 → 调 /chat/execute-action 真正执行
用户点【取消】 → 记录取消到 trace
    ↓
模型生成友好回复
```

### Agent Trace 日志

完整记录每一步：
- 用户消息
- 模型思考（reasoning_content）
- 模型回复
- 工具调用参数 + 返回结果
- 审批发起 + 审批完成/取消

## 环境变量（backend/.env）

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `OPENAI_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | OpenAI 兼容端点（豆包/DeepSeek/Ollama 均可） |
| `OPENAI_API_KEY` | 空 | 未配置时对话类接口返回 502 |
| `LLM_MODEL` | `doubao-pro-32k` | 模型名 |
| `CHECKIN_HOUR` | `21` | 每晚主动问询时间 |
| `REVIEW_HOUR` | `20` | 周日周复盘时间 |
| `PA_DATA_DIR` | `./data` | SQLite 数据目录（未配置时自动初始化） |
| `PA_ENABLE_SCHEDULER` | `1` | 是否启用定时任务（测试置 0） |

## 设计风格

- 萌系奶油风格，薄荷绿主色 `#7bc8a4`
- 圆角卡片，柔和阴影
- 对话 Markdown 渲染
- Element Plus 组件库

## 数据与隐私

- 单用户本地部署：SQLite 单文件存储，数据默认在 `backend/data/`，不上传任何第三方。
- 心理学功能定位为自我管理辅助，不提供诊断、治疗或替代专业心理咨询。

## 已知限制（MVP）

- LLM 密钥未配置时，对话/拆解/复盘类功能不可用，其余 CRUD 可用。
- 无账号体系、无多端同步、无数据导入导出（P1 后置）。
