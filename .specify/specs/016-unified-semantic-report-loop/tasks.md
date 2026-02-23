# 统一业务闭环架构 - 任务清单

> 此文档用于跟踪 Spec 016 的执行进度，每个任务完成后更新状态。

## 任务状态说明

- `[ ]` - 待开始（Pending）
- `[-]` - 进行中（In Progress）
- `[x]` - 已完成（Completed）
- `[!]` - 已阻塞（Blocked）

---

## Phase 0: 架构重构准备（3天）

### 0.1 定义核心接口（1天）

#### 0.1.1 定义 SemanticProvider 接口
- [ ] 创建 `backend/app/interfaces/semantic_provider.py`
- [ ] 定义 `SemanticProvider` 协议接口
- [ ] 定义 `SemanticMetrics` 数据类
- [ ] 定义 `SemanticLoadStrategy` 枚举
- [ ] 添加完整docstring和类型注解
- [ ] mypy类型检查通过

**验收**：
- [ ] 接口定义清晰，无歧义
- [ ] 所有方法有docstring
- [ ] 类型注解完整

---

#### 0.1.2 定义事件总线
- [ ] 创建 `backend/app/events/semantic_bus.py`
- [ ] 实现 `SemanticEventBus` 类
- [ ] 定义 `Events` 常量类
- [ ] 实现 `get_event_bus()` 工厂函数
- [ ] 添加单元测试

**验收**：
- [ ] 发布-订阅机制可用
- [ ] 异常隔离（单个回调失败不影响其他）
- [ ] 单元测试覆盖率>80%

---

#### 0.1.3 定义监控指标
- [ ] 创建 `backend/app/models/system_health.py`
- [ ] 定义 `SystemHealthMetrics` 数据类
- [ ] 定义 `Degradation` 数据类
- [ ] 文档化各指标含义和阈值

**验收**：
- [ ] 覆盖5大层次（语义/标注/社区/分析/报告）
- [ ] 每个指标有清晰定义

---

### 0.2 建立测试基线（1.5天）

#### 0.2.1 语义层基线测试
- [ ] 创建 `backend/tests/baseline/test_semantic_loader.py`
- [ ] 测试当前SemanticLoader可正常加载
- [ ] 测试DB加载成功
- [ ] 测试YAML加载成功
- [ ] 测试缓存机制

**验收**：
- [ ] 所有测试通过
- [ ] 覆盖核心路径

---

#### 0.2.2 分析引擎基线测试
- [ ] 创建 `backend/tests/baseline/test_analysis_engine.py`
- [ ] 测试社区选择逻辑
- [ ] 测试数据采集流程
- [ ] 测试信号提取（pain/competitors/opportunities）
- [ ] 测试结果组装

**验收**：
- [ ] 分析引擎基础流程可用
- [ ] 输出结构稳定

---

#### 0.2.3 报告生成基线测试
- [ ] 创建 `backend/tests/baseline/test_report_service.py`
- [ ] 测试 technical 模式报告生成
- [ ] 测试 market 模式报告生成（如已实现）
- [ ] 测试报告导出（JSON/Markdown/PDF）

**验收**：
- [ ] 报告生成成功率100%
- [ ] 输出格式符合预期

---

### 0.3 设计事件Schema（0.5天）

- [ ] 创建 `docs/events-schema.md`
- [ ] 定义 `lexicon.updated` 事件
- [ ] 定义 `candidate.approved` 事件
- [ ] 定义 `report.completed` 事件
- [ ] 定义 `tier.adjusted` 事件
- [ ] 文档化载荷结构和订阅者

**验收**：
- [ ] 事件Schema清晰
- [ ] 载荷结构有JSON示例

---

## Phase 1: 语义层解耦（5天）

### 1.1 实现 RobustSemanticLoader（2天）

#### 1.1.1 核心类实现
- [ ] 创建 `backend/app/services/semantic/robust_loader.py`
- [ ] 实现 `__init__` 方法
- [ ] 实现 `async load()` 方法
- [ ] 实现 `async reload()` 方法
- [ ] 实现 `async _load_from_db()` 方法
- [ ] 实现 `_load_from_yaml()` 方法
- [ ] 实现 `_is_cache_valid()` 方法

**验收**：
- [ ] 三种策略都可用（DB_ONLY/FALLBACK/YAML_ONLY）
- [ ] TTL缓存生效

---

#### 1.1.2 降级逻辑
- [ ] 实现DB失败→YAML降级
- [ ] 添加降级日志
- [ ] 统计降级次数

