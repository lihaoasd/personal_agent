# 修改记录

## 2026-09-12 — 设计阶段（从 0 构建）

- 需求/问题：从 0 构建「个人成长管理助手 Agent」，完成设计阶段交付
- 改动范围：新建 `docs/` 目录及 8 份文档（需求 1、设计 4、前端 1、方案 1、索引 1、修改记录）
- 关键文件：
  - `docs/requirements/requirements.md`
  - `docs/design/architecture.md`、`database.md`、`api.md`、`business-logic.md`
  - `docs/frontend/style-guide.md`
  - `docs/plan/mvp-plan.md`
  - `docs/README.md`
- 验证结果：文档内容交叉引用一致（API ↔ 数据库 ↔ 业务逻辑 ↔ 方案）；待用户评审确认 D1–D4 默认假设
- 未完成项：无（设计阶段完成；编码未开始，等待方案评审）

## 2026-09-12 — 需求迭代（v0.1 → v0.2）

- 需求/问题：用户确认桌面端形态，新增「日程管理、阅读笔记、健康记录、心理学管理、学习计划」模块
- 改动范围：重写 `docs/requirements/requirements.md`（v0.2），范围收敛为桌面端 + 7 项 P0 + 心理学横切层
- 关键文件：`docs/requirements/requirements.md`
- 验证结果：心理学位移（6 原则 → 6 功能）与合规边界已写入 §5；D1 已定，D3–D6 待确认
- 未完成项：设计文档（架构/数据库/API/业务/方案）待需求确认后同步修订

## 2026-09-12 — 需求迭代（v0.2 → v0.3）

- 需求/问题：用户提出核心留存问题「记录疲劳」——随时间推移用户不愿再记录
- 改动范围：需求文档新增 §6「记录防疲劳机制」（降成本/提收益/心理机制），P0 新增第 8 项；新增 D7 待确认
- 关键文件：`docs/requirements/requirements.md`
- 验证结果：机制与心理学层（自我慈悲、习惯回路）一致；宽容统计口径写入成功标准
- 未完成项：D3–D7 待确认；设计文档待同步

## 2026-09-12 — 设计同步（v0.3）

- 需求/问题：需求 v0.3 收敛后，全部设计文档同步（桌面端 / 日程 / 学习计划 / 心理学层 / 防疲劳机制）
- 改动范围：重写 `docs/design/architecture.md`、`database.md`、`api.md`、`business-logic.md`、`docs/plan/mvp-plan.md` 至 v0.3
- 关键决策（默认假设，待用户确认）：D2 单用户 / D3 Electron / D5 学习计划通用型 / D6 轻干预 / D7 防疲劳机制进 P0
- 关键文件：`docs/design/*`（5 份）、`docs/plan/mvp-plan.md`
- 验证结果：四份设计与需求 v0.3 交叉引用一致（表结构 ↔ 接口 ↔ 业务 ↔ 方案阶段）；宽容统计口径、中断干预规则、主动问询流程均已落位
- 未完成项：待用户最终评审；通过后进入阶段 0 编码

## 2026-09-13 — 编码阶段（后端 + 前端 + 桌面壳）

- 需求/问题：用户确认「开始编码」，按 mvp-plan 阶段 0–10 落地 v0.3 全部 P0 范围
- 类型: new-feature
- 改动范围：
  - 后端 `backend/`：FastAPI 应用工厂 + APScheduler（每晚 21:00 主动问询 / 周日 20:00 周复盘）、OpenAI 兼容 LLM Provider（可注入 fake）、意图抽取、Agent 编排、目标规划/拆解、周复盘聚合、心理学策略库、8 张表数据层、全部 API、CORS（Electron file:// 跨源）
  - 后端测试 `backend/tests/`：conftest（脚本化 FakeProvider + 临时库）+ 24 个用例（数据层/抽取/Agent/API）
  - 前端 `frontend/`：Vue3 + Vite + Element Plus + vue-router，5 个视图（对话打卡/目标计划/日程/复盘/看板），`.env.production` 指向本机后端
  - 桌面壳 `desktop/`：Electron 主进程（窗口/托盘常驻/通知权限）+ 启动器（先起后端再开窗）
- 关键文件：
  - `backend/app/{main,config}.py`、`app/core/{llm,prompts,extractor,agent,planner,reviewer,psychology}.py`、`app/services/*`、`app/api/*`、`app/db/{database,repos}.py`
  - `backend/tests/*`；`frontend/src/{App.vue,router.ts,api/client.ts}`、`frontend/src/views/*`（5 个）
  - `desktop/{main.js,preload.js,scripts/start.js}`
