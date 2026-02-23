# Spec 013 任务清单

**状态**: 🚧 In Progress  
**创建日期**: 2025-11-12  
**关联文档**: [spec.md](./spec.md) | [plan-v2.md](./plan-v2.md)

---

## 任务概览

| Phase | 任务数 | 预计工时 | 状态 |
|-------|--------|---------|------|
| Phase 0: 启动基础设施 | 5 | 8h | 🔴 未开始 |
| Phase 1: 扩充社区池 | 5 | 14h | 🔴 未开始 |
| Phase 2: 数据积累期 | 4 | 持续14-30天 | 🔴 未开始 |
| Phase 3: 质量优化 | 6 | 16h | 🔴 未开始 |
| Phase 4: 验收文档 | 4 | 12h | 🔴 未开始 |
| **总计** | **24** | **50h + 14-30天** | **0%** |

---

## Phase 0: 启动数据生产基础设施 (P0 - 2天)

### 0.1 添加 Celery Beat 启动函数
- **文件**: `scripts/makefile-common.sh`
- **预计工时**: 2h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
添加 `start_celery_beat` 和 `stop_celery_beat` 函数到 `scripts/makefile-common.sh`

**实施步骤**:
1. 在 `scripts/makefile-common.sh` 添加函数
2. 参考 `start_celery_worker` 的实现
3. 支持 foreground 和 background 模式
4. 日志输出到 `/tmp/celery_beat.log`

**验收标准**:
```bash
# 测试启动
source scripts/makefile-common.sh
start_celery_beat background

# 验证进程
ps aux | grep "celery.*beat" | grep -v grep
# 预期: 有进程

# 验证日志
tail -20 /tmp/celery_beat.log
# 预期: 看到 "Scheduler: Sending due task"
```

---

### 0.2 添加 Makefile Beat 命令
- **文件**: `makefiles/celery.mk`
- **预计工时**: 1h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
添加 4 个 Celery Beat 相关命令到 `makefiles/celery.mk`

**实施步骤**:
1. 添加 `celery-beat-start` 命令
2. 添加 `celery-beat-restart` 命令
3. 添加 `celery-beat-stop` 命令
4. 添加 `celery-beat-status` 命令
5. 更新 `make help` 输出

**验收标准**:
```bash
# 测试所有命令
make celery-beat-start &  # 后台启动
sleep 5
make celery-beat-status   # 检查状态
make celery-beat-stop     # 停止
make celery-beat-status   # 再次检查
# 预期: 第一次 ✅，第二次 ❌
```

---

### 0.3 更新 dev-golden-path
- **文件**: `scripts/dev_golden_path.sh`
- **预计工时**: 1h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
在 `dev-golden-path` 中添加 Celery Beat 启动步骤

**实施步骤**:
1. 在启动 Celery Worker 后添加 Beat 启动
2. 添加健康检查
3. 更新输出信息

**验收标准**:
```bash
# 执行 golden path
make dev-golden-path

# 验证 Beat 运行
ps aux | grep "celery.*beat" | grep -v grep
# 预期: 有进程
```

---

### 0.4 创建数据积累监控脚本
- **文件**: `backend/scripts/monitor_data_accumulation.py`
- **预计工时**: 3h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
创建数据积累监控脚本，支持多种监控模式

**实施步骤**:
1. 创建 `monitor_data_accumulation.py`
2. 实现 `check_data_growth(days)` 函数
3. 实现 `check_celery_beat_health()` 函数
4. 实现 `generate_accumulation_report()` 函数
5. 添加命令行参数支持

**验收标准**:
```bash
# 测试数据增长监控
python backend/scripts/monitor_data_accumulation.py --days 7
# 预期: 显示最近7天的数据增长趋势

# 测试 Beat 健康检查
python backend/scripts/monitor_data_accumulation.py --check-beat
# 预期: 显示 Beat 运行状态

# 测试报告生成
python backend/scripts/monitor_data_accumulation.py --report
# 预期: 生成完整的积累报告
```

---

### 0.5 添加 Makefile 监控命令
- **文件**: `Makefile`
- **预计工时**: 0.5h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
添加数据积累监控相关的 Makefile 命令

**实施步骤**:
1. 添加 `monitor-data-accumulation` 命令
2. 添加 `check-beat-health` 命令
3. 更新 `make help` 输出

