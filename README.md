# 个人成长管理助手（Personal Agent）

以「长期记忆 + 心理学方法」为核心的桌面端个人成长管理助手。对话即记录，AI 帮你完成目标、学习计划、日程、健康习惯的沉淀与复盘，并用宽容机制对抗记录疲劳。

> 设计文档索引见 [docs/README.md](docs/README.md)。

## 功能

| 模块 | 说明 |
| --- | --- |
| 对话打卡 | 自然语言记录「今天读了 30 页书」，自动归属目标并更新任务 |
| 目标 / 学习计划 | AI 拆解目标为课程/书籍/实践子任务，学习计划复用同一底座 |
| 日程 | 手动或对话创建日程，周视图管理完成/取消 |
| 心理学管理 | 执行意图、微小习惯、习惯回路、自我慈悲、成长型思维、自我决定；只做自我管理辅助，不诊断、不替代专业咨询 |
| 防疲劳机制 | 每晚 21:00 主动问询、宽容统计（本周 X/7 天）、中断 3 天温和重启、快捷模板、允许补记、低密度模式 |
| 周复盘 | 每周日 20:00 自动生成，可手动触发 |
| 看板 | 今日记录 / 周打卡 / 目标进度 / 记录类型分布 / 最近记录 |

## 目录结构

```text
personal_agent/
├─ backend/          FastAPI 后端（数据层 + Agent 核心 + API）
│  ├─ app/
│  ├─ tests/         24 个 pytest 用例
│  └─ .env.example   环境配置模板
├─ frontend/         Vue3 + Vite + Element Plus 前端
├─ desktop/          Electron 桌面壳（窗口/托盘/启动器）
└─ docs/             需求 / 设计 / 方案 / 修改记录
```

## 快速启动

### 前置要求

- Python 3.11+
- Node.js 18+

### 一键启动（桌面端）

```powershell
# 1. 首次：安装依赖
cd backend; python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt
cd ..\frontend; npm install; npm run build
cd ..\desktop; npm install

# 2. 配置 LLM（backend\.env，参照 .env.example）
#    OPENAI_API_KEY=你的密钥

# 3. 启动
cd ..\desktop; npm start
```

`desktop\scripts\start.js` 会自动拉起后端（127.0.0.1:8000）再打开桌面窗口，关闭窗口后驻留托盘。

### 开发模式（前后端分离）

```powershell
cd backend; .\.venv\Scripts\python -m uvicorn app.main:app --port 8000   # 终端 1
cd frontend; npm run dev                                                 # 终端 2，http://127.0.0.1:5173
```

### 测试

```powershell
cd backend; .\.venv\Scripts\python -m pytest tests -q
```

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

## 数据与隐私

- 单用户本地部署：SQLite 单文件存储，数据默认在 `backend/data/`，不上传任何第三方。
- 心理学功能定位为自我管理辅助，不提供诊断、治疗或替代专业心理咨询。

## 已知限制（MVP）

- LLM 密钥未配置时，对话/拆解/复盘类功能不可用，其余 CRUD 可用。
- 无账号体系、无多端同步、无数据导入导出（P1 后置）。
