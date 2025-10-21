# Tasks: 数据与算法双轨优化

**Feature ID**: 005-data-quality-optimization  
**Plan**: [plan.md](./plan.md)  
**Created**: 2025-10-16  
**Status**: IN_PROGRESS

---

## Task Overview

| Phase | Tasks | Estimated Time | Status |
|-------|-------|----------------|--------|
| Phase 0: 冷热分层基础 | 5 tasks | 已完成 | ✅ COMPLETE |
| Phase 1: 数据基础设施 | 8 tasks | 3 天 | ✅ COMPLETE |
| Phase 2: 分析引擎改造 | 10 tasks | 6 天 | ✅ COMPLETE |
| Phase 3: 评测与优化 | 6 tasks | 9 天 | ✅ COMPLETE (编码) |
| P0: 测试基础稳固 | 4 tasks | 1 天 | ✅ COMPLETE |
| Phase 4: 迭代与延伸 | 6 tasks | 12 天 | ⏳ NOT_STARTED |
| **Total** | **39 tasks** | **31 天** | - |

---

## Phase 0: 冷热分层基础设施 ✅ COMPLETE

**目标**: 建立增量累积 + 实时热缓存的混合架构  
**完成时间**: 2025-10-16

### T0.1: 数据库架构设计 ✅
**Status**: COMPLETE  
**Estimated**: 1h  
**Actual**: 1h

**Checklist**:
- [x] 设计 posts_raw（冷库）表结构
- [x] 设计 posts_hot（热缓存）表结构
- [x] 设计 posts_latest 物化视图
- [x] 设计水位线字段（community_cache）
- [x] 创建 SQL 迁移脚本

**Output**: `backend/migrations/001_cold_hot_storage.sql`

---

### T0.2: SQLAlchemy 模型创建 ✅
**Status**: COMPLETE  
**Estimated**: 30min  
**Actual**: 45min

**Checklist**:
- [x] 创建 PostRaw 模型
- [x] 创建 PostHot 模型
- [x] 修复 metadata 保留字冲突（改为 extra_data）
- [x] 扩展 CommunityCache 模型（添加水位线字段）

**Output**: `backend/app/models/posts_storage.py`

---

### T0.3: 增量抓取服务实现 ✅
**Status**: COMPLETE  
**Estimated**: 2h  
**Actual**: 3h

**Checklist**:
- [x] 实现 IncrementalCrawler 类
- [x] 实现水位线机制（_get_watermark）
- [x] 实现双写逻辑（_dual_write）
- [x] 实现冷库 upsert（_upsert_to_cold_storage）
- [x] 实现热缓存 upsert（_upsert_to_hot_cache）
- [x] 修复 Unix 时间戳转换问题

**Output**: `backend/app/services/incremental_crawler.py`

---

### T0.4: Celery 任务改造 ✅
**Status**: COMPLETE  
**Estimated**: 30min  
**Actual**: 30min

**Checklist**:
- [x] 创建增量抓取任务（crawl_seed_communities_incremental）
- [x] 更新 Celery Beat 配置（每 2 小时）
- [x] 保留旧任务（兼容性）

**Output**: `backend/app/tasks/crawler_task.py`, `backend/app/core/celery_app.py`

---

### T0.5: 自检测试与部分抓取 ✅
**Status**: COMPLETE  
**Estimated**: 1h  
**Actual**: 1.5h

**Checklist**:
- [x] 修复 4 个关键问题（metadata、created_at、insert、CommunityCache）
- [x] 测试增量抓取（2 个社区）
- [x] 部分抓取（26/102 社区，3,075 条帖子）
- [x] 验证冷热分层数据一致性

**Output**: `reports/增量抓取测试报告.md`

---

## Phase 1: 数据基础设施完善 ✅ COMPLETE

**目标**: 完成社区抓取、监控埋点、社区扩容、调度改造
**完成时间**: 2025-10-19

### T1.1: 完成剩余社区抓取 ✅
**Status**: COMPLETE
**Assignee**: AI Agent
**Estimated**: 4h
**Actual**: 2h
**Completed**: 2025-10-19 02:03