- 关键决策：前端构建产物 `dist/` 为桌面默认加载目标；LLM 提供商待用户配置 `.env`
- 行为变化：真实服务可运行闭环（对话打卡→任务完成→宽容统计→主动问询→周复盘→看板）
- 验证：
  - `backend: pytest tests -q` → 24 passed
  - `frontend: npm run build` → 构建成功（仅 chunk 体积提示）
  - 冒烟：uvicorn 启动、/api/stats/dashboard、/api/checkin/status、/api/templates 均 200
  - `desktop: npm install` 完成
- 测试：新增 test_database / test_extractor / test_agent / test_api（覆盖宽容口径、温和重启、未来日期拒绝、补记、502 降级）
- 未完成项：LLM API Key 未配置（对话回复需真实密钥）；Electron 窗口真实打开验证待本机执行 `desktop\npm start`

## 2026-09-13 — 编码阶段（Electron 端到端验收修复）

- 需求/问题：Electron 生产模式端到端验收发现三处集成问题，全部修复后全链路 200
- 类型: bug-fix
- 改动范围：
  1. 前端构建产物在 `file://` 下无法加载（Vite 默认绝对路径 `/assets/...`）→ `vite.config.ts` 设 `base: './'`
  2. 生产 API 地址缺 `/api` 前缀 → `.env.production` 改为 `VITE_API_BASE=http://127.0.0.1:8000/api`（`src/api/client.ts` 读取）
  3. 真实 uvicorn 线程池下 SQLite 跨线程使用报错（TestClient 单线程未暴露）→ `db/database.py` 连接加 `check_same_thread=False`（每请求独立连接，无并发共享）
  4. 后端补 CORS 中间件（Electron file:// 跨源访问本地 API）
- 关键文件：`backend/app/main.py`、`backend/app/db/database.py`、`frontend/vite.config.ts`、`frontend/.env.production`、`frontend/src/api/client.ts`
- 验证：
  - 回归 `pytest tests -q` → 24 passed
  - Electron 启动 → CDP 检查 DOM：导航/视图/空态正常渲染
  - 后端日志：`GET /api/messages|templates|checkin/status` 全部 200
  - 真实链路：POST /api/goals 创建目标 → GET /api/stats/dashboard 回读成功
- 测试：既有用例不变（修复不改变接口行为）

## 2026-09-13 — 新增模型配置页（v0.4）

- 需求/问题：对话功能依赖 LLM 配置，需要应用内配置页（Base URL / API Key / 模型名 + 测试连接 + 保存即生效），替代手工改 `.env`
- 类型: new-feature
- 改动范围：
  - 后端：新增 `services/model_config_service.py`（数据库配置加载/保存/构建/热更新提供商）、`api/settings.py`（GET/POST /api/settings/model、POST /api/settings/model/test）；`main.py` 提供商初始化改为「数据库配置优先，.env 兜底」并注册 settings 路由；`llm.py` 增加公开 `get_provider()`
  - 前端：新增 `views/SettingsView.vue`（配置表单 + 状态标签 + 测试结果），路由 `/settings`，侧边导航加「模型配置」
  - 文档：`api.md` §1.9、`style-guide.md` 页面清单
- 关键决策：API Key 存本地 SQLite（单用户本地应用），GET 仅返回脱敏值；`api_key` 为空时保留已存值（不可经接口清空）；保存即热更新无需重启
- 行为变化：应用内可完成模型配置与连通性验证；配置持久化且优先级高于 `.env`
- 验证：
  - `pytest tests -q` → 30 passed（新增 test_settings.py 6 例：默认空态/保存热更新/空 key 保留/校验/测试连接成功失败）
  - 前端 `npm run build` 成功
  - 端到端（网页代理链路）：GET 空态 → POST 保存 → 脱敏正确 → 持久化回读；测试后已清理演示配置
- 测试：新增 tests/test_settings.py
- 修复的坑：`create_app(settings)` 参数名与 `api.settings` 模块同名导致遮蔽（导入改名 `settings_api`）；`save_config` 参数名与数据库键名不一致

## 2026-09-13 — 配置入口改右下角（v0.4.1）

- 需求/问题：配置入口不应占主导航位；改为右下角齿轮按钮，模型配置作为设置面板中的可扩展配置项
- 类型: ui-change
- 改动范围：
  - 新增 `frontend/src/components/SettingsDrawer.vue`（设置抽屉：左侧配置项列表 + 右侧内容区，`sections` 列表可扩展）
  - 新增 `frontend/src/components/ModelConfigForm.vue`（由原 SettingsView 迁移）
  - `App.vue`：右下角固定齿轮按钮（`@element-plus/icons-vue`），移除侧边导航「模型配置」菜单项
  - 删除 `views/SettingsView.vue` 与 `/settings` 路由；`package.json` 新增图标库依赖
- 关键决策：配置统一收敛到设置抽屉，后续新增配置（通用/通知/数据等）在 `SettingsDrawer.sections` 追加一项即可，无需改导航
- 验证：`npm run build` 成功；dev server 热更新后页面 200、组件正常提供
- 测试：无后端变更，前端构建验证通过