**验收**：
- [ ] DB不可用时自动降级
- [ ] 日志清晰记录降级原因

---

#### 1.1.3 指标统计
- [ ] 实现 `async get_metrics()` 方法
- [ ] 统计 db_hits
- [ ] 统计 yaml_fallbacks
- [ ] 统计 cache_hit_rate
- [ ] 统计 load_latency_p50/p95

**验收**：
- [ ] 指标准确统计
- [ ] get_metrics() 返回正确数据

---

#### 1.1.4 事件集成
- [ ] 订阅 `lexicon.updated` 事件
- [ ] 实现 `async _on_lexicon_updated()` 回调
- [ ] 测试事件触发reload

**验收**：
- [ ] 事件触发成功reload
- [ ] 30秒内缓存刷新

---

#### 1.1.5 单元测试
- [ ] 创建 `backend/tests/services/test_robust_semantic_loader.py`
- [ ] 测试DB加载
- [ ] 测试YAML降级
- [ ] 测试缓存机制
- [ ] 测试指标统计
- [ ] Mock DB测试

**验收**：
- [ ] 单元测试覆盖率>85%
- [ ] 所有测试通过

---

### 1.2 重构 TextClassifier（1天）

#### 1.2.1 依赖注入改造
- [ ] 修改 `backend/app/services/text_classifier.py`
- [ ] 构造函数接受 `SemanticProvider` 参数
- [ ] 使用 `await provider.load()` 获取lexicon
- [ ] 删除直接依赖 `SemanticLoader` 的代码

**验收**：
- [ ] 构造函数签名正确
- [ ] 依赖接口而非实现

---

#### 1.2.2 调用点更新
- [ ] 更新 `backend/app/services/labeling/comments_labeling.py`
- [ ] 更新 `backend/app/services/analysis/pain_cluster.py`
- [ ] 更新 `backend/app/tasks/comments_task.py`
- [ ] 创建 `get_semantic_provider()` 工厂函数

**验收**：
- [ ] 所有调用点使用依赖注入
- [ ] 工厂函数可用

---

#### 1.2.3 单元测试
- [ ] 创建 `MockSemanticProvider`
- [ ] 更新 `backend/tests/services/test_text_classifier.py`
- [ ] 使用Mock测试分类逻辑

**验收**：
- [ ] 单元测试通过（使用Mock）
- [ ] 回归测试通过

---

### 1.3 重构 SemanticScorer（1天）

#### 1.3.1 依赖注入改造
- [ ] 修改 `backend/app/services/semantic/semantic_scorer.py`
- [ ] 构造函数接受 `SemanticProvider` 参数
- [ ] 使用 `await provider.load()` 获取lexicon

**验收**：
- [ ] 依赖注入完成
- [ ] 评分逻辑不变

---

#### 1.3.2 脚本更新
- [ ] 更新 `backend/scripts/score_with_semantic.py`
- [ ] 传入 `semantic_provider` 参数

**验收**：
- [ ] 脚本可正常运行
- [ ] 评分结果与旧版一致

---

#### 1.3.3 单元测试
- [ ] 更新 `backend/tests/services/test_semantic_scorer.py`
- [ ] 使用MockProvider测试

**验收**：
- [ ] 单元测试通过
- [ ] 分层评分准确

---

### 1.4 集成事件总线（0.5天）

#### 1.4.1 触发点集成
- [ ] 修改 `backend/app/repositories/semantic_candidate_repository.py`
- [ ] 在 `approve()` 方法中发布事件
- [ ] 事件载荷包含 term_id / canonical

**验收**：
- [ ] approve()后成功触发事件
- [ ] 事件载荷正确

---

#### 1.4.2 订阅点集成
- [ ] SemanticLoader订阅 `lexicon.updated`
- [ ] TierIntelligence订阅 `candidate.approved`（可选）
- [ ] 测试事件通知

**验收**：
- [ ] 事件通知成功
- [ ] 回调函数正常执行

---

### 1.5 添加监控API（0.5天）

#### 1.5.1 实现接口
- [ ] 创建 `backend/app/api/admin/metrics.py`
- [ ] 实现 `GET /api/admin/metrics/semantic`
- [ ] 返回 `SemanticMetrics` 对象

**验收**：
- [ ] API可访问
- [ ] 返回正确指标

---

#### 1.5.2 权限控制
- [ ] 添加管理员权限检查
- [ ] 测试非管理员访问（应403）

**验收**：
- [ ] 仅管理员可访问
- [ ] 权限控制正确

---