**Description**: 完成剩余 76 个社区的首次抓取

**Checklist**:
- [x] 启动完整抓取任务（200 个社区）
- [x] 监控抓取进度
- [x] 记录失败社区（14 个）
- [x] 验证冷热分层数据一致性
- [x] 更新 community_cache 统计字段

**Results**:
- 冷库：16,881 条帖子（超额 211%）
- 热缓存：16,869 条帖子（超额 211%）
- 成功率：93.0% (186/200)
- 失败社区：14 个（已记录）

**Output**: `reports/phase-log/T1.1-crawl-20251019-020351.json`

---

### T1.2: 扩展 community_cache 监控字段 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16

**Checklist**:
- [x] 创建数据库迁移脚本
- [x] 添加 empty_hit, success_hit, failure_hit 字段
- [x] 添加 avg_valid_posts, quality_tier 字段
- [x] 执行迁移
- [x] 验证字段创建成功

**Output**: `backend/alembic/versions/20251016_000005_extend_community_cache_monitoring.py`

**SQL**:
```sql
ALTER TABLE community_cache 
ADD COLUMN empty_hit INTEGER DEFAULT 0,
ADD COLUMN success_hit INTEGER DEFAULT 0,
ADD COLUMN failure_hit INTEGER DEFAULT 0,
ADD COLUMN avg_valid_posts NUMERIC(5,2) DEFAULT 0,
ADD COLUMN quality_tier VARCHAR(20) DEFAULT 'normal';
```

**Acceptance Criteria**:
- 所有字段创建成功
- 现有数据不受影响

---

### T1.3: 创建 crawl_metrics 监控表 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16

**Checklist**:
- [x] 设计表结构（metric_date, cache_hit_rate, valid_posts_24h 等）
- [x] 创建迁移脚本
- [x] 执行迁移
- [x] 创建索引（metric_date, metric_hour）
- [x] 验证表创建成功

**Output**: `backend/alembic/versions/20251016_000006_create_crawl_metrics_table.py`

---

### T1.4: 改造 IncrementalCrawler 埋点 ✅
**Status**: COMPLETE
**Completed**: 2025-10-19

**Checklist**:
- [x] 记录成功抓取（有帖子）
- [x] 记录空结果（0 条帖子）
- [x] 记录失败（API 错误）
- [x] 更新 community_cache 统计字段
- [x] 写入 crawl_metrics 表（每小时）
- [x] 测试埋点逻辑

**Output**:
- `backend/app/services/incremental_crawler.py` - 新增 `_record_crawl_metrics()` 方法
- `backend/alembic/versions/20251019_000013_add_unique_constraint_to_crawl_metrics.py` - 唯一约束迁移

**实现细节**:
- 成功抓取：记录 successful_crawls, total_new_posts, total_updated_posts, total_duplicates
- 空结果：记录 empty_crawls, 更新 community_cache.empty_hit
- 失败：记录 failed_crawls, 更新 community_cache.failure_hit
- 每小时汇总：按 (metric_date, metric_hour) 聚合统计

---

### T1.5: 社区池扩容到 300 个 ⏸️
**Status**: DEFERRED
**Assignee**: AI Agent
**Estimated**: 3h
**Dependencies**: T1.1
**Note**: 当前 201 个社区已满足需求，延期至后续阶段

**Description**: 扩充社区池并添加类目标签

**Checklist**:
- [ ] 从现有 102 个社区筛选 Top 100
- [ ] 研究并补充 200 个新社区
- [ ] 添加类目标签（tech/business/lifestyle/finance）
- [ ] 限制同类目 ≤5 个
- [ ] 更新 community_pool 表
- [ ] 验证社区质量

**Acceptance Criteria**:
- 社区池：300 个
- 类目分布均衡
- 每个社区有类目标签

---

### T1.6: 创建黑名单配置 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16

**Checklist**:
- [x] 创建 config/community_blacklist.yaml
- [x] 添加黑名单社区（20 个）
- [x] 添加降权关键词
- [x] 扩展 community_pool 表（is_blacklisted, blacklist_reason）
- [x] 实现黑名单加载逻辑
- [x] 测试黑名单过滤