## 2026-09-14 — 前端整体视觉重设计（v0.5）

- 需求/问题：用户反馈「页面不好看，重新设计」
- 类型: ui-redesign
- 改动范围：全部前端视图与组件
  - `style.css`：新增设计令牌（侧边栏色/卡片阴影/圆角/渐变），背景改 `#F0F2F5`
  - `App.vue`：侧边栏改深蓝灰 `#1A2B36`（210px），logo 区加渐变图标，菜单加图标 + 激活态绿色渐变，顶部栏加日期，齿轮按钮改绿色渐变
  - `ChatView.vue`：聊天页全屏沉浸布局，状态 chip 化，气泡用户侧绿色渐变/助手侧白色阴影，输入区卡片化，模板标签精致化，加载动画
  - `GoalsView.vue`：目标卡片左侧分类色条 + hover 上浮，自定义复选框，分类 tab 胶囊化，AI 拆解按钮
  - `SchedulesView.vue`：周视图 7 列网格，今日列高亮，日程卡片左侧色条，空槽虚线添加
  - `ReviewsView.vue`：复盘卡片精致化，头部周期 + 时间
  - `DashboardView.vue`：4 色统计卡片（顶部色条 + 图标块），目标进度条渐变，类型分布横条，最近记录列表
  - `SettingsDrawer.vue` / `ModelConfigForm.vue`：匹配新风格
- 关键决策：保留绿色主色与功能不变，仅升级视觉层次；深色侧边栏形成专业桌面应用感
- 验证：`npm run build` 成功（修复了 `Sparkles`/`Target`/`ChatLineSquare` 图标不存在的问题，替换为 `MagicStick`/`Aim`/`ChatLineRound`）
- 测试：无后端变更

## 2026-09-14 — 萌系视觉重设计（v0.6）

- 需求/问题：用户反馈「可以不要做的像后台管理一样吗，萌一些」
- 类型: ui-redesign
- 改动范围：全部前端视图与组件，纯视觉层
  - `style.css`：主色改柔和薄荷绿 `#7BC8A4`，背景改奶油米白 `#FFF9F2`，圆角 20px，柔和边框替代硬阴影
  - `App.vue`：侧边栏改奶油色（非深色），logo 用 🌱 emoji，菜单全部 emoji 化，顶部栏加鼓励语，齿轮按钮改粉橙渐变 + hover 旋转
  - `ChatView.vue`：气泡薄荷绿渐变，状态 chip 加 emoji，发送按钮粉橙渐变，模板标签橙色
  - `GoalsView.vue`：目标卡片左侧色条改 emoji 分类图标，自定义圆角复选框，分类 tab 胶囊化，按钮全部渐变圆角
  - `SchedulesView.vue`：7 列网格，今日列薄荷绿高亮，日程卡片左侧色条，空槽虚线
  - `ReviewsView.vue`：紫色系按钮，复盘卡片柔和边框
  - `DashboardView.vue`：4 色渐变统计卡片（薄荷/桃/粉/紫）+ emoji，渐变进度条按分类着色
  - `SettingsDrawer.vue` / `ModelConfigForm.vue`：emoji 配置项，柔和风格
- 关键决策：移除所有 element-plus 线性图标，统一用 emoji；去掉深色侧边栏和硬阴影；文字用柔和深灰不用纯黑
- 验证：`npm run build` 成功
- 测试：无后端变更

## 2026-09-14 — 交互娱乐化升级（v0.7）

- 需求/问题：用户反馈「页面可以绘制的有趣一点，多一些交互娱乐」
- 类型: feature + ui
- 改动范围：
  - 新增 `components/Confetti.vue`：撒花庆祝组件（40 粒子，6 色，触发式）
  - 新增 `components/GrowthTree.vue`：成长小树苗（6 阶段 🌰→🌱→🌿→🪴→🌳→🌲，点击摇摆，进度条显示距下一阶段）
  - 新增 `components/CountUp.vue`：数字滚动动画（ease-out 缓动）
  - `App.vue`：浮动背景装饰（🌸⭐🍀✨🌙 缓慢上浮），页面切换淡入上滑过渡动画
  - `DashboardView.vue`：顶部接入成长小树苗，统计数字全部 CountUp 滚动，累计记录跨越里程碑（10/30/50/100/200）时自动撒花
  - `GoalsView.vue`：勾选完成任务时触发撒花
  - `ChatView.vue`：助手回复打字机逐字显示，消息气泡弹入动画
  - `SchedulesView.vue`：完成日程时卡片弹跳动画
- 关键决策：纯 CSS + 少量 JS 实现，不引入动画库；撒花仅在「完成」正向动作触发，不滥用
- 验证：`npm run build` 成功
- 测试：无后端变更