## Phase 2: 主线集成（7天）

### 2.1 修复 report_service.py（2天）

#### 2.1.1 启用T1MarketAgent
- [ ] 修改 `backend/app/services/report_service.py`
- [ ] 启用 `_build_t1_market_report_md()` 函数
- [ ] 修复空指针检查（insights/sources可能为None）
- [ ] 添加异常处理（LLM失败时降级）

**验收**：
- [ ] T1MarketAgent可被调用
- [ ] 空指针安全
- [ ] 异常有降级

---

#### 2.1.2 配置简化
- [ ] 废弃 `ENABLE_MARKET_REPORT` / `ENABLE_UNIFIED_LEXICON` / `ENABLE_LLM_SUMMARY`
- [ ] 统一到 `REPORT_QUALITY_LEVEL=basic|standard|premium`
- [ ] 更新 `.env.example`
- [ ] 更新配置文档

**验收**：
- [ ] 配置统一
- [ ] 文档更新

---

#### 2.1.3 模式路由
- [ ] basic: 规则引擎 + 模板
- [ ] standard: 语义库 + 模板
- [ ] premium: 语义库 + LLM
- [ ] 测试三种模式

**验收**：
- [ ] 三种模式都可用
- [ ] 降级路径清晰

---

### 2.2 重构 AnalysisEngine（2天）

#### 2.2.1 SignalExtractor改造
- [ ] 修改 `backend/app/services/analysis/signal_extractor.py`
- [ ] 查询 `content_labels` 而非关键词匹配
- [ ] 实现批量查询（避免N+1）

**验收**：
- [ ] 使用DB查询
- [ ] 不再有硬编码关键词

---

#### 2.2.2 pain_points提取
- [ ] 实现 `async extract_pain_points(db, post_ids)`
- [ ] 批量查询 `ContentLabel.category==PAIN`
- [ ] 按aspect聚合

**验收**：
- [ ] 批量查询高效
- [ ] 输出结构与旧版兼容

---

#### 2.2.3 competitors提取
- [ ] 实现 `async extract_competitors(db, post_ids)`
- [ ] 查询 `ContentEntity.entity_type==BRAND`
- [ ] 统计mentions

**验收**：
- [ ] 品牌识别准确
- [ ] 统计正确

---

#### 2.2.4 单元测试
- [ ] 更新 `backend/tests/services/test_analysis_engine.py`
- [ ] Mock DB查询
- [ ] 测试批量查询逻辑

**验收**：
- [ ] 单元测试通过
- [ ] 回归测试通过

---

### 2.3 PainCluster改造（1天）

#### 2.3.1 基于DB聚合
- [ ] 修改 `backend/app/services/analysis/pain_cluster.py`
- [ ] SQL聚合按aspect
- [ ] 采样top 5评论（按score排序）

**验收**：
- [ ] 基于DB聚合
- [ ] 采样逻辑正确

---

#### 2.3.2 输出兼容性
- [ ] 输出 `PainCluster` 对象
- [ ] 包含 topic / size / aspects / sample_comments

**验收**：
- [ ] 输出结构与旧版兼容
- [ ] 下游消费无影响

---

### 2.4 LLM集成（1.5天）

#### 2.4.1 Prompt模板设计
- [ ] 设计战场画像Prompt
- [ ] 设计用户之声Prompt
- [ ] 设计机会卡Prompt
- [ ] 文档化Prompt模板

**验收**：
- [ ] Prompt模板清晰
- [ ] 有Few-shot examples

---

#### 2.4.2 实现LLM调用
- [ ] 修改 `backend/app/services/report/t1_market_agent.py`
- [ ] 实现 `async _generate_battlefield_with_llm()`
- [ ] 实现 `async _refine_user_voice_with_llm()`
- [ ] 实现 `async _generate_opportunity_card_with_llm()`

**验收**：
- [ ] LLM调用成功
- [ ] 返回格式正确

---

#### 2.4.3 降级策略
- [ ] 实现 `_generate_battlefield_template()` 降级
- [ ] 实现 `_refine_user_voice_template()` 降级
- [ ] 实现 `_generate_opportunity_card_template()` 降级
- [ ] 记录降级到 `Degradation`

**验收**：
- [ ] LLM失败时降级到模板
- [ ] 降级有日志

---

#### 2.4.4 人工review
- [ ] 生成5份premium报告
- [ ] 人工review内容质量
- [ ] 调整Prompt（如需要）

**验收**：
- [ ] 报告内容可读
- [ ] 策略建议合理

---

