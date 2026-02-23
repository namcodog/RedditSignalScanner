# 社区池动态调级实现记录（后端 + 前端 v1）

## 一、本次实现范围

- 按「社区池 & Tier 动态调级」方案，完成后端数据结构、服务层、Admin API、定时任务与前端基础管理界面。
- 聚焦能力：
  - 手动调整：社区 tier / priority / is_active 批量更新 + 审计日志
  - 智能建议：基于 posts_hot / comments / 语义标注的多维指标生成调级建议
  - 自动化：每日生成建议，支持高置信度自动应用（可配置开关）

## 二、后端改动概览

### 1. 数据模型与迁移

- 新增模型：
  - `backend/app/models/tier_suggestion.py` → 表 `tier_suggestions`
    - 字段：`community_name/current_tier/suggested_tier/confidence/reasons/metrics/priority_score/status/generated_at/reviewed_by/reviewed_at/applied_at/expires_at`
  - `backend/app/models/tier_audit_log.py` → 表 `tier_audit_logs`
    - 字段：`community_name/action/field_changed/from_value/to_value/changed_by/change_source/reason/snapshot_before/snapshot_after/suggestion_id/is_rolled_back/rolled_back_at/rolled_back_by`
- 扩展 `CommunityPool` 模型：
  - 新增字段：
    - `health_status: str`（healthy | warning | critical | unknown）
    - `last_evaluated_at: datetime | None`
    - `auto_tier_enabled: bool`（是否允许自动调级）
- Alembic 迁移：
  - `backend/alembic/versions/20251120_000036_add_tier_intelligence_tables.py`
    - 创建 `tier_suggestions` / `tier_audit_logs`
    - 为 `community_pool` 添加上述三个字段及默认值

### 2. TierIntelligenceService

- 新增服务：`backend/app/services/tier_intelligence.py`
  - `CommunityMetrics`：
    - 指标：posts_per_day、comments_per_day、pain_density、brand_mentions、feature_coverage、sentiment_score、growth_rate、diversity_score、labeling_coverage、spam_ratio、avg_engagement
    - 趋势：posts_trend_7d、comments_trend_7d、pain_trend_30d
  - `TierThresholds`：
    - 内嵌 `PromoteToT1/PromoteToT2/DemoteToT3/RemoveFromPool` 默认阈值，支持按请求覆盖部分字段
  - 核心方法：
    - `calculate_community_metrics(community_name, lookback_days=30)`：
      - 从 `posts_hot` / `comments` / `content_labels` / `content_entities` 中汇总指标
    - `generate_tier_suggestions(thresholds, target_communities=None)`：
      - 对 active 社区批量生成升级/降级/移除建议（仅内存结构）
    - `get_latest_suggested_tier(community_name)`：
      - 读取 `tier_suggestions` 获取最新 pending/applied/auto_applied 建议的目标 tier
  - 内部评估逻辑：
    - `_recommend_tier`：结合 `CommunityPool.quality_score` 与阈值判断 T1/T2/T3/REMOVE
    - `_calculate_confidence`：根据指标与阈值距离估算置信度（0–1），跨级调低权重
    - `_generate_reasons`：产出简要中文理由（帖量、痛点密度、增长、标注覆盖）
    - `_calculate_priority_score`：置信度 + 活跃偏离度 + 健康状态 + 质量分
    - `_assess_health_status`：粗粒度划分 healthy/warning/critical

### 3. Admin API 扩展（admin_community_pool）

- 文件：`backend/app/api/routes/admin_community_pool.py`
- `GET /api/admin/communities/pool`（增强版）：
  - 新增查询参数：
    - `tier/priority/is_active/health_status`
    - `sort_by`（quality_score/daily_posts/avg_comment_length/name）、`order`
    - `page/page_size`
  - 返回数据结构在原有基础上增加：
    - `health_status`
    - `auto_tier_enabled`
    - `recent_metrics`: `posts_7d/comments_7d/pain_density_30d/brand_mentions_30d`
    - `tier_suggestion`: 最新建议的目标 tier（无则 null）
