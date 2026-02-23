# Phase 107 - DecisionUnit（平台神经元）+ semantic_main_view（语义单一真相）落地

日期：2026-01-03

## 背景（一句话）
Phase105/106 已经把“系统不撒谎、能自愈、账本可追溯”封死；Phase107 的第一步不继续堆报告，而是先把**平台级中间产物**打出来：DecisionUnit（对外可复用的决策单元）+ semantic_main_view（对外只认一个语义口径）。

## 本阶段不许破的合同（沿用 Phase105/106）
- 合同A：任何合法请求不因 RLS/GUC 缺失而 500（跨用户访问 403/404 都行，但不许 500）
- 合同B：主链路不被新能力拖慢/拖死（DecisionUnit 写入/校验失败也不许把分析/报告搞 500）
- 合同C：账本可追溯（后续 DecisionUnit 必须能回答“从哪来/证据是谁/版本是什么”）

---

## 任务清单（按顺序 1/2/3/4… 依次落地，不穿插）

### 1) 落地 semantic_main_view（融合 SSOT：tags_analysis 优先，缺啥用别的补齐）
目标（说人话）：以后系统对外别再“两个语义口径各说各话”，统一从一个视图拿“我到底给这条内容打了什么标签/提了哪些品牌”。

落地内容：
- [x] 新增 DB 视图 `semantic_main_view`（posts + comments 统一口径）
  - tags/实体优先读 `post_scores_latest_v` / `comment_scores_latest_v`
  - taxonomy 读 `post_semantic_labels`
  - labels/entities 补齐读 `content_labels` / `content_entities`
  - provenance 明确标记：哪些字段来自哪条链路（并且容忍历史脏值如 `pain_tag`）
- [x] 迁移：`backend/alembic/versions/20260103_000001_create_semantic_main_view.py`
- [x] 测试：`backend/tests/models/test_semantic_main_view.py`

验收（眼睛一看就懂）：
- 同一条 post/comment 既能看到 `tags_analysis/entities_extracted`，也能看到 taxonomy/labels/entities 的补齐结果；
- 即使 `content_labels.category` 出现脏值（历史遗留），查询也不炸；
- tags_analysis 缺失时，依然能用 taxonomy 做兜底（而不是整条内容“语义空白”）。

---

### 2) DecisionUnit 存储落地（复用 insight_cards + decision_units_v 视图）
目标（说人话）：DecisionUnit 要当“平台神经元”，但工程上先别搬家——用现有 `insight_cards` 加抽屉，最快出第一桶水；对外用 `decision_units_v` 当稳定门面。

落地内容：
- [x] DB 迁移：`backend/alembic/versions/20260103_000002_add_decision_unit_fields.py`
  - `insight_cards` 增列：`kind/concept_id/signal_type/du_schema_version/du_payload`
  - Unique 约束升级：`(task_id, kind, title)`（允许同 task 下同 title 的“旧洞察卡”与“决策单元”共存）
  - 索引补齐（含 `du_payload` 的 GIN）以支撑后续 feed/pagination
  - 新建视图：`decision_units_v`（对外读口径）
  - `evidences` 增列：`content_type/content_id`（证据链从 URL 升级为“可审计的内部主键”）
- [x] ORM 同步：`backend/app/models/insight.py`
- [x] 补齐缺失的引用表模型：`backend/app/models/semantic_concept.py`（否则 ORM 外键会报 NoReferencedTableError）
- [x] 测试：`backend/tests/models/test_decision_units_schema.py`

验收：
- `insight_cards` 既能存旧卡（kind=insight），也能存 DecisionUnit（kind=decision_unit）；
- `decision_units_v` 只返回 decision_unit；
- `evidences` 具备 content_type/content_id，后续可追溯到具体 post/comment。

---

### 3) 新 API 主合同：/api/decision-units
目标（说人话）：DecisionUnit 不能绑在 report/admin 里当“又一种输出”，必须作为独立资源给别人用。