### 2.5 端到端测试（0.5天）

#### 2.5.1 实现E2E测试
- [ ] 创建 `backend/tests/e2e/test_unified_pipeline.py`
- [ ] 测试 POST /api/analyze → GET /api/report
- [ ] 验证报告结构（4张卡片/战场/痛点/机会）
- [ ] 验证置信度 >= 0.7

**验收**：
- [ ] E2E测试通过
- [ ] 报告对齐 `t1价值的报告.md`

---

## Phase 3: 后台闭环（5天）

### 3.1 主动社区发现（2天）

#### 3.1.1 实现任务
- [ ] 创建 `backend/app/tasks/discovery_task.py`
- [ ] 实现 `async semantic_community_discovery()`
- [ ] 从语义库提取L1品牌词（top 20）
- [ ] 构造Reddit搜索query
- [ ] 初始语义评分
- [ ] 写入community_pool

**验收**：
- [ ] 任务可手动触发
- [ ] 发现至少10个候选社区

---

#### 3.1.2 Celery定时配置
- [ ] 修改 `backend/app/core/celery_app.py`
- [ ] 添加 `semantic-discovery-weekly` 任务
- [ ] 配置 crontab（每周日凌晨2点）

**验收**：
- [ ] Celery Beat调度成功
- [ ] 任务按时执行

---

### 3.2 强化T1/T2门槛（1天）

#### 3.2.1 修改阈值
- [ ] 修改 `backend/app/services/tier_intelligence.py`
- [ ] T1增加 `min_l1_coverage=0.50` / `min_l4_density=0.30`
- [ ] T2增加 `min_l1_coverage=0.30` / `min_l4_density=0.20`

**验收**：
- [ ] 阈值修改生效
- [ ] T1社区质量提升

---

#### 3.2.2 判定逻辑
- [ ] 修改 `should_promote_to_t1()` 函数
- [ ] 修改 `should_promote_to_t2()` 函数
- [ ] 测试判定逻辑

**验收**：
- [ ] 判定逻辑正确
- [ ] 测试通过

---

#### 3.2.3 人工验证
- [ ] 抽检10个T1社区
- [ ] 验证L1覆盖率 >= 50%
- [ ] 验证L4痛点密度 >= 30%

**验收**：
- [ ] T1社区质量符合预期

---

### 3.3 候选词差异化（1天）

#### 3.3.1 实现差异化逻辑
- [ ] 修改 `backend/app/services/semantic/candidate_extractor.py`
- [ ] T1: min_frequency=10, 优先L1/L4
- [ ] T2: min_frequency=5, 优先L2/L3
- [ ] T3: min_frequency=3, 边界探索

**验收**：
- [ ] 不同tier使用不同阈值
- [ ] 提炼层级有差异

---

#### 3.3.2 测试
- [ ] 测试T1候选词提取
- [ ] 测试T2候选词提取
- [ ] 测试T3候选词提取

**验收**：
- [ ] 频次阈值正确
- [ ] 层级偏好正确

---

### 3.4 报告质量反馈（1天）

#### 3.4.1 DB变更
- [ ] 迁移脚本：`ALTER TABLE reports ADD COLUMN quality_rating FLOAT`
- [ ] 迁移脚本：`ALTER TABLE reports ADD COLUMN user_feedback TEXT`
- [ ] 运行迁移

**验收**：
- [ ] 字段添加成功
- [ ] 无数据丢失

---

#### 3.4.2 打分接口
- [ ] 创建 `POST /api/reports/{report_id}/rate`
- [ ] 接受 rating (1.0-5.0) 和 feedback
- [ ] 发布 `report.completed` 事件

**验收**：
- [ ] 打分接口可用
- [ ] 事件触发成功

---

#### 3.4.3 反馈处理
- [ ] 创建 `backend/app/services/quality_feedback.py`
- [ ] 订阅 `report.completed` 事件
- [ ] 低分报告提高相关候选词优先级

**验收**：
- [ ] 反馈处理逻辑可用
- [ ] 候选词优先级调整

---

## Phase 4: 监控与优化（5天）

### 4.1 可观测性仪表盘（2天）

#### 4.1.1 实现API
- [ ] 创建 `backend/app/api/admin/dashboard.py`
- [ ] 实现 `GET /api/admin/dashboard/pipeline-health`
- [ ] 聚合5大层次指标

**验收**：
- [ ] API返回完整指标
- [ ] 数据准确

---

#### 4.1.2 降级日志API
- [ ] 实现 `GET /api/admin/dashboard/degradation-log`
- [ ] 返回最近24小时降级记录

