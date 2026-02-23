# Phase 23 - TopicProfile 落地（保守版）：topic_profile_id 从 API → DB → 引擎生效

日期：2025-12-17  
代码基线：`main@fbc5a89`（工作区 dirty；本阶段以当前代码实况为准）

## 一句话结论

把“先定赛道规则”这件事做成了可控开关：**调用方在 `/api/analyze` 传 `topic_profile_id` → tasks 表永久记住 → 后台引擎按 TopicProfile 限定社区范围 + 调整抓取/过滤关键词**，同时把 profile 信息写进 `Analysis.sources` 方便回溯。

---

## 我查到的证据（以代码为准）

### 1) API 入口（黄金门牌仍是 `/api`）
- 路由挂载：`backend/app/main.py:create_application`（v1 router 仍挂在 `prefix="/api"`）
- 创建任务：`backend/app/api/v1/endpoints/analyze.py:create_analysis_task`

### 2) topic_profile_id 入参 + 落库
- 入参 schema：`backend/app/schemas/task.py:TaskCreate.topic_profile_id`
- tasks 表字段：`backend/app/models/task.py:Task.topic_profile_id`
- DB 迁移：`backend/alembic/versions/20251217_000002_add_topic_profile_id_to_tasks.py`
- API 校验+写入：`backend/app/api/v1/endpoints/analyze.py:_validate_topic_profile_id` + `Task(topic_profile_id=...)`

### 3) TopicProfile 配置来源（可复现）
- 解析逻辑：`backend/app/services/topic_profiles.py:load_topic_profiles`
- 配置文件（推荐/可追踪）：`config/topic_profiles.yaml`

### 4) 后台执行真正生效（不是“只存不用”）
- pipeline 把字段带进引擎：`backend/app/tasks/analysis_task.py:_mark_processing`（写入 `TaskSummary.topic_profile_id`）
- 引擎应用 profile（社区/关键词/过滤）：`backend/app/services/analysis_engine.py:run_analysis`
  - `build_search_keywords` / `build_fetch_keywords`
  - `topic_profile_allows_community`
  - `topic_profile_blocklist_keywords` + `_apply_topic_profile_context_filter`
- 引擎回写证据：`backend/app/services/analysis_engine.py:sources`（写入 `topic_profile_id/topic_profile/fetch_keywords`）

---

## 端到端链路（本期只做后端黄金主线）

`POST /api/analyze (topic_profile_id=...)`  
→ API 校验该 id 是否存在（找不到直接 422）  
→ tasks 表写入 `topic_profile_id`  
→ pipeline 执行时把 `topic_profile_id` 带进引擎  
→ analysis_engine 按 TopicProfile “选社区 + 选关键词 + 做过滤”，并把证据写进 sources  

---

## 当前问题与根因（按模块归因）

### 1) 之前“赛道规则”只是文档设想，代码里没入口
- 现状：API 没有 `topic_profile_id`，DB 也不存，后台只能“看一句话瞎猜”。
- 后果：你想要的“可复现的赛道选择/社区白名单/窄题双钥匙”没法落地。

### 2) 早期实现踩坑：TopicProfile + mode 交叉过滤会把社区筛成 0
- 根因：`mode=market_insight` 会粗粒度排除 seller 社区；但像 `shopify_ads_conversion_v1` 这种 profile 本身就是 seller 盘子，交叉以后就“全被误杀”。
- 修正：**当指定 TopicProfile 时，以 profile 的社区范围为准，不再让 mode 的粗筛去误杀**（mode 仍会记录在 sources 里，便于审计）。

---

## 方案（保守版 / 升级版）

### 保守版（本期已落地）
- tasks 表新增 `topic_profile_id`（可为空；非空不允许空串）
- API 支持传 `topic_profile_id`，并严格校验存在性（不存在直接 422）
- 引擎按 profile：
  - 限定社区范围（allowlist/pattern）
  - 用 profile 生成 `search_keywords/fetch_keywords`
  - 过滤掉 profile 明确排除的内容（blocklist + 窄题 context 过滤）
  - 把 profile 元信息写进 sources（可追溯）

### 升级版（下一期再做）
- 把 facts v2 的 A/B/C/X 门禁与报告分级，统一进产品 API 的主链路（替代脚本主导）

---

## 风险与回滚

- 风险：TopicProfile 配置文件缺失/写错会导致任务直接失败（这是“诚实失败”，便于定位配置缺口）。
- 回滚：保留 DB 字段不影响旧链路；把引擎里 topic_profile 相关逻辑短路（不加载/不筛选）即可回到“只按 product_description 跑”的旧行为。

---

## 测试与监控（必须包含）

### 新增/更新测试
- `backend/tests/api/test_analyze.py`
  - 默认 `topic_profile_id=None`
  - 传 `shopify_ads_conversion_v1` 能创建任务并落库
  - 传未知 id 直接 422

### 本地验证命令（我实际跑过）
- `cd backend && PYTEST_RUNNING=1 APP_ENV=test ENABLE_CELERY_DISPATCH=0 DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q tests/api/test_analyze.py`

---

## 验收标准（可量化）

1) 调用 `/api/analyze` 传 `topic_profile_id=shopify_ads_conversion_v1`：DB 里该任务 `topic_profile_id` 正确落库。  
2) 调用 `/api/analyze` 传未知 `topic_profile_id`：接口直接 422，任务不入库。  
3) 当任务带 `topic_profile_id` 跑完：`Analysis.sources` 里能看到 `topic_profile_id` 与 `topic_profile` 元信息（用于审计与复现）。  
