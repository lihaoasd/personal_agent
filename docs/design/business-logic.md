# 个人成长管理助手 Agent — 业务逻辑设计

- 版本：v0.3
- 日期：2026-09-12
- 说明：覆盖主流程、心理学策略、状态流转、边界条件与一致性

## 1. 对话打卡主流程（含心理学策略）

```
用户消息（对话 / 快捷打卡 / 补记）
  ↓
1. 取最近 10 轮 chat_messages 作为上下文
  ↓
2. LLM#1 结构化输出：
   {
     "intent": "checkin | template | backfill | goal_manage | schedule | query | chat",
     "goal_id", "task_id",
     "event": { "event_type", "amount", "unit" },
     "happened_on": "YYYY-MM-DD" | null,   -- backfill 时必填
     "need_clarify": "..." | null
   }
  ↓
3. 心理学策略判定（psychology.py）：
   - 中断检测：最近事件距今 ≥ 3 天 → 启用「温和重启」话术
   - 目标进度：读取相关目标进度 → 决定反馈基调（进度好：鼓励+肯定；停滞：共情+建议）
   - 习惯引擎：event_type 命中习惯 → 累计 N 次给里程碑反馈
  ↓
4. 分支执行（单事务）：
   ├─ checkin / template / backfill → 写 event（source 对应）→ 关联 task 完成则更新进度
   ├─ goal_manage → 目标 / 学习计划操作
   ├─ schedule → 日程创建 / 调整（复用 LLM 抽取的时间字段）
   └─ query → 查库生成回答
  ↓
5. LLM#2 生成回复（注入：档案 + 相关进度 + 心理学策略基调）
  ↓
6. 用户消息 + 助手回复落库，返回 reply
```

### 状态流转

- `tasks.status`：`todo → doing → done`（回退允许，同步清空 `done_at`）
- `goals.status`：`active ↔ paused`；`active → done / abandoned`（终态）
- `schedules.status`：`upcoming → done / cancelled`

## 2. 心理学策略库（psychology.py）

| 策略 | 触发条件 | 行为 |
|---|---|---|
| 温和重启 | 最近事件距今 ≥ 3 天 | 反馈话术：共情 → 不指责 → 给最小重启动作（如 2 分钟法则） |
| 即时正反馈 | 每次打卡 | 回复含进度、鼓励；不用惩罚性语言 |
| 里程碑反馈 | 同一 event_type 累计达 7/30 次 | 生成里程碑回顾与肯定 |
| 难度自适应 | 目标任务连续 3 次未完成 | 提示调整目标粒度或延期，不施压 |
| 过程归因 | 周复盘生成 | 归因于过程与可控因素，避免自我标签 |
| 执行意图提醒 | 目标含 If-Then 计划 | 到计划时间附近（±30 分钟）生成提醒文案 |

## 3. 主动问询流程（防疲劳核心）

```
APScheduler 每晚 21:00（profile.checkin_time 可配）
  → 若今日已有记录（events.happened_on = today）：不打扰，跳过
  → 否则 app_state.checkin_pending = "1"（last_ask_date = today）
  → 前端轮询 GET /api/checkin/status（60s）
  → pending=true → Electron 系统通知「今天过得怎么样？」→ 点击聚焦聊天页
  → 用户回复 → 走打卡链路 → checkin_pending = "0"
  → 用户忽略：pending 保留至次日，不重复弹通知
```

## 4. 快捷模板与补记

- 快捷打卡：前端调用模板 → `POST /api/chat`（intent=template）或直接写事件（source=template），即时反馈不变
- 补记：识别消息中的时间表述（"昨天/前天/上周三"）或显式 `POST /api/checkin/backfill`；**happened_on 不允许未来日期**（400）
- 补记同样计入周统计与复盘

## 5. 周复盘流程（含心理维度）

```
触发：APScheduler 周日 20:00，或手动 POST /api/reviews/generate
  → period = 上周一 ~ 上周日
  → 聚合：各目标事件数、完成任务数、周打卡天数、事件类型分布
  → psychology.process_attribution + 低密度处理（记录少时说明「本周记录较少」）
  → LLM 生成 Markdown 复盘：
      ## 本周概览 / ## 完成情况 / ## 中断与原因 / ## 心理洞察（过程归因） / ## 下周建议
  → 写 reviews（content + stats_json 快照）
```

## 6. 边界条件

| 场景 | 行为 |
|---|---|
| 同一目标同日重复打卡 | 允许多条事件，不合并 |
| 打卡未提供数量 | 只记事件（amount 为空） |
| 目标已 done 仍打卡 | 正常记录，提示目标已完成、询问是否新目标 |
| 主动问询时用户回复无关内容 | 按意图正常分流，不强制记录 |
| 补记未来日期 | 400 拒绝 |
| 日程时间冲突 | 允许并存（单用户工具不强制互斥），日历视图可见 |
| 一周无事件 | 复盘为「本周无记录」，不报错 |

## 7. 一致性处理

- 打卡写库为单事务：event 与 task 状态更新同成功同回滚
- 复盘 stats_json 与 reviews 同时写入，可复现可比对
- 主动问询 pending 与消息落库无强耦合：记录完成即清 pending，失败可重试
- 所有时间以服务端本地时区（Asia/Shanghai）为准
