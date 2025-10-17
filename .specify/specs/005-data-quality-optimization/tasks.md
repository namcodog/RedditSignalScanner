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
| Phase 1: 数据基础设施 | 8 tasks | 3 天 | 🔄 IN_PROGRESS |
| Phase 2: 分析引擎改造 | 10 tasks | 6 天 | ⏳ NOT_STARTED |
| Phase 3: 评测与优化 | 6 tasks | 9 天 | ⏳ NOT_STARTED |
| Phase 4: 迭代与延伸 | 6 tasks | 12 天 | ⏳ NOT_STARTED |
| **Total** | **35 tasks** | **30 天** | - |

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

## Phase 1: 数据基础设施完善（T+0~3 天）

**目标**: 完成社区抓取、监控埋点、社区扩容、调度改造

### T1.1: 完成剩余社区抓取 🔄
**Status**: IN_PROGRESS  
**Assignee**: AI Agent  
**Estimated**: 4h  
**Dependencies**: T0.5

**Description**: 完成剩余 76 个社区的首次抓取

**Checklist**:
- [ ] 启动完整抓取任务（101 个社区）
- [ ] 监控抓取进度（每 30 分钟检查）
- [ ] 记录失败社区（空结果/API 错误）
- [ ] 验证冷热分层数据一致性
- [ ] 更新 community_cache 统计字段

**Commands**:
```bash
python3 scripts/run-incremental-crawl.py
```

**Acceptance Criteria**:
- 冷库：~8,000 条帖子
- 热缓存：~8,000 条帖子
- 成功率：≥90%
- 失败社区已记录

---

### T1.2: 扩展 community_cache 监控字段
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 1h  
**Dependencies**: T1.1

**Description**: 添加监控统计字段到 community_cache 表

**Checklist**:
- [ ] 创建数据库迁移脚本
- [ ] 添加 empty_hit, success_hit, failure_hit 字段
- [ ] 添加 avg_valid_posts, quality_tier 字段
- [ ] 执行迁移
- [ ] 验证字段创建成功

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

### T1.3: 创建 crawl_metrics 监控表
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 1h  
**Dependencies**: T1.2

**Description**: 创建爬虫监控指标表

**Checklist**:
- [ ] 设计表结构（metric_date, cache_hit_rate, valid_posts_24h 等）
- [ ] 创建迁移脚本
- [ ] 执行迁移
- [ ] 创建索引（metric_date, metric_hour）
- [ ] 验证表创建成功

**Acceptance Criteria**:
- crawl_metrics 表创建成功
- 索引创建成功

---

### T1.4: 改造 IncrementalCrawler 埋点
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T1.2, T1.3

**Description**: 在抓取器中添加监控埋点

**Checklist**:
- [ ] 记录成功抓取（有帖子）
- [ ] 记录空结果（0 条帖子）
- [ ] 记录失败（API 错误）
- [ ] 更新 community_cache 统计字段
- [ ] 写入 crawl_metrics 表（每小时）
- [ ] 测试埋点逻辑

**Acceptance Criteria**:
- 每次抓取都有统计记录
- community_cache 字段正确更新
- crawl_metrics 每小时有记录

---

### T1.5: 社区池扩容到 300 个
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: T1.1

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

### T1.6: 创建黑名单配置
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 1h  
**Dependencies**: T1.5

**Description**: 建立社区黑名单和降权配置

**Checklist**:
- [ ] 创建 config/community_blacklist.yaml
- [ ] 添加黑名单社区（spam_farm, low_quality）
- [ ] 添加降权关键词（giveaway, for fun）
- [ ] 扩展 community_pool 表（is_blacklisted, blacklist_reason）
- [ ] 实现黑名单加载逻辑
- [ ] 测试黑名单过滤

**Acceptance Criteria**:
- 黑名单配置文件创建
- 黑名单社区被排除
- 降权关键词生效

---

### T1.7: 实现分级调度策略
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T1.4

**Description**: 根据社区质量分级调度抓取频率

**Checklist**:
- [ ] 计算社区质量分（avg_valid_posts）
- [ ] 分级：Tier 1（Top 20）、Tier 2（次优 40）、Tier 3（长尾）
- [ ] 更新 Celery Beat 配置（2h/6h/24h）
- [ ] 创建 crawl_tier 任务
- [ ] 测试分级调度

**Acceptance Criteria**:
- Tier 1：每 2 小时
- Tier 2：每 6 小时
- Tier 3：每 24 小时