**Output**:
- `config/community_blacklist.yaml`
- `backend/app/services/blacklist_loader.py`

---

### T1.7: 实现分级调度策略 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16

**Checklist**:
- [x] 计算社区质量分（avg_valid_posts）
- [x] 分级：Tier 1（Top 20）、Tier 2（次优 40）、Tier 3（长尾）
- [x] 更新 Celery Beat 配置（2h/6h/24h）
- [x] 创建 crawl_tier 任务
- [x] 测试分级调度

**Output**: `backend/app/services/tiered_scheduler.py`

---

### T1.8: 实现精准补抓任务 ✅
**Status**: COMPLETE
**Completed**: 2025-10-19

**Checklist**:
- [x] 创建补抓任务（crawl_low_quality_communities）
- [x] 查询条件：last_crawled_at > 8h 且 avg_valid_posts < 50
- [x] 失败回写 empty_hit
- [x] 添加到 Celery Beat（每 4 小时）
- [x] 测试补抓逻辑

**Output**:
- `backend/app/tasks/crawler_task.py` L451-545
- `backend/app/core/celery_app.py` L122-127

---

## Phase 2: 分析引擎改造 ✅ COMPLETE

**目标**: 样本检查、规则优化、去重聚合
**完成时间**: 2025-10-16

### T2.1: 实现样本下限检查 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 2h
**Actual**: 2h

**Description**: 分析前检查样本量是否 ≥1500

**Checklist**:
- [x] 实现 check_sample_size 函数
- [x] 从热缓存读取样本量
- [x] 从冷库补读（最近 30 天）
- [x] 样本不足时触发补抓
- [x] 集成到分析引擎
- [x] 测试样本检查逻辑

**Output**: `backend/app/services/analysis/sample_guard.py`

---

### T2.2: 实现关键词补抓任务 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 3h
**Actual**: 3h

**Description**: 使用 Reddit Search API 按关键词抓取

**Checklist**:
- [x] 实现 keyword_crawl 函数
- [x] 提取产品描述关键词
- [x] 调用 Reddit Search API
- [x] 标记来源类型（cache/search）
- [x] 写入冷库
- [x] 测试关键词抓取

**Output**: `backend/app/services/analysis/keyword_crawler.py`

---

### T2.3: 创建评分规则配置 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 2h
**Actual**: 2h

**Description**: 创建正负关键词配置文件

**Checklist**:
- [x] 创建 config/scoring_rules.yaml
- [x] 添加正例关键词（need, urgent, looking for）
- [x] 添加负例关键词（giveaway, for fun, just sharing）
- [x] 添加语义否定模式（not interested, don't need）
- [x] 实现配置加载逻辑
- [x] 测试配置热更新

**Output**: `config/scoring_rules.yaml`

---

### T2.4: 改造 OpportunityScorer ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 3h
**Actual**: 3h

**Description**: 实现正负关键词对冲评分

**Checklist**:
- [x] 加载评分规则配置
- [x] 实现正例关键词评分
- [x] 实现负例关键词对冲
- [x] 实现语义否定检测
- [x] 确保分数不低于 0
- [x] 测试评分逻辑

**Output**: `backend/app/services/analysis/opportunity_scorer.py`

---

### T2.5: 实现文本清洗函数 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 1h
**Actual**: 1h

**Description**: 去除 URL、代码块、引用块

**Checklist**:
- [x] 实现 clean_text 函数
- [x] 去除 URL（正则）
- [x] 去除代码块（```...```）
- [x] 去除引用块（> ...）
- [x] 测试清洗效果

**Output**: `backend/app/services/analysis/text_cleaner.py`

---

### T2.6: 实现句级评分 + 上下文窗口 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 2h
**Actual**: 2h

**Description**: 取当前句 + 前后各 1 句窗口评分

**Checklist**:
- [x] 实现句子分割
- [x] 实现 score_with_context 函数
- [x] 窗口大小：±1 句
- [x] 集成到评分器
- [x] 测试上下文窗口

**Output**: `backend/app/services/analysis/text_cleaner.py` (score_with_context)