**验收标准**:
```bash
# 测试命令
make monitor-data-accumulation
make check-beat-health

# 验证 help
make help | grep "monitor-data"
# 预期: 显示新命令
```

---

## Phase 1: 扩充社区池 (P0 - 3天)

### 1.1 导入 Top1000 社区
- **命令**: `make pool-import-top1000`
- **预计工时**: 1h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
执行 Top1000 社区导入，验证导入结果

**实施步骤**:
1. 执行 `make pool-import-top1000`
2. 验证导入数量
3. 检查数据质量

**验收标准**:
```bash
# 执行导入
make pool-import-top1000

# 验证数量
psql -c "SELECT COUNT(*) FROM community_pool WHERE is_active=true"
# 预期: ≥300

# 验证质量
make pool-stats
# 预期: 显示详细统计
```

---

### 1.2 执行语义评分回灌
- **命令**: `make semantic-refresh-pool`
- **预计工时**: 2h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
执行语义评分并回灌到社区池

**实施步骤**:
1. 执行 `make semantic-refresh-pool`
2. 验证评分覆盖率
3. 检查评分质量

**验收标准**:
```bash
# 执行回灌
make semantic-refresh-pool

# 验证覆盖率
psql -c "SELECT COUNT(*) FROM community_pool WHERE metadata->>'semantic_score' IS NOT NULL"
# 预期: ≥200

# 验证评分分布
psql -c "SELECT 
    CASE 
        WHEN (metadata->>'semantic_score')::float >= 0.7 THEN 'high'
        WHEN (metadata->>'semantic_score')::float >= 0.4 THEN 'medium'
        ELSE 'low'
    END as score_range,
    COUNT(*)
FROM community_pool
WHERE metadata->>'semantic_score' IS NOT NULL
GROUP BY score_range"
# 预期: 合理分布
```

---

### 1.3 优化 Tier 分级策略
- **文件**: `backend/scripts/optimize_tier_allocation.py`
- **预计工时**: 4h
- **优先级**: P1
- **状态**: 🔴 未开始

**任务描述**:
创建 Tier 分级优化脚本，基于语义评分和历史表现重新分配 Tier

**实施步骤**:
1. 创建 `optimize_tier_allocation.py`
2. 实现综合评分算法
3. 实现 Tier 重新分配逻辑
4. 更新 community_pool

**验收标准**:
```bash
# 执行优化
python backend/scripts/optimize_tier_allocation.py

# 验证 Tier 分布
make pool-stats
# 预期: T1:20, T2:80, T3:200+

# 验证高质量社区在 T1
psql -c "SELECT name, tier, metadata->>'semantic_score' as score 
FROM community_pool 
WHERE tier='T1' 
ORDER BY (metadata->>'semantic_score')::float DESC 
LIMIT 10"
# 预期: 评分都 ≥0.7
```

---

### 1.4 添加持续发现机制
- **文件**: `backend/app/tasks/community_discovery_task.py`
- **预计工时**: 6h
- **优先级**: P1
- **状态**: 🔴 未开始

**任务描述**:
创建社区持续发现任务，每周从用户任务中发现新社区

**实施步骤**:
1. 创建 `community_discovery_task.py`
2. 实现 `discover_from_user_tasks()` 函数
3. 添加到 Celery Beat 调度
4. 添加通知机制

**验收标准**:
```bash
# 手动触发任务
python -c "from app.tasks.community_discovery_task import discover_from_user_tasks; discover_from_user_tasks()"

# 验证发现结果
psql -c "SELECT * FROM community_discovery_candidates ORDER BY created_at DESC LIMIT 10"
# 预期: 有新发现的社区

# 验证调度
redis-cli KEYS "*discover-new-communities*"
# 预期: 有调度记录
```

---

### 1.5 验证社区池扩充完成
- **预计工时**: 1h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
验证社区池扩充的所有目标都已达成

**验收标准**:
```bash
# 1. 社区池规模
psql -c "SELECT COUNT(*) FROM community_pool WHERE is_active=true"
# 预期: ≥300

# 2. Tier 分布
make pool-stats
# 预期: T1:20, T2:80, T3:200+

# 3. 语义评分覆盖
psql -c "SELECT COUNT(*) FROM community_pool WHERE metadata->>'semantic_score' IS NOT NULL"
# 预期: ≥200

# 4. 持续发现任务
redis-cli KEYS "*discover-new-communities*"
# 预期: 有调度记录

# 5. 生成 Phase 1 报告
cat reports/phase-log/phase013-phase1.md
# 预期: 所有验收标准通过
```