**验收**：
- [ ] 降级记录完整
- [ ] 时间排序正确

---

#### 4.1.3 前端展示（可选）
- [ ] 创建仪表盘页面（如有UI框架）
- [ ] 展示5大层次指标
- [ ] 展示降级日志

**验收**：
- [ ] 前端可视化清晰

---

### 4.2 性能优化（1.5天）

#### 4.2.1 Redis缓存
- [ ] 缓存 UnifiedLexicon 对象（30分钟TTL）
- [ ] 缓存社区评分（6小时TTL）
- [ ] 测试缓存命中率

**验收**：
- [ ] Redis缓存生效
- [ ] 命中率 > 80%

---

#### 4.2.2 批量查询优化
- [ ] 优化 content_labels 查询（in()）
- [ ] 优化 content_entities 查询
- [ ] 测试查询性能

**验收**：
- [ ] 查询次数显著减少
- [ ] 响应时间缩短

---

#### 4.2.3 索引优化
- [ ] 添加 `idx_community_semantic_score`
- [ ] 添加 `idx_content_labels_category_aspect`
- [ ] 测试索引效果

**验收**：
- [ ] 索引添加成功
- [ ] 查询使用索引（EXPLAIN分析）

---

### 4.3 降级策略验证（1天）

#### 4.3.1 语义库DB故障
- [ ] 测试：关闭DB连接
- [ ] 验证：YAML降级成功
- [ ] 验证：日志清晰

**验收**：
- [ ] 降级测试通过

---

#### 4.3.2 SemanticScorer超时
- [ ] Mock超时
- [ ] 验证：使用历史缓存
- [ ] 验证：降级标记

**验收**：
- [ ] 降级测试通过

---

#### 4.3.3 LLM API超时
- [ ] Mock超时
- [ ] 验证：模板降级
- [ ] 验证：Degradation记录

**验收**：
- [ ] 降级测试通过

---

### 4.4 压力测试（0.5天）

#### 4.4.1 编写Locust脚本
- [ ] 创建 `backend/tests/performance/locustfile.py`
- [ ] 模拟100并发用户
- [ ] 混合读写请求

**验收**：
- [ ] Locust脚本可运行

---

#### 4.4.2 执行测试
- [ ] 运行100并发10分钟
- [ ] 记录成功率/P95延迟/缓存命中率
- [ ] 分析瓶颈

**验收**：
- [ ] 成功率 >= 95%
- [ ] P95延迟 < 5s
- [ ] 缓存命中率 > 90%

---

## 总体验收（上线标准）

### 功能完整性
- [ ] HTTP主线可稳定生成T1级市场报告
- [ ] 语义库可自动发现社区+提取候选词+审核回流
- [ ] 所有降级路径可用且有监控

### 性能指标
- [ ] 语义库DB命中率 > 95%
- [ ] 报告生成成功率 > 95%（premium模式）
- [ ] 端到端响应时间 < 5s（P95）
- [ ] 缓存命中率 > 90%

### 鲁棒性
- [ ] 模拟故障场景测试通过（DB/API/连接池）
- [ ] 压力测试100并发成功率 > 95%
- [ ] 所有异常有日志和告警

### 可观测性
- [ ] 监控仪表盘覆盖5大层次指标
- [ ] 关键指标有告警阈值配置
- [ ] 可追踪完整请求链路

### 文档完整性
- [ ] Spec文档完整（spec.md/design.md/plan.md/tasks.md）
- [ ] 架构指南编写（`docs/unified-architecture-guide.md`）
- [ ] 运维手册编写（`docs/ops/monitoring-playbook.md`）
- [ ] 接口有完整的docstring和类型注解

---

## 进度追踪

| Phase | 开始日期 | 完成日期 | 状态 | 备注 |
|-------|---------|---------|------|------|
| Phase 0 | - | - | 待开始 | |
| Phase 1 | - | - | 待开始 | |
| Phase 2 | - | - | 待开始 | |
| Phase 3 | - | - | 待开始 | |
| Phase 4 | - | - | 待开始 | |

---

## 阻塞问题追踪

> 记录执行过程中遇到的阻塞问题

| 日期 | 问题描述 | 影响任务 | 解决方案 | 状态 |
|------|---------|---------|---------|------|
| - | - | - | - | - |

---

## 变更日志

| 日期 | 变更内容 | 变更原因 | 影响评估 |
|------|---------|---------|---------|
| 2025-11-23 | 初始版本 | 创建任务清单 | - |
