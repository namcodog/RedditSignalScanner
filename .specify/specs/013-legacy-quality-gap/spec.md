# Spec 013: 数据生产闭环启动与质量优化

**状态**: 🚧 In Progress  
**优先级**: P0 - Critical  
**创建日期**: 2025-11-12  
**负责人**: Product Team  
**关联**: Spec 009-012 (数据生产基础), Spec 010 (报告质量), Spec 011 (语义库)

---

## 📋 执行摘要

### 问题陈述

虽然 Spec 009-012 已完成 85% 的功能闭环，但**数据生产闭环未真正运转**：

1. 🔴 **Celery Beat 未启动** - 定时抓取配置已存在但未运行，导致数据积累停滞
2. 🔴 **数据储备不足** - 最近30天仅 10,519 条帖子，远低于样本级报告所需的 20,000+ 条
3. ⚠️ **社区池未扩充** - 仅 200 个社区，未导入 Top1000，未执行语义回灌
4. ⚠️ **数据质量缺口** - Evidence URL 格式错误、缺少 neutral 情感类别、竞品分层数据单一

**核心洞察**: 没有持续的数据积累，就无法产出样本级质量的报告。Spec 013 的真正目标是**让整个数据生产闭环运转起来**。

### 目标

**主目标**: 启动并运转完整的数据生产闭环，实现持续数据积累和质量优化

**子目标**:
1. ✅ 启动 Celery Beat 定时调度，实现每天新增 ~1,500 条帖子
2. ✅ 扩充社区池到 300+，优化 Tier 分级抓取策略
3. ✅ 积累 14-30 天数据，达到 20,000+ 帖子储备
4. ✅ 修复数据质量缺口（Evidence + Sentiment + Competitor）
5. ✅ 建立数据积累监控和质量门禁

### 成功标准

| 指标 | 当前值 | 目标值 | 验收标准 |
|------|--------|--------|---------|
| **Celery Beat 运行** | ❌ 未启动 | ✅ 持续运行 | `ps aux \| grep celery.*beat` 有进程 |
| **每日新增帖子** | 0 | ~1,500 | 连续7天平均 ≥1,000 条/天 |
| **数据池规模** | 10,519 | 20,000+ | `SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '30 days'` |
| **社区池规模** | 200 | 300+ | `SELECT COUNT(*) FROM community_pool WHERE is_active=true` |
| **Evidence 可用性** | 0% | 95%+ | 每个 action_item ≥2 条真实可访问 URL |
| **Neutral 情感占比** | 0% | 10-40% | 80% 的报告中 neutral_pct ∈ [10%, 40%] |
| **竞品分层完整性** | 0 层 | ≥2 层 | 每份报告 competitor_layers_summary ≥2 |
| **报告质量评分** | 60% | 90%+ | `content-acceptance` score ≥90 |

---

## 🎯 范围定义

### 包含范围 (In Scope)

#### Phase 0: 数据生产基础设施启动 (P0 - 2天)
- ✅ 添加 `celery-beat-start` 命令到 `makefiles/celery.mk`
- ✅ 添加 `start_celery_beat` 函数到 `scripts/makefile-common.sh`
- ✅ 更新 `dev-golden-path` 包含 Celery Beat 启动
- ✅ 添加 Celery Beat 健康检查命令 `celery-beat-status`
- ✅ 创建数据积累监控脚本 `scripts/monitor_data_accumulation.py`

#### Phase 1: 社区池扩充与优化 (P0 - 3天)
- ✅ 执行 `make pool-import-top1000` 导入 Top1000 社区
- ✅ 执行 `make semantic-refresh-pool` 语义评分回灌
- ✅ 优化 Tier 分级策略（T1/T2/T3 社区分配）
- ✅ 添加社区池持续发现机制（每周从用户任务中发现新社区）
- ✅ 验证社区池规模达到 300+

#### Phase 2: 数据积累期 (P1 - 14-30天)
- ✅ 持续监控 Celery Beat 运行状态
- ✅ 每日检查数据增长（目标 ~1,500 条/天）
- ✅ 监控抓取任务成功率（目标 ≥80%）
- ✅ 监控 Redis 缓存命中率（目标 ≥70%）
- ✅ 每周生成数据积累报告

#### Phase 3: 数据质量优化 (P1 - 5天)
- ✅ 修复 Evidence URL 格式错误（从 posts_hot 回溯真实 URL）
- ✅ 添加 neutral 情感类别（基于 TextBlob polarity 阈值）
- ✅ 实现竞品分层多源汇总（YAML + posts_hot 统计 + community_pool 标签）
- ✅ 更新 `content-acceptance` 门禁脚本
- ✅ 添加 Evidence 可访问性探活检查