落地内容：
- [x] 新 schema：`backend/app/schemas/decision_unit.py`
- [x] 新 endpoints：`backend/app/api/v1/endpoints/decision_units.py`
  - `GET /api/decision-units`：支持按 task_id / concept_id / signal_type 过滤 + 分页
  - `GET /api/decision-units/{id}`：返回详情 + 证据链
- [x] 接入 v1 路由（/api 与 /api/v1 同时生效）：`backend/app/api/v1/api.py`
- [x] API 测试：`backend/tests/api/test_decision_units.py`

验收：
- 只能看到自己的 decision units（跨用户访问 403/404，但不许 500）；
- detail 返回 evidence，且包含 `content_type/content_id`；
- 不影响黄金业务路径：/api/analyze → worker → /api/report。

---

### 4) 旧洞察卡 API 不被 DecisionUnit 污染（保持向后兼容）
落地内容：
- [x] `InsightService` 只返回 `kind='insight'`，避免未来 DecisionUnit 生成后“洞察页混进一堆运营决策单元”。
  - 修改：`backend/app/services/insight_service.py`

---

### 5) Phase107#1 通水：tier_suggestions → ops DecisionUnit（第一桶水）
目标（说人话）：社区池的“升/降级建议”不再只是后台一坨 JSON，而是能落成 **可复用的 DecisionUnit**，并且带上“代表性证据”，后续才能做订阅/复盘/反馈/学习闭环。

落地内容：
- [x] 新增生产线服务：`backend/app/services/ops/tier_suggestion_decision_units.py`
  - 输入：`TierSuggestion`（可按 id 指定）
  - 输出：`InsightCard(kind='decision_unit', signal_type='ops') + du_payload`
  - 为某天生成/复用一个 ops task（uuid5，幂等）
  - 证据链：从对应社区近 N 天 `posts_raw` 里挑 top engagement 帖子写入 `evidences`（并补齐 `content_type/content_id`）
- [x] 修掉“pain_tag enum 报错刷屏”的根因：`backend/app/models/comment.py`
  - `content_labels.category/aspect` 改为自由文本（String），允许历史/回填的 `pain_tag/aspect_tag` 等值
  - `content_entities.entity_type` 同步改为 String，避免未来扩展时再踩 Enum 映射坑
- [x] 测试覆盖：
  - `backend/tests/services/ops/test_tier_suggestion_decision_units.py`（会产出 DecisionUnit + evidence，且二次运行幂等不重复）
  - `backend/tests/models/test_content_labels_legacy_values.py`（验证 ORM 读取 `pain_tag` 不炸）

验收：
- 给定一条 tier_suggestion，可以稳定产出 ops DecisionUnit（能查到 du_payload lineage= tier_suggestions）；
- evidences 至少 1 条，且带 `content_type/content_id`；
- 同一条建议重复执行不会重复生成 decision unit（幂等）。

---

### 6) Phase107#5 闭环入口：DecisionUnit 反馈事件（append-only）
目标（说人话）：DecisionUnit 不只是“系统自己说的”，必须允许人类在证据链上给一句“对/不对/跑偏/值不值”，让系统以后能学。

落地内容：
- [x] 新增表：`decision_unit_feedback_events`（append-only）
  - 迁移：`backend/alembic/versions/20260103_000003_add_decision_unit_feedback_events.py`
  - 强约束：label 只能是 `correct/incorrect/mismatch/valuable/worthless`
  - 允许缺省 evidence_id（服务端会自动选 top evidence），但最终必须能回放到某条证据
- [x] 新增模型：`backend/app/models/decision_unit_feedback_event.py`
- [x] 新增 API：`POST /api/decision-units/{id}/feedback`
  - 只允许 owner（通过 tasks.user_id 绑定，不会跨用户写入）
  - evidence 校验：如果传 evidence_id，必须属于该 DecisionUnit，否则 400
  - 软去重（防手滑连点）：默认 120 秒窗口（`DECISION_UNIT_FEEDBACK_DEDUPE_WINDOW_SECONDS`）