- `PATCH /api/admin/communities/batch`：
  - 请求体：`{ communities: string[], updates: { tier?, priority?, is_active?, downrank_factor? }, reason? }`
  - 行为：
    - 批量更新 `CommunityPool`
    - 为每个社区写入一条 `TierAuditLog(action=batch_update, field_changed=multiple, snapshot_before/after)`
- `POST /api/admin/communities/suggest-tier-adjustments`：
  - 请求体：`{ thresholds?: TierThresholdsPayload, target_communities?: string[] }`
  - 调用 `TierIntelligenceService.generate_tier_suggestions` 生成建议
  - 将结果批量插入 `tier_suggestions`（默认过期时间 7 天）
  - 返回：`{ suggestions, summary }`
- `POST /api/admin/communities/apply-suggestions`：
  - 请求体：`{ suggestion_ids: number[] }`
  - 将对应 pending 建议应用到 `CommunityPool.tier`，并：
    - 修改建议状态为 `applied`，填充 `reviewed_by/reviewed_at/applied_at`
    - 写入一条 `TierAuditLog(action=tier_change, change_source=suggestion, suggestion_id=...)`
- `POST /api/admin/communities/rollback`：
  - 请求体：`{ audit_log_id: number, reason: string }`
  - 依据 `TierAuditLog.snapshot_before` 回滚社区配置，并：
    - 标记原日志为已回滚
    - 写入一条 `TierAuditLog(action=rollback, ...)` 记录回滚操作
- `POST /api/admin/communities/approve`：
  - 新增行为：当社区已存在时，同步更新 `pool.tier = body.tier`，避免“重新审批但 tier 不随审批更新”的情况。

### 4. 定时任务（Celery）

- 新增任务：`backend/app/tasks/tier_intelligence_task.py`
  - `generate_daily_tier_suggestions`（Celery 任务入口）：
    - 每日生成所有 active 社区的调级建议并落库 `tier_suggestions`
    - 统计返回：总建议数及各类建议数量
    - 受环境变量 `ENABLE_AUTO_TIER_APPLICATION` 控制：
      - 为 true 时，调用 `_apply_high_confidence_suggestions`：
        - 自动应用置信度 ≥ 0.9 且 `auto_tier_enabled == True` 且 `is_active == True` 的建议
        - 更新社区 tier，标记建议 `status=auto_applied`，并写入 `TierAuditLog(change_source=auto)`
- 在 `backend/app/core/celery_app.py` 中：
  - `task_routes` 添加路由：`"tasks.tier.generate_daily_suggestions" -> monitoring_queue`
  - `beat_schedule` 添加：
    - `"generate-daily-tier-suggestions"`：每天 01:00 运行任务
  - 确保任务模块被导入：`from app.tasks import tier_intelligence_task as _tier_task`

## 三、前端界面与服务层

### 1. Admin Service 扩展

- 文件：`frontend/src/services/admin.service.ts`
  - `getCommunityPool`：
    - 参数扩展为：`{ page?, page_size?, tier?, is_active?, health_status?, priority? }`
    - 返回值扩展为：`{ items, total, page, page_size }`，items 为后端增强后的社区记录
  - 新增方法：
    - `batchUpdateCommunityPool(payload)`：
      - 封装 `PATCH /admin/communities/batch`
    - `generateTierSuggestions(payload)`：
      - 封装 `POST /admin/communities/suggest-tier-adjustments`
    - `applyTierSuggestions(payload)`：
      - 封装 `POST /admin/communities/apply-suggestions`

### 2. 社区池管理页面（v1）