#### Phase 4: 验收与文档 (P1 - 2天)
- ✅ 完整闭环验收（从社区发现到报告生成）
- ✅ 质量门禁验证（content-acceptance score ≥90）
- ✅ 生成 Phase 完成报告到 `reports/phase-log/phase013.md`
- ✅ 更新 README.md 和文档
- ✅ 创建 Spec 013 快速启动指南

### 排除范围 (Out of Scope)

- ❌ LLM 增强的证据生成（保持可选，不作为 P0 要求）
- ❌ 实时情感分析（使用批处理模式）
- ❌ 多语言支持（仅英文）
- ❌ 证据归档到 S3/MinIO（使用 PostgreSQL 存储）
- ❌ 前端 UI 改动（仅后端和脚本）

---

## 🏗️ 技术架构

### 数据生产闭环流程图

```
语义库 L1-L4
    ↓ 驱动
社区发现 (discover_communities)
    ↓ 语义评分
社区池 200+ → 300+
    ↓ Tier 分级 (T1/T2/T3)
Celery Beat 调度 ⚡ [新增]
    ↓ 定时触发
持续抓取 (T1:2h T2:4h T3:6h)
    ↓ 并发抓取
Redis 缓存 + PostgreSQL 存储
    ↓ 数据积累 (≥30天)
posts_hot 50k+ [目标]
    ↓ 分析引擎
信号提取 (痛点/机会/竞品)
    ↓ 聚类/分层/量化
报告生成 (controlled_summary_v2)
    ↓ 质量门禁
样本级报告 ✨
```

### 关键组件

#### 1. Celery Beat 调度器
```python
# backend/app/core/celery_app.py (已存在)
celery_app.conf.beat_schedule = {
    "auto-crawl-incremental": {
        "task": "tasks.crawler.crawl_seed_communities_incremental",
        "schedule": crontab(minute="0,30"),  # 每30分钟
    },
    "warmup-crawl-seed-communities": {
        "task": "tasks.crawler.crawl_seed_communities",
        "schedule": crontab(minute="0", hour="*/2"),  # 每2小时
    },
    "crawl-low-quality-communities": {
        "task": "tasks.crawler.crawl_low_quality_communities",
        "schedule": crontab(minute="0", hour="*/4"),  # 每4小时
    },
}
```

#### 2. 数据积累监控
```python
# backend/scripts/monitor_data_accumulation.py (新增)
def monitor_data_accumulation():
    """监控数据积累状态"""
    # 1. 检查最近7天的数据增长
    # 2. 计算每日新增帖子数
    # 3. 检查社区覆盖度
    # 4. 生成监控报告
```

#### 3. Evidence 修复
```python
# backend/app/services/evidence/backfill.py (新增)
def backfill_real_evidence(task_id: str):
    """从 posts_hot 回溯真实证据"""
    # 1. 读取 insight_cards
    # 2. 根据 subreddit 匹配 posts_hot
    # 3. 提取真实 URL 和 excerpt
    # 4. 更新 evidences 表
```

#### 4. Sentiment 优化
```python
# backend/app/services/analysis/sentiment.py (扩展)
def classify_sentiment_with_neutral(text: str) -> str:
    """添加 neutral 类别"""
    polarity = TextBlob(text).sentiment.polarity
    if abs(polarity) < 0.1:  # 弱情绪阈值
        return "neutral"
    elif polarity > 0:
        return "positive"
    else:
        return "negative"
```

---

## 📊 数据需求分析

### 报告样本质量标准

基于 `crypto-report` 样本分析：
- 15 个痛点 → 需聚类成 ≥2 个簇
- 5 个机会 → 每个需量化 potential_users
- 3 个行动项 → 每项 ≥3 条真实证据
- 20 个社区覆盖
- 情感分布：positive 15%, negative 85%, neutral 0% (需修复)

### 数据量反推计算

```python
# 信号提取比例（基于现有算法）
痛点提取率 = 8%   # 需要负向情感 + 关键词匹配
机会提取率 = 4%   # 需要正向意图 + 模板匹配
有效证据率 = 60%  # URL 可访问 + 内容相关

# 单次分析所需帖子数
痛点所需 = 15 / 0.08 = 188 条
机会所需 = 5 / 0.04 = 125 条
证据所需 = 9 / 0.60 = 15 条

# 综合（加安全系数 2x）
单次最小 = max(188, 125, 15) × 2 = 376 条

# 考虑社区多样性（20 个社区）
每社区最小 = 376 / 20 = 19 条

# 持续积累需求（关键）
理想数据池 = 20 社区 × 500 条/社区 = 10,000 条
目标数据池 = 300 社区 × 100 条/社区 = 30,000 条

# 数据新鲜度要求
最近7天: 30% (9,000 条)
最近30天: 50% (15,000 条)
历史数据: 20% (6,000 条)
```

### 持续抓取频率