- [x] 测试：`backend/tests/api/test_decision_unit_feedback.py`

验收：
- 任意一条反馈事件能一键回放：DecisionUnit → evidence → label/备注/时间/人。
- 跨用户不允许提交（403/404 皆可，但不许 500）。

---

### 7) Phase107#2 运营节奏：定时产出 + 管理员手动触发（不靠工程师盯）
目标（说人话）：第一桶水不能只停留在“工程师说它能跑”，必须进入“每天自动出一张建议单”的稳定节奏；同时保留 Admin 一键补跑阀门。

落地内容：
- [x] Celery 定时任务：`tasks.tier.emit_daily_suggestion_decision_units`
  - 代码：`backend/app/tasks/tier_intelligence_task.py`
  - 调度：`backend/app/core/celery_app.py`（每天 01:10 UTC 触发，跑在 monitoring_queue）
  - 说明：owner 用户通过 `OPS_DECISION_UNIT_USER_ID` / `OPS_DECISION_UNIT_USER_EMAIL`（或 `ADMIN_EMAILS` 第一个）解析；缺配置则跳过（不炸主链路）
  - 轻量 run ledger：写入 `data_audit_events`（best-effort，不影响产出）
- [x] Admin 手动触发阀门：
  - `POST /api/admin/communities/tier-suggestions/emit-decision-units`
  - 代码：`backend/app/api/legacy/admin_community_pool.py`
- [x] 测试：
  - Admin 触发：`backend/tests/api/test_admin_emit_tier_suggestion_decision_units.py`
  - Beat 配置回归：`backend/tests/tasks/test_celery_beat_schedule.py`

验收：
- 可以用 Admin 一键生成今日建议单（并能通过 `/api/decision-units` 查到）。
- 定时任务已入表/入调度（线上只需要配置 owner 账号即可跑起来）。

---

### 8) 补充验收（2026-01-18）：本地“真跑通”（DB 升级 + 真实产出 + 反馈落库）
目标（说人话）：不是“代码写完/测试过了”，而是让本地数据库里**真的长出** DecisionUnit、证据、反馈事件，闭环能用。

本地遇到的真实问题：
- 本地库还停在旧版本（`alembic_version=20251229_000001`），导致：
  - `insight_cards.kind` 这类新列不存在；
  - `decision_units_v / semantic_main_view / decision_unit_feedback_events` 也不存在；
  - 新能力“看起来能跑”，但库里根本落不下去。

落地动作（按顺序）：
- [x] 停掉本地 celery worker/beat（避免迁移锁表时互相打架）
- [x] 升级本地数据库到 head（本地执行）
  - `MIGRATION_DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner' alembic upgrade head`
  - 升级结果：`alembic_version=20260103_000003`
  - 核对：`insight_cards.kind/du_payload` 已存在；`decision_units_v / semantic_main_view` 视图存在；`decision_unit_feedback_events` 表存在
- [x] 重启本地 worker/beat（本地执行）
  - `bash backend/start_celery_worker.sh`
  - `bash backend/start_celery_beat.sh`
  - 健康检查：`celery inspect ping` 返回 `pong`
  - 脚本注意：从 repo 根目录跑需要 `PYTHONPATH=backend python backend/scripts/check_celery_health.py`
- [x] 本地通水：把现有 `tier_suggestions` 翻译成 ops DecisionUnit（手动阀门）
  - 先用 `POST /api/auth/register` / `POST /api/auth/login` 拿 token（本地用白名单邮箱 `prd-test@example.com`，因为 `ADMIN_EMAILS` 里允许它做 admin）
  - 再 `POST /api/admin/communities/tier-suggestions/emit-decision-units`（默认处理 pending 且未过期的建议）
  - 回包里能看到幂等行为：`created_units / skipped_existing_units / created_evidences`
- [x] 本地闭环：DecisionUnit 列表可查 + feedback 可写入
  - `GET /api/decision-units?signal_type=ops`：本地能看到 ops 决策单元列表
  - `POST /api/decision-units/{id}/feedback`：写入一条 `valuable` 反馈事件（自动绑定 top evidence）