---

### T2.7: 创建模板配置 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 2h
**Actual**: 2h

**Description**: 创建正向模板和反模板配置

**Checklist**:
- [x] 创建 config/scoring_templates.yaml
- [x] 添加正向模板（金额、时间、数量）
- [x] 添加反模板（招聘、抽奖、宣发）
- [x] 实现模板匹配逻辑
- [x] 测试模板加成/降权

**Output**: `config/scoring_templates.yaml`

---

### T2.8: 集成模板评分 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 2h
**Actual**: 2h

**Description**: 将模板评分集成到 OpportunityScorer

**Checklist**:
- [x] 加载模板配置
- [x] 实现正向模板匹配
- [x] 实现反模板匹配
- [x] 计算模板加成/降权
- [x] 测试模板评分

**Output**: `backend/app/services/analysis/template_matcher.py`

---

### T2.9: 实现 MinHash 去重 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 3h
**Actual**: 3h

**Description**: 使用 MinHash + LSH 去重

**Checklist**:
- [x] 安装 datasketch 库
- [x] 实现 deduplicate_posts 函数
- [x] 相似度阈值：0.85
- [x] 主贴保留，重复项聚合
- [x] 记录证据计数
- [x] 测试去重效果

**Output**: `backend/app/services/analysis/deduplicator.py`

---

### T2.10: 集成去重到分析引擎 ✅
**Status**: COMPLETE
**Completed**: 2025-10-16
**Estimated**: 2h
**Actual**: 2h

**Description**: 在分析前进行去重

**Checklist**:
- [x] 在分析引擎中调用去重
- [x] 记录 duplicate_ids
- [x] 记录 evidence_count
- [x] 更新分析结果结构
- [x] 测试去重集成

**Output**: `backend/app/services/analysis_engine.py` (L972: deduplicate_posts)

---

## Phase 3: 评测与优化 ✅ COMPLETE (编码部分)

**目标**: 抽样标注、阈值校准、仪表盘、报告强化
**完成时间**: 2025-10-20
**备注**: T3.1.5 人工标注和 T3.2 阈值调参需要人工执行

### T3.1: 抽样标注数据集 ⏸️
**Status**: PARTIAL (4/5 完成)
**Completed**: 2025-10-20 (编码部分)
**Assignee**: AI Agent + User
**Estimated**: 4h
**Actual**: 3h (编码) + 待定 (人工标注)

**Description**: 从冷库抽样 500 条帖子进行人工标注

**Checklist**:
- [x] 从冷库随机抽样 500 条
- [x] 创建标注界面/表格
- [x] 实现标注工作流（LabelingWorkflow）
- [x] 实现 ThresholdOptimizer 类
- [ ] **人工标注：机会/非机会、强/中/弱**（待用户执行）

**Output**:
- `backend/app/services/evaluation/labeling_workflow.py`
- `backend/app/services/evaluation/threshold_optimizer.py`

---

### T3.2: 实现阈值网格搜索 ⏸️
**Status**: DEFERRED
**Assignee**: AI Agent
**Estimated**: 2h
**Dependencies**: T3.1 (需要人工标注数据)

**Description**: 网格搜索最优阈值

**Checklist**:
- [x] 实现 grid_search_threshold 函数
- [x] 阈值范围：0.3-0.9，步长 0.05
- [x] 优化指标：Precision@50, F1
- [ ] **执行首次阈值调参**（需要 T3.1 人工标注完成）
- [ ] 更新配置文件

**Output**: `backend/app/services/evaluation/threshold_optimizer.py`

---

### T3.3: 创建每日跑分脚本 ✅
**Status**: COMPLETE
**Completed**: 2025-10-20
**Estimated**: 3h
**Actual**: 3h

**Description**: 生成每日指标报告

**Checklist**:
- [x] 实现 generate_daily_metrics 函数
- [x] 收集指标（cache_hit_rate, valid_posts_24h, duplicate_rate 等）
- [x] 写入 CSV（reports/daily_metrics/）
- [x] 创建 Celery 定时任务（每日 0 点）
- [x] 测试跑分脚本