```python
# T1 社区（高价值，20个）
频率 = 每2小时
每次抓取 = 100条
日新增 = 20 × 100 × 12 = 24,000 条 (理论值)
实际去重后 = ~1,200 条/天

# T2 社区（中价值，80个）
频率 = 每4小时
每次抓取 = 50条
日新增 = 80 × 50 × 6 = 24,000 条 (理论值)
实际去重后 = ~300 条/天

# T3 社区（低价值，100个）
频率 = 每6小时
每次抓取 = 20条
日新增 = 100 × 20 × 4 = 8,000 条 (理论值)
实际去重后 = ~80 条/天

# 总计
每日新增 = 1,200 + 300 + 80 = ~1,580 条/天
```

---

## 🚀 实施路线图

### Timeline

```
Week 1 (Day 1-7):
├─ Day 1-2: Phase 0 - 启动 Celery Beat
├─ Day 3-5: Phase 1 - 扩充社区池
└─ Day 6-7: 验证数据开始积累

Week 2-4 (Day 8-30):
├─ Phase 2 - 数据积累期
├─ 每日监控数据增长
└─ 每周生成积累报告

Week 5 (Day 31-35):
├─ Phase 3 - 数据质量优化
└─ Phase 4 - 验收与文档

Total: 35 天 (5 周)
```

### 里程碑

| 里程碑 | 日期 | 交付物 | 验收标准 |
|--------|------|--------|---------|
| M0: Celery Beat 启动 | Day 2 | `celery-beat-start` 命令 | Beat 进程持续运行 24h |
| M1: 社区池扩充完成 | Day 5 | 300+ 社区池 | `pool-stats` 显示 ≥300 |
| M2: 数据积累 Week 1 | Day 14 | 10,000+ 帖子 | 每日新增 ≥1,000 条 |
| M3: 数据积累 Week 2 | Day 21 | 20,000+ 帖子 | 报告质量达 75% |
| M4: 质量优化完成 | Day 33 | Evidence/Sentiment/Competitor 修复 | `content-acceptance` ≥90 |
| M5: 完整闭环验收 | Day 35 | Phase 013 报告 | 所有验收标准通过 |

---

## 📝 验收标准

### Phase 0 验收

```bash
# 1. Celery Beat 进程运行
ps aux | grep "celery.*beat" | grep -v grep
# 预期: 有进程

# 2. Beat 健康检查
make celery-beat-status
# 预期: ✅ Celery Beat is running

# 3. 定时任务调度
redis-cli KEYS "celery-task-meta-*" | wc -l
# 预期: >0 (有任务执行记录)
```

### Phase 1 验收

```bash
# 1. 社区池规模
psql -c "SELECT COUNT(*) FROM community_pool WHERE is_active=true"
# 预期: ≥300

# 2. Tier 分布
make pool-stats
# 预期: T1:20, T2:80, T3:200+

# 3. 语义回灌
psql -c "SELECT COUNT(*) FROM community_pool WHERE metadata->>'semantic_score' IS NOT NULL"
# 预期: ≥200
```

### Phase 2 验收

```bash
# 1. 数据增长
python backend/scripts/monitor_data_accumulation.py --days 7
# 预期: 平均每日新增 ≥1,000 条

# 2. 数据池规模
psql -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '30 days'"
# 预期: ≥20,000

# 3. 社区覆盖
psql -c "SELECT COUNT(DISTINCT subreddit) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '7 days'"
# 预期: ≥100
```

### Phase 3 验收

```bash
# 1. Evidence 可用性
python backend/scripts/check_evidence_quality.py
# 预期: 95%+ URL 可访问

# 2. Sentiment 分布
make content-acceptance
# 预期: neutral_pct ∈ [10%, 40%] 在 80% 报告中

# 3. Competitor 分层
psql -c "SELECT AVG(jsonb_array_length(report->'competitor_layers_summary')) FROM reports WHERE created_at >= NOW() - INTERVAL '7 days'"
# 预期: ≥2.0
```

### Phase 4 验收

```bash
# 1. 完整闭环
make crossborder-acceptance
# 预期: 所有步骤成功

# 2. 质量门禁
make content-acceptance
# 预期: score ≥90

# 3. Phase 报告
cat reports/phase-log/phase013.md
# 预期: 包含所有里程碑和验收结果
```

---

## 🔗 相关文档

- [Implementation Plan](./plan.md) - 详细实施计划
- [Tasks](./tasks.md) - 任务清单
- [Spec 009-012](../) - 数据生产基础
- [Spec 010](../010-样本级报告达成蓝图.md) - 报告质量标准
- [Spec 011](../011-semantic-lexicon-development-plan.md) - 语义库开发

---

**文档状态**: ✅ Ready for Implementation  
**下次更新**: Phase 0 完成后更新状态为 In Progress  
**最后更新**: 2025-11-12