---

### T1.8: 实现精准补抓任务
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T1.7

**Description**: 对低质量社区进行精准补抓

**Checklist**:
- [ ] 创建补抓任务（crawl_low_quality_communities）
- [ ] 查询条件：last_crawled_at > 8h 且 avg_valid_posts < 50
- [ ] 失败回写 empty_hit
- [ ] 添加到 Celery Beat（每 4 小时）
- [ ] 测试补抓逻辑

**Acceptance Criteria**:
- 低质量社区被补抓
- empty_hit 正确更新

---

## Phase 2: 分析引擎改造（T+3~9 天）

**目标**: 样本检查、规则优化、去重聚合

### T2.1: 实现样本下限检查
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T1.1

**Description**: 分析前检查样本量是否 ≥1500

**Checklist**:
- [ ] 实现 check_sample_size 函数
- [ ] 从热缓存读取样本量
- [ ] 从冷库补读（最近 30 天）
- [ ] 样本不足时触发补抓
- [ ] 集成到分析引擎
- [ ] 测试样本检查逻辑

**Acceptance Criteria**:
- 样本 ≥1500 才开始分析
- 样本不足自动触发补抓

---

### T2.2: 实现关键词补抓任务
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: T2.1

**Description**: 使用 Reddit Search API 按关键词抓取

**Checklist**:
- [ ] 实现 keyword_crawl 函数
- [ ] 提取产品描述关键词
- [ ] 调用 Reddit Search API
- [ ] 标记来源类型（cache/search）
- [ ] 写入冷库
- [ ] 测试关键词抓取

**Acceptance Criteria**:
- 关键词抓取成功
- 来源类型正确标记

---

### T2.3: 创建评分规则配置
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: None

**Description**: 创建正负关键词配置文件

**Checklist**:
- [ ] 创建 config/scoring_rules.yaml
- [ ] 添加正例关键词（need, urgent, looking for）
- [ ] 添加负例关键词（giveaway, for fun, just sharing）
- [ ] 添加语义否定模式（not interested, don't need）
- [ ] 实现配置加载逻辑
- [ ] 测试配置热更新

**Acceptance Criteria**:
- 配置文件创建
- 支持热更新

---

### T2.4: 改造 OpportunityScorer
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: T2.3

**Description**: 实现正负关键词对冲评分

**Checklist**:
- [ ] 加载评分规则配置
- [ ] 实现正例关键词评分
- [ ] 实现负例关键词对冲
- [ ] 实现语义否定检测
- [ ] 确保分数不低于 0
- [ ] 测试评分逻辑

**Acceptance Criteria**:
- 正负关键词对冲正常
- 语义否定检测生效

---

### T2.5: 实现文本清洗函数
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 1h  
**Dependencies**: None

**Description**: 去除 URL、代码块、引用块

**Checklist**:
- [ ] 实现 clean_text 函数
- [ ] 去除 URL（正则）
- [ ] 去除代码块（```...```）
- [ ] 去除引用块（> ...）
- [ ] 测试清洗效果

**Acceptance Criteria**:
- 噪声内容被正确去除
- 有效内容保留

---

### T2.6: 实现句级评分 + 上下文窗口
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T2.5

**Description**: 取当前句 + 前后各 1 句窗口评分

**Checklist**:
- [ ] 实现句子分割
- [ ] 实现 score_with_context 函数
- [ ] 窗口大小：±1 句
- [ ] 集成到评分器
- [ ] 测试上下文窗口

**Acceptance Criteria**:
- 句级评分正常
- 上下文窗口生效

---

### T2.7: 创建模板配置
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: None

**Description**: 创建正向模板和反模板配置

**Checklist**:
- [ ] 创建 config/scoring_templates.yaml
- [ ] 添加正向模板（金额、时间、数量）
- [ ] 添加反模板（招聘、抽奖、宣发）
- [ ] 实现模板匹配逻辑
- [ ] 测试模板加成/降权

**Acceptance Criteria**:
- 正向模板加权 +0.3
- 反模板降权/置零

---

### T2.8: 集成模板评分
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T2.4, T2.7

**Description**: 将模板评分集成到 OpportunityScorer

**Checklist**:
- [ ] 加载模板配置
- [ ] 实现正向模板匹配
- [ ] 实现反模板匹配
- [ ] 计算模板加成/降权
- [ ] 测试模板评分

**Acceptance Criteria**:
- 模板评分正常
- 加成/降权生效