**Output**:
- `backend/app/services/metrics/daily_metrics.py`
- `backend/app/tasks/metrics_task.py`

---

### T3.4: 实现红线检查逻辑 ✅
**Status**: COMPLETE
**Completed**: 2025-10-20
**Estimated**: 2h
**Actual**: 2h

**Description**: 检查红线触发条件并自动降级

**Checklist**:
- [x] 实现 check_red_lines 函数
- [x] 红线 1：有效帖子 <1500 → 保守模式
- [x] 红线 2：缓存命中率 <60% → 提升抓取频率
- [x] 红线 3：重复率 >20% → 改进去重
- [x] 红线 4：Precision@50 <0.6 → 提高阈值
- [x] 测试红线触发

**Output**:
- `backend/app/services/metrics/red_line_checker.py`
- `config/deduplication.yaml` (红线阈值配置)

---

### T3.5: 改造报告模版 ✅
**Status**: COMPLETE
**Completed**: 2025-10-20
**Estimated**: 3h
**Actual**: 3h

**Description**: 添加行动位到报告模版

**Checklist**:
- [x] 创建 OpportunityReport 类
- [x] 添加 problem_definition 字段
- [x] 添加 evidence_chain 字段（2-3 条）
- [x] 添加 suggested_actions 字段
- [x] 添加 confidence, urgency, product_fit 字段
- [x] 实现 priority 计算（confidence × urgency × product_fit）
- [x] 测试报告生成

**Output**:
- `backend/app/services/reporting/opportunity_report.py`
- `backend/app/schemas/opportunity_signal.py`

---

### T3.6: 集成行动位到 API ✅
**Status**: COMPLETE
**Completed**: 2025-10-20
**Estimated**: 2h
**Actual**: 2h

**Description**: 在 API 和前端展示行动位

**Checklist**:
- [x] 更新分析结果 API
- [x] 返回行动位字段
- [x] 前端展示问题定义
- [x] 前端展示证据链（可点击链接）
- [x] 前端展示建议动作
- [x] 前端展示优先级（星级）
- [x] 测试前后端集成

**Output**:
- `backend/app/api/v1/reports.py` (action_items 字段)
- `frontend/src/components/ActionItemCard.tsx`
- `frontend/src/components/ActionItemsList.tsx`
- `frontend/src/utils/export.ts` (导出功能)

---

## P0: 测试基础稳固 ✅ COMPLETE

**目标**: 修复测试执行超时问题，优化性能
**完成时间**: 2025-10-21
**触发原因**: Phase 3 完成后发现测试超时（>120 秒），需要稳固测试基础再开始 Phase 4

### P0.1: 修复 pytest-asyncio 事件循环冲突 ✅
**Status**: COMPLETE
**Completed**: 2025-10-21
**Estimated**: 1h
**Actual**: 1h

**Description**: 解决 "attached to a different loop" 错误

**Checklist**:
- [x] 添加 session-scoped event_loop fixture
- [x] 正确关闭事件循环
- [x] 测试事件循环修复

**Output**: `backend/tests/conftest.py` (event_loop fixture)

---

### P0.2: 优化去重性能（避免 O(n²) 回退）✅
**Status**: COMPLETE
**Completed**: 2025-10-21
**Estimated**: 2h
**Actual**: 2h

**Description**: 修复 MinHash 未命中时的 O(n²) 全量比对问题

**Checklist**:
- [x] 添加 DeduplicationStats 统计
- [x] 优化 _cluster_posts 逻辑
- [x] 仅对小数据集（≤50）回退全量比对
- [x] 大数据集跳过回退，避免性能灾难
- [x] 测试去重性能

**Output**:
- `backend/app/services/analysis/deduplicator.py` (DeduplicationStats, 优化逻辑)
- `backend/tests/services/test_deduplicator_stats.py`

**Performance**: 500 帖子去重从几十秒 → <1 秒（提升 95%）

---

### P0.3: 优化分析引擎性能 ✅
**Status**: COMPLETE
**Completed**: 2025-10-21
**Estimated**: 1h
**Actual**: 1h

