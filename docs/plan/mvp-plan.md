# 个人成长管理助手 Agent — MVP 开发方案

- 版本：v0.3
- 日期：2026-09-12
- 前置：需求 v0.3 与设计 v0.3 评审通过
- 范围：MVP（P0，含记录防疲劳机制），不实现 P1 与「暂不做」项

## 1. 改动范围

- 新建 `desktop/`：Electron 壳（窗口 / 托盘 / 系统通知）
- 新建 `backend/`：FastAPI 应用（api / services / core / db / schemas）+ 测试
- 新建 `frontend/`：Vue3 + Vite + Element Plus（5 个视图：Chat / Goals / Schedules / Reviews / Dashboard）
- 根 `README.md`（一键启动）
- 设计文档与修改记录存放 `docs/`（已同步 v0.3）

## 2. 实现顺序（纵向切片）

| 阶段 | 内容 | 验证方式 |
|---|---|---|
| 0 | 项目骨架：backend hello + frontend 脚手架 + Electron 壳 | 三端可启动；Electron 能加载前端 |
| 1 | 数据层：全部表结构 + repos + 迁移 | pytest 通过（含 schedules/templates/app_state） |
| 2 | Agent 核心：extractor（新意图）+ psychology 策略库 | 单测覆盖 打卡/模板/补记/日程/中断干预 分支 |
| 3 | 对话链路：`POST /api/chat` + ChatView | 端到端打卡：事件落库 → 进度更新 → 即时反馈 |
| 4 | 目标与学习计划：category/item_type + GoalsView | 接口单测 + 页面走查 |
| 5 | 日程管理：schedules CRUD + SchedulesView（日历视图） | 接口单测 + 页面走查 |
| 6 | 快捷模板 + 补记：templates API + 补记链路 | 端到端：一键打卡 / 补记昨日 |
| 7 | 主动问询：APScheduler + checkin API + Electron 通知 + 前端轮询 | 定时触发后通知出现，回复后 pending 清除 |
| 8 | 周复盘（含心理维度）+ ReviewsView | 生成复盘落库；空数据不报错 |
| 9 | 看板（宽容统计）+ DashboardView | 统计数字与表重算一致 |
| 10 | 收尾：README、修改记录、全量 pytest | 全新环境按 README 可启动；测试全绿 |

每阶段结束跑该阶段测试与手动走查；全部完成后全量测试 + 端到端验收。

## 3. 关键伪代码

### 3.1 extractor — 意图识别与抽取

```
function extract_intent(messages, active_goals, templates):
    prompt = build_extract_prompt(messages, active_goals, templates)
    raw = llm_chat(prompt, response_format="json")
    parsed = parse_json(raw)          # 失败重试 1 次
    validate: intent ∈ 枚举; backfill 时 happened_on 必填且非未来
    return parsed   # {intent, goal_id, task_id, event, happened_on, need_clarify}
```

### 3.2 agent — 打卡编排（含心理学）

```
function handle_chat(message):
    history = repo.recent_messages(10)
    parsed = extract_intent(history + [message], repo.active_goals(), repo.templates())
    tone = psychology.decide_tone(parsed, repo)   # 中断检测/进度/里程碑
    case parsed.intent:
      checkin|template|backfill:
        if goal_id 不存在: return clarify(parsed.need_clarify)
        with tx():
            repo.insert_event(goal_id, task_id, message, event, source, happened_on)
            if task 完成: mark_task_done(task); update_goal_progress()
        reply = generate_reply(profile, progress, tone)
      goal_manage: goal_service 操作
      schedule: schedule_service 操作
      query: stats 查询 → 回答
      chat: 仅对话
    repo.insert_message("user", message); repo.insert_message("assistant", reply)
    return reply
```

### 3.3 psychology — 策略判定

```
function decide_tone(parsed, repo):
    days_since = repo.days_since_last_event()
    if days_since >= 3:  return "gentle_restart"   # 温和重启
    if parsed.intent in (checkin, template):
        return "positive_feedback"
    return "neutral"

function review_framing(stats):
    # 过程归因：归因于努力与可控因素，不贴标签；记录少时提示低密度说明
```

### 3.4 checkin — 主动问询

```
function nightly_checkin():
    if repo.has_event_today(): return            # 今日已记录，不打扰
    app_state.set("checkin_pending", "1", date=today)

function get_checkin_status():
    return { pending, today_done, last_ask_date, week_days }
```

### 3.5 reviewer — 周复盘

```
function generate_review(period):
    events = repo.events_between(period)
    goals  = repo.goals_with_progress()
    stats  = aggregate(events, goals)
    frame  = psychology.review_framing(stats)
    content = llm_chat(build_review_prompt(stats, frame))
    repo.insert_review("weekly", period, content, stats)
```

## 4. 测试策略

- 单元测试：mock LLM 固定 JSON，覆盖 extractor 各意图、agent 各分支、psychology 各策略触发、reviewer 空/正常数据
- 仓储测试：内存 SQLite，验证全表 CRUD、级联删除、未来日期校验
- 集成测试：TestClient 走 `/api/chat`、`/api/checkin/*`、`/api/schedules`，验证落库与状态流转
- 边界用例：无关联目标打卡、数量缺失、目标已完成、中断 3 天干预、补记未来日期拒绝、周复盘无数据、LLM 非法 JSON

## 5. 验收清单

- [ ] 阶段 0~10 全部完成且测试通过
- [ ] 端到端走查：定目标 → 拆学习计划 → 排日程 → 每日打卡/模板/补记 → 主动问询 → 周复盘 → 看板（宽容统计）数据一致
- [ ] 中断 3 天后的回复话术无指责、含重启建议
- [ ] `pytest` 全绿；`npm run build` 通过；Electron 打包可运行
- [ ] README 一键启动可用；修改记录与本次改动一一对应