---

### T2.9: 实现 MinHash 去重
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: None

**Description**: 使用 MinHash + LSH 去重

**Checklist**:
- [ ] 安装 datasketch 库
- [ ] 实现 deduplicate_posts 函数
- [ ] 相似度阈值：0.85
- [ ] 主贴保留，重复项聚合
- [ ] 记录证据计数
- [ ] 测试去重效果

**Acceptance Criteria**:
- 相似帖子被聚合
- 证据计数正确

---

### T2.10: 集成去重到分析引擎
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T2.9

**Description**: 在分析前进行去重

**Checklist**:
- [ ] 在分析引擎中调用去重
- [ ] 记录 duplicate_ids
- [ ] 记录 evidence_count
- [ ] 更新分析结果结构
- [ ] 测试去重集成

**Acceptance Criteria**:
- 分析前自动去重
- 证据计数记录到结果

---

## Phase 3: 评测与优化（T+9~18 天）

**目标**: 抽样标注、阈值校准、仪表盘、报告强化

### T3.1: 抽样标注数据集
**Status**: NOT_STARTED  
**Assignee**: AI Agent + User  
**Estimated**: 4h  
**Dependencies**: T2.10

**Description**: 从冷库抽样 500 条帖子进行人工标注

**Checklist**:
- [ ] 从冷库随机抽样 500 条
- [ ] 创建标注界面/表格
- [ ] 人工标注：机会/非机会、强/中/弱
- [ ] 保存到 data/labeled_samples.csv
- [ ] 验证标注质量

**Acceptance Criteria**:
- 500 条样本已标注
- 标注数据保存成功

---

### T3.2: 实现阈值网格搜索
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T3.1

**Description**: 网格搜索最优阈值

**Checklist**:
- [ ] 实现 grid_search_threshold 函数
- [ ] 阈值范围：0.3-0.9，步长 0.05
- [ ] 优化指标：Precision@50, F1
- [ ] 记录最优阈值
- [ ] 更新配置文件

**Acceptance Criteria**:
- 最优阈值：Precision@50 ≥0.6
- 配置文件已更新

---

### T3.3: 创建每日跑分脚本
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: T1.4

**Description**: 生成每日指标报告

**Checklist**:
- [ ] 实现 generate_daily_metrics 函数
- [ ] 收集指标（cache_hit_rate, valid_posts_24h, duplicate_rate 等）
- [ ] 写入 CSV（reports/daily_metrics/）
- [ ] 创建 Celery 定时任务（每日 0 点）
- [ ] 测试跑分脚本

**Acceptance Criteria**:
- 每日自动生成报告
- CSV 格式正确

---

### T3.4: 实现红线检查逻辑
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T3.3

**Description**: 检查红线触发条件并自动降级

**Checklist**:
- [ ] 实现 check_red_lines 函数
- [ ] 红线 1：有效帖子 <1500 → 保守模式
- [ ] 红线 2：缓存命中率 <60% → 提升抓取频率
- [ ] 红线 3：重复率 >20% → 改进去重
- [ ] 红线 4：Precision@50 <0.6 → 提高阈值
- [ ] 测试红线触发

**Acceptance Criteria**:
- 红线触发自动降级
- 降级策略生效

---

### T3.5: 改造报告模版
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 3h  
**Dependencies**: T2.10

**Description**: 添加行动位到报告模版

**Checklist**:
- [ ] 创建 OpportunityReport 类
- [ ] 添加 problem_definition 字段
- [ ] 添加 evidence_chain 字段（2-3 条）
- [ ] 添加 suggested_actions 字段
- [ ] 添加 confidence, urgency, product_fit 字段
- [ ] 实现 priority 计算（confidence × urgency × product_fit）
- [ ] 测试报告生成

**Acceptance Criteria**:
- 报告包含行动位
- 优先级计算正确

---

### T3.6: 集成行动位到 API
**Status**: NOT_STARTED  
**Assignee**: AI Agent  
**Estimated**: 2h  
**Dependencies**: T3.5

**Description**: 在 API 和前端展示行动位

**Checklist**:
- [ ] 更新分析结果 API
- [ ] 返回行动位字段
- [ ] 前端展示问题定义
- [ ] 前端展示证据链（可点击链接）
- [ ] 前端展示建议动作
- [ ] 前端展示优先级（星级）
- [ ] 测试前后端集成

**Acceptance Criteria**:
- API 返回行动位
- 前端正确展示

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