验收结果（本地库真实数据）：
- `tasks(mode=operations)`：1 条
- `insight_cards(kind=decision_unit, signal_type=ops)`：5 条
- `evidences`：15 条（全部带 `content_type/content_id`）
- `decision_unit_feedback_events`：1 条（可回放到具体 evidence）

---

## 证据（测试命令 + 结果）
- semantic_main_view：`python -m pytest backend/tests/models/test_semantic_main_view.py -q` ✅
- DecisionUnit schema：`python -m pytest backend/tests/models/test_decision_units_schema.py -q` ✅
- DecisionUnit API：`python -m pytest backend/tests/api/test_decision_units.py -q` ✅
- 旧洞察兼容：`python -m pytest backend/tests/api/test_insights.py -q` ✅
- 合同A 回归：`python -m pytest backend/tests/models/test_rls_current_user_context.py -q` ✅
- ops 通水（tier_suggestions → DecisionUnit）：`python -m pytest backend/tests/services/ops/test_tier_suggestion_decision_units.py -q` ✅
- legacy 标签不炸（pain_tag）：`python -m pytest backend/tests/models/test_content_labels_legacy_values.py -q` ✅
- DecisionUnit 反馈：`python -m pytest backend/tests/api/test_decision_unit_feedback.py -q` ✅
- Admin 手动阀门：`python -m pytest backend/tests/api/test_admin_emit_tier_suggestion_decision_units.py -q` ✅
- Beat 调度回归：`python -m pytest backend/tests/tasks/test_celery_beat_schedule.py -q` ✅
- 本轮复验（关键用例合集）：`python -m pytest backend/tests/models/test_content_labels_legacy_values.py backend/tests/api/test_decision_unit_feedback.py backend/tests/api/test_admin_emit_tier_suggestion_decision_units.py backend/tests/tasks/test_celery_beat_schedule.py -q` ✅（23 passed）

---

## 统一反馈四问（这次 Phase107 的“说人话版”）
1) 发现了什么问题/根因？
   - 之前系统的“语义口径”散在多条链路里，容易出现同一条内容在不同模块里标签不一致。
   - 另外，DecisionUnit 要平台化，但如果先新造表/搬家，会引入第二条真相线，工期和风险都更大。
2) 是否已精确定位？
   - 是：需要一个融合 SSOT（semantic_main_view）统一语义读口径；DecisionUnit 存储先复用 insight_cards 并用 view 做稳定门面。
3) 精确修复方法？
   - 新增 `semantic_main_view`（融合视图 + provenance），并补齐测试覆盖“tags 缺失/脏值”场景。
   - insight_cards 增列 `kind/du_payload...` + 新建 `decision_units_v`，并升级唯一约束与索引。
   - 新增 `/api/decision-units` 主合同 API（列表/详情）。
4) 下一步做什么？
   - Phase107 可以“整体关账”：已经具备最小闭环（能产出 + 能回放 + 能反馈 + 不影响主链路）。
   - 后续更高级的自优化（topic_profile 补丁建议、阈值建议、样本库制度化、自愈策略学习）建议作为下一阶段插件推进（Phase108/后续迭代）。
5) 这次修复效果是什么？
   - 现在 DecisionUnit 已经是独立资源：有存储、有视图、有 API、有证据链字段；
   - semantic_main_view 已经能把“主语义+补齐语义”统一输出，且对历史脏值有韧性；
   - ops 场景的第一条生产线已通水：tier_suggestions 可以稳定落成 DecisionUnit + evidences；
   - DecisionUnit 已具备反馈入口（append-only）并能回放到证据；
   - 定时产出 + Admin 手动阀门已接入，开始进入可运营节奏；
   - content_labels 允许自由文本后，worker 不再因为 `pain_tag` 这类历史值刷屏报错；
   - 不影响现有黄金业务路径，且合同A（RLS 不 500）回归通过。