**Description**: 减少数据库查询和 API 调用

**Checklist**:
- [x] 减少社区查询量：50 → 10（80% 减少）
- [x] 减少 Reddit API 调用：100 → 50 条/社区（50% 减少）
- [x] 修复类型转换问题（None 值处理）
- [x] 添加 dedup_stats 到分析结果
- [x] 测试性能优化

**Output**: `backend/app/services/analysis_engine.py`

**Performance**:
- 数据库查询减少 80%
- Reddit API 调用减少 50%

---

### P0.4: 新增快速测试（基于 exa-code 最佳实践）✅
**Status**: COMPLETE
**Completed**: 2025-10-21
**Estimated**: 1h
**Actual**: 1h

**Description**: 添加快速 Mock 测试避免数据库开销

**Checklist**:
- [x] 创建 test_run_analysis_fast_with_mocked_database
- [x] Mock SessionFactory 避免数据库连接
- [x] 使用合成数据验证核心逻辑
- [x] 测试缓存优先架构
- [x] 验证去重统计数据

**Output**: `backend/tests/services/test_analysis_engine.py`

**Performance**: 测试耗时 <1 秒（vs 原版 90 秒）

---

### P0 任务总结

**成果**:
- ✅ 测试通过率：250/250 (100%)
- ✅ 测试执行时间：>120s → 69.58s（提升 42%）
- ✅ 去重性能：500 帖子从几十秒 → <1 秒（提升 95%）
- ✅ 数据库查询：减少 80%
- ✅ Reddit API 调用：减少 50%
- ✅ CI 全部通过（Run #62）

**文档**:
- `reports/phase-log/phase3-vs-phase4-decision-analysis.md`
- `reports/phase-log/test-performance-analysis.md`
- `reports/phase-log/phase3-acceptance-report.md`
- `reports/phase-log/phase4-execution-plan.md`

---

## Phase 4: 迭代与延伸（T+18~30 天）

**目标**: 两周总结、NER、趋势分析、证据图谱

### T4.1: 生成两周迭代总结
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T3.6

**Description**: 复盘社区扩容、规则改造、阈值调整效果

**Checklist**:
- [ ] 收集社区扩容数据（102 → 300）
- [ ] 收集样本量提升数据（3K → 15K+）
- [ ] 收集规则优化数据（Precision@50, F1）
- [ ] 收集红线触发次数
- [ ] 写入 reports/phase-log/phase5-summary.md
- [ ] 规划下一月工作

**Acceptance Criteria**:
- 总结报告已生成
- 下一月计划已制定

---

### T4.2: 实现轻量 NER
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 4h  
**Dependencies**: T4.1

**Description**: 使用 spaCy 或词典+正则提取实体

**Checklist**:
- [ ] 安装 spaCy（en_core_web_sm）
- [ ] 实现 extract_entities 函数
- [ ] 提取产品、功能、受众、行业
- [ ] 集成到评分器
- [ ] 测试 NER 效果

**Acceptance Criteria**:
- 实体提取准确率 ≥70%
- 集成到评分器

---

### T4.3: 实现趋势分析
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: T4.1

**Description**: 输出主题趋势曲线（7/14/30 天）

**Checklist**:
- [ ] 实现 analyze_trends 函数
- [ ] 查询冷库数据（7/14/30 天）
- [ ] 按日期聚合帖子数量
- [ ] 绘制趋势图（matplotlib）
- [ ] 保存到 reports/trends/
- [ ] 测试趋势分析

**Acceptance Criteria**:
- 趋势图生成成功
- 支持 7/14/30 天窗口

---

### T4.4: 实现证据图谱
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 4h  
**Dependencies**: T4.1

**Description**: 构建证据图谱数据结构

**Checklist**:
- [ ] 创建 EvidenceGraph 类
- [ ] 添加机会节点
- [ ] 添加证据节点
- [ ] 添加边（机会 → 证据）
- [ ] 导出 JSON 格式
- [ ] 前端可视化（可选）
- [ ] 测试证据图谱

**Acceptance Criteria**:
- 证据图谱生成成功
- JSON 格式正确

---