---

## Phase 2: 数据积累期 (P1 - 14-30天)

### 2.1 每日数据增长监控
- **命令**: `make monitor-data-accumulation`
- **预计工时**: 持续
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
每天执行数据增长监控，记录增长趋势

**实施步骤**:
1. 每天执行 `make monitor-data-accumulation`
2. 记录数据到 `reports/phase-log/daily-growth.csv`
3. 如果增长异常，立即排查

**验收标准**:
```bash
# 每日执行
make monitor-data-accumulation

# 验证增长
tail -7 reports/phase-log/daily-growth.csv
# 预期: 每日新增 ≥1,000 条
```

---

### 2.2 每周生成积累报告
- **文件**: `backend/scripts/generate_weekly_accumulation_report.py`
- **预计工时**: 2h (开发) + 每周1h (执行)
- **优先级**: P1
- **状态**: 🔴 未开始

**任务描述**:
创建每周数据积累报告生成脚本

**实施步骤**:
1. 创建 `generate_weekly_accumulation_report.py`
2. 实现报告生成逻辑
3. 每周日执行

**验收标准**:
```bash
# 生成报告
python backend/scripts/generate_weekly_accumulation_report.py --week 1

# 验证报告
cat reports/phase-log/phase013-phase2-week1.md
# 预期: 包含数据池规模、增长趋势、社区覆盖度等
```

---

### 2.3 监控抓取任务成功率
- **预计工时**: 持续
- **优先级**: P1
- **状态**: 🔴 未开始

**任务描述**:
每天监控抓取任务成功率，确保 ≥80%

**验收标准**:
```bash
# 每日检查
psql -c "SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) as succeeded,
    ROUND(100.0 * SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM crawl_metrics
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC"
# 预期: success_rate ≥80%
```

---

### 2.4 验证数据积累目标
- **预计工时**: 每周1h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
每周验证数据积累是否达到目标

**验收标准**:
```bash
# Week 1 (Day 7)
psql -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '30 days'"
# 预期: ≥15,000

# Week 2 (Day 14)
psql -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '30 days'"
# 预期: ≥20,000

# Week 3-4 (Day 21-30)
psql -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '30 days'"
# 预期: ≥30,000
```

---

## Phase 3: 数据质量优化 (P1 - 5天)

### 3.1 修复 Evidence URL 格式
- **文件**: `backend/scripts/backfill_real_evidence.py`
- **预计工时**: 6h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
创建 Evidence URL 修复脚本，从 posts_hot 回溯真实 URL

**实施步骤**:
1. 创建 `backfill_real_evidence.py`
2. 实现 URL 回溯逻辑
3. 实现 URL 可访问性检查
4. 批量修复所有 Evidence

**验收标准**:
```bash
# 执行修复
python backend/scripts/backfill_real_evidence.py

# 验证修复结果
python backend/scripts/check_evidence_quality.py
# 预期: 95%+ URL 可访问
```

---

### 3.2 添加 Neutral 情感类别
- **文件**: `backend/app/services/analysis/sentiment.py`
- **预计工时**: 4h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
扩展情感分类算法，添加 neutral 类别

**实施步骤**:
1. 修改 `sentiment.py`
2. 添加 `classify_sentiment_with_neutral()` 函数
3. 更新所有调用点
4. 添加单元测试

**验收标准**:
```bash
# 运行单元测试
pytest backend/tests/services/analysis/test_sentiment.py -v

# 验证情感分布
make content-acceptance
# 预期: neutral_pct ∈ [10%, 40%] 在 80% 报告中
```

---

### 3.3 竞品分层多源汇总
- **文件**: `backend/app/services/analysis/competitor_layering.py`
- **预计工时**: 3h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
扩展竞品分层算法，支持多源数据汇总

**实施步骤**:
1. 修改 `competitor_layering.py`
2. 添加 `aggregate_competitor_layers()` 函数
3. 实现多源汇总逻辑
4. 添加单元测试

**验收标准**:
```bash
# 运行单元测试
pytest backend/tests/services/analysis/test_competitor_layering.py -v

# 验证分层结果
psql -c "SELECT AVG(jsonb_array_length(report->'competitor_layers_summary')) FROM reports WHERE created_at >= NOW() - INTERVAL '7 days'"
# 预期: ≥2.0
```