- 新页面：`frontend/src/pages/admin/CommunityPoolManager.tsx`
  - 页面内容：
    - 顶部标题区：`社区池管理` + 简短说明
    - 工具栏：
      - 筛选：
        - Tier：全部/T1/T2/T3
        - 健康状态：全部/健康/警告/严重
        - 状态：全部/启用/禁用
      - 动作：
        - `生成调级建议`：调用 `adminService.generateTierSuggestions`，成功后打开右侧建议抽屉
        - 当有选中行时显示 `批量设为 T2`：调用 `batchUpdateCommunityPool`
    - 列表表格：
      - 列：勾选框、社区名称、Tier、优先级、状态、日均帖子、健康状态、调级建议
      - 健康状态通过 emoji+文字展示（🟢 健康 / 🟠 警告 / 🔴 严重 / 未知）
      - 调级建议列显示最新 `tier_suggestion`（例如“建议：T1”），无则显示“暂无”
      - 支持全选/单选行，用于批量操作
    - 右侧抽屉（建议面板）：
      - 标题：`调级建议`
      - 列表每条建议展示：
        - 社区名、当前 tier → 建议 tier
        - 置信度（百分比）和优先级分
        - 文本化理由列表（来自后端 `reasons`）
      - 当前版本只读展示；后续可加「一键应用」/「批量应用」按钮。

### 3. 前端路由

- 当前路由配置中：
  - `/admin` 仍为 `AdminDashboardPage`
  - `CommunityPoolManager` 暂未挂入路由，后续可按产品规划挂在：
    - 如 `/admin/communities/pool` 或在 AdminDashboard 中增加 Tab 嵌入

### 4. 前端测试

- 新增测试：`frontend/src/pages/__tests__/CommunityPoolManager.test.tsx`
  - 使用 Vitest + Testing Library：
    - Mock `adminService` 的四个接口：
      - `getCommunityPool / batchUpdateCommunityPool / generateTierSuggestions / applyTierSuggestions`
    - 覆盖用例：
      - “应该加载并展示社区池列表”：渲染后看到页面标题和 mock 社区名 `r/ecommerce`
      - “点击生成调级建议时会调用后端并打开抽屉”：点击按钮后，断言 `generateTierSuggestions` 被调用，且出现“调级建议”文案

## 四、测试情况

- 后端单元/集成测试：
  - 模型：
    - `tests/models/test_tier_intelligence_models.py`（新表结构、索引、默认值、插入回读）
  - 服务：
    - `tests/services/test_tier_intelligence_service.py`
      - 空数据指标为 0
      - 构造 posts_hot 后能生成升级建议，结构与阈值逻辑正确
  - 定时任务：
    - `tests/tasks/test_tier_intelligence_task.py`
      - `_generate_daily_tier_suggestions_impl` 正常完成，返回 summary
      - `_apply_high_confidence_suggestions` 能自动更新 tier 并写入审计日志
  - Admin API：
    - `tests/api/test_admin_community_pool.py`
      - 原有列表/审批/拒绝/禁用用例全部通过（已根据新 FK 约束补种必要数据）
      - 新增逻辑（审批时同步更新现有社区 tier）也被覆盖验证
- 前端测试：
  - `npm test -- CommunityPoolManager.test.tsx` 通过
  - 仅在单文件范围内执行，未影响其他页面用例

## 五、后续优化建议

- 前端交互：
  - 在建议抽屉中增加「一键应用」/「批量应用」按钮，调用 `applyTierSuggestions`
  - 支持在列表中行内切换 tier / is_active 后直接调用后端 PATCH 接口 + 写审计日志（与后端 batch API 对齐）
- 性能与体验：
  - `GET /admin/communities/pool` 当前逐个社区调用 `calculate_community_metrics`，后续可考虑：
    - 改为按 subreddit 批量查询 posts_hot/comments，或增加物化视图/缓存
  - 建议列表目前一次性返回全部，可加分页或按优先级 Top N
- 监控与告警：
  - 在现有 monitoring dashboard 中增加「每天生成的调级建议数量、自动应用数量、回滚数量」指标，方便观察自动调级效果。