### T4.5: 实现实体词典
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: T4.2

**Description**: 建立行业实体词典

**Checklist**:
- [ ] 创建 config/entity_dictionary.yaml
- [ ] 添加产品词典
- [ ] 添加功能词典
- [ ] 添加受众词典
- [ ] 添加行业词典
- [ ] 添加竞品域词库
- [ ] 实现槽位匹配逻辑
- [ ] 测试实体匹配

**Acceptance Criteria**:
- 词典创建成功
- 槽位匹配生效

---

### T4.6: 实现态度极性过滤
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T4.1

**Description**: 定义强负面词库并过滤

**Checklist**:
- [ ] 创建负面词库（doesn't work, hate, terrible）
- [ ] 实现极性检测函数
- [ ] 命中负面词降权/过滤
- [ ] 集成到评分器
- [ ] 测试极性过滤

**Acceptance Criteria**:
- 负面帖子被过滤
- 抱怨不被当成机会

---

## Success Criteria

### 数据层面
- [ ] 可用帖子样本量：3,075 → 15,000+（5 倍提升）
- [ ] 冷库数据：支持 30/90 天历史回溯
- [ ] 热缓存命中率：≥60%
- [ ] 社区池：102 → 300

### 算法层面
- [ ] Precision@50：≥0.6
- [ ] F1 Score：≥0.6
- [ ] 去重率：<20%
- [ ] 阈值校准：每周固化流程

### 系统层面
- [ ] 分析引擎：5 分钟内完成
- [ ] 红线策略：自动降级
- [ ] 仪表盘：每日跑分表
- [ ] 报告行动位：问题定义 + 证据链 + 建议动作 + 优先级

---

## Dependencies Graph

```
Phase 0 (冷热分层) ✅
  └─ T0.1 → T0.2 → T0.3 → T0.4 → T0.5

Phase 1 (数据基础)
  ├─ T1.1 (完成抓取) ← T0.5
  ├─ T1.2 (监控字段) ← T1.1
  ├─ T1.3 (监控表) ← T1.2
  ├─ T1.4 (埋点) ← T1.2, T1.3
  ├─ T1.5 (社区扩容) ← T1.1
  ├─ T1.6 (黑名单) ← T1.5
  ├─ T1.7 (分级调度) ← T1.4
  └─ T1.8 (精准补抓) ← T1.7

Phase 2 (分析引擎)
  ├─ T2.1 (样本检查) ← T1.1
  ├─ T2.2 (关键词补抓) ← T2.1
  ├─ T2.3 (评分配置)
  ├─ T2.4 (评分器) ← T2.3
  ├─ T2.5 (文本清洗)
  ├─ T2.6 (句级评分) ← T2.5
  ├─ T2.7 (模板配置)
  ├─ T2.8 (模板评分) ← T2.4, T2.7
  ├─ T2.9 (去重)
  └─ T2.10 (去重集成) ← T2.9

Phase 3 (评测优化)
  ├─ T3.1 (抽样标注) ← T2.10
  ├─ T3.2 (阈值搜索) ← T3.1
  ├─ T3.3 (每日跑分) ← T1.4
  ├─ T3.4 (红线检查) ← T3.3
  ├─ T3.5 (报告模版) ← T2.10
  └─ T3.6 (行动位集成) ← T3.5

Phase 4 (迭代延伸)
  ├─ T4.1 (两周总结) ← T3.6
  ├─ T4.2 (NER) ← T4.1
  ├─ T4.3 (趋势分析) ← T4.1
  ├─ T4.4 (证据图谱) ← T4.1
  ├─ T4.5 (实体词典) ← T4.2
  └─ T4.6 (极性过滤) ← T4.1
```

---

## Execution Notes

1. **Phase 0** 已完成，可以直接进入 Phase 1
2. **T1.1** 正在进行中，需要完成剩余 76 个社区抓取
3. 所有配置文件应集中存放在 `config/` 目录
4. 所有报告应记录到 `reports/phase-log/`
5. MCP 工具操作超 12 秒需记录到 `reports/`
6. 每个 Phase 完成后需要验证 Success Criteria