---

### 3.4 更新 Content Acceptance 门禁
- **文件**: `backend/scripts/content_acceptance.py`
- **预计工时**: 2h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
更新 content-acceptance 脚本，添加新的质量检查

**实施步骤**:
1. 添加 Evidence 可访问性检查
2. 添加 Neutral 占比检查
3. 添加 Competitor 分层检查
4. 更新评分算法

**验收标准**:
```bash
# 执行门禁
make content-acceptance

# 验证评分
cat reports/local-acceptance/content-acceptance-latest.json | jq '.score'
# 预期: ≥90
```

---

### 3.5 创建 Evidence 质量检查脚本
- **文件**: `backend/scripts/check_evidence_quality.py`
- **预计工时**: 2h
- **优先级**: P1
- **状态**: 🔴 未开始

**任务描述**:
创建 Evidence 质量检查脚本，验证 URL 可访问性

**实施步骤**:
1. 创建 `check_evidence_quality.py`
2. 实现 URL 可访问性检查
3. 生成质量报告

**验收标准**:
```bash
# 执行检查
python backend/scripts/check_evidence_quality.py

# 预期输出:
# Total Evidence: 112
# Accessible URLs: 108 (96.4%)
# Broken URLs: 4 (3.6%)
```

---

### 3.6 验证质量优化完成
- **预计工时**: 1h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
验证所有质量优化目标都已达成

**验收标准**:
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

# 4. Content Acceptance 评分
make content-acceptance
# 预期: score ≥90

# 5. 生成 Phase 3 报告
cat reports/phase-log/phase013-phase3.md
# 预期: 所有验收标准通过
```

---

## Phase 4: 验收与文档 (P1 - 2天)

### 4.1 完整闭环验收
- **命令**: `make crossborder-acceptance`
- **预计工时**: 4h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
执行完整的数据生产闭环验收

**验收标准**:
```bash
# 执行完整验收
make crossborder-acceptance

# 验证所有步骤成功
# 1. discover-crossborder ✅
# 2. pool-init ✅
# 3. pool-import-top1000 ✅
# 4. semantic-build-L1 ✅
# 5. crossborder-high-value ✅
```

---

### 4.2 质量门禁验证
- **命令**: `make content-acceptance`
- **预计工时**: 2h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
执行质量门禁验证，确保评分 ≥90

**验收标准**:
```bash
# 执行门禁
make content-acceptance

# 验证评分
cat reports/local-acceptance/content-acceptance-latest.json | jq '.score'
# 预期: ≥90
```

---

### 4.3 生成 Phase 013 报告
- **文件**: `reports/phase-log/phase013.md`
- **预计工时**: 4h
- **优先级**: P0
- **状态**: 🔴 未开始

**任务描述**:
生成完整的 Phase 013 验收报告

**验收标准**:
```bash
# 验证报告存在
cat reports/phase-log/phase013.md

# 验证所有里程碑达成
cat reports/phase-log/phase013.md | grep "✅" | wc -l
# 预期: ≥6

# 验证所有关键指标达标
cat reports/phase-log/phase013.md | grep "目标" | grep "✅" | wc -l
# 预期: ≥8
```

---

### 4.4 更新文档
- **文件**: README.md, quickstart.md, monitoring.md
- **预计工时**: 2h
- **优先级**: P1
- **状态**: 🔴 未开始

**任务描述**:
更新所有相关文档

**验收标准**:
```bash
# 验证文档存在
ls .specify/specs/013-legacy-quality-gap/
# 预期: spec.md, plan-v2.md, tasks.md, quickstart.md, monitoring.md

# 验证 README 更新
grep "Spec 013" README.md
# 预期: 有相关说明
```

---

## 进度跟踪

### 当前进度

- Phase 0: 0/5 (0%)
- Phase 1: 0/5 (0%)
- Phase 2: 0/4 (0%)
- Phase 3: 0/6 (0%)
- Phase 4: 0/4 (0%)
- **总计**: 0/24 (0%)

### 下一步行动

1. ✅ 开始 Phase 0.1: 添加 Celery Beat 启动函数
2. ⏳ 等待 Phase 0.1 完成
3. ⏳ 继续 Phase 0.2-0.5
4. ⏳ 开始 Phase 1

---

**文档状态**: ✅ Ready for Implementation  
**下次更新**: 每完成一个任务更新进度  
**最后更新**: 2025-11-12

