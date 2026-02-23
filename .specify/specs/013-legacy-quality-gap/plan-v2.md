# Implementation Plan: 数据生产闭环启动与质量优化 (Spec 013)

**Branch**: `013-data-production-loop` | **Date**: 2025-11-12 | **Spec**: [spec.md](./spec.md)

## Summary

**Spec 013 的真正目标**: 让整个数据生产闭环运转起来，而不仅仅是修复3个质量缺口。

**核心问题**: 虽然 Spec 009-012 已完成 85% 的功能闭环，但数据生产闭环未真正运转：
1. 🔴 Celery Beat 未启动 - 定时抓取配置已存在但未运行
2. 🔴 数据储备不足 - 最近30天仅 10,519 条帖子
3. ⚠️ 社区池未扩充 - 仅 200 个社区
4. ⚠️ 数据质量缺口 - Evidence/Sentiment/Competitor

**解决方案**: 5 个 Phase 的完整计划，从启动基础设施到数据积累再到质量优化。

---

## Technical Context

**Language/Version**: Python 3.11 (FastAPI + Celery)，TypeScript 5.x (Vite + React)  
**Primary Dependencies**: FastAPI, SQLAlchemy, Redis, PostgreSQL, Celery Beat, React 18  
**Storage**: PostgreSQL (posts_hot/posts_raw/community_pool)，Redis (缓存 & 队列)  
**Testing**: pytest、content-acceptance、数据积累监控  
**Target Platform**: macOS (开发) + Linux (生产)  
**Performance Goals**: 每日新增 ~1,500 条帖子，30天积累 ≥20,000 条  
**Constraints**: 不能破坏现有验收；必须离线友好；Reddit API 速率限制  
**Scale/Scope**: 300+ 社区池，日均 1.5k 帖子，支撑 3-5 同时分析任务

---

## Constitution Check

| Gate | Status | 说明 |
|------|--------|------|
| 单一职责 | ✅ | Celery Beat 仅负责调度，抓取任务独立 |
| 依赖倒置 | ✅ | 监控脚本通过 DB 查询，不依赖 Celery 内部状态 |
| 复杂度控制 | ✅ | 每个 Phase 独立可验收，可回滚 |
| 质量门禁 | ⚠️ | 需更新 content-acceptance 新增数据积累检查 |
| 数据合规 | ✅ | 遵守 Reddit API TOS，速率限制已配置 |

---

## Project Structure

### Documentation
```
.specify/specs/013-legacy-quality-gap/
├── spec.md              # 完整需求规格 (已创建)
├── plan-v2.md           # 本文档 - 完整实施计划
├── tasks.md             # 详细任务清单 (待创建)
├── quickstart.md        # 快速启动指南 (待创建)
└── monitoring.md        # 数据积累监控指南 (待创建)
```

### Source Code Touchpoints
```
backend/
├── app/core/celery_app.py          # ✅ 已有 beat_schedule 配置
├── app/tasks/crawler_task.py       # ✅ 已有 3 个抓取任务
├── scripts/
│   ├── monitor_data_accumulation.py    # 新增：数据积累监控
│   ├── check_celery_beat_health.py     # 新增：Beat 健康检查
│   ├── backfill_real_evidence.py       # 新增：Evidence 修复
│   └── check_evidence_quality.py       # 新增：Evidence 质量检查
├── app/services/analysis/
│   └── sentiment.py                # 扩展：添加 neutral 类别
└── app/services/analysis/
    └── competitor_layering.py      # 扩展：多源汇总

makefiles/
└── celery.mk                       # 扩展：添加 celery-beat-start

scripts/
└── makefile-common.sh              # 扩展：添加 start_celery_beat 函数
```

---

## Implementation Strategy

### Phase 0 – 启动数据生产基础设施 (P0 - 2天)

**目标**: 启动 Celery Beat，让定时抓取开始运行

#### 任务清单

1. **添加 Celery Beat 启动函数** (2小时)
   ```bash
   # scripts/makefile-common.sh
   start_celery_beat() {
     local mode=${1:-foreground}
     load_backend_env
     pushd "${BACKEND_DIR}" >/dev/null
     local cmd=("${PYTHON_BIN}" -m celery -A "${CELERY_APP}" beat --loglevel=info)
     if [[ "${mode}" == "background" ]]; then
       nohup "${cmd[@]}" >"${CELERY_BEAT_LOG}" 2>&1 &
     else
       "${cmd[@]}"
     fi
     popd >/dev/null
   }
   
   stop_celery_beat() {
     pkill -f "celery.*beat" || true
   }
   ```

2. **添加 Makefile 命令** (1小时)
   ```makefile
   # makefiles/celery.mk
   celery-beat-start: ## 启动 Celery Beat 调度器（前台运行）
       @. $(COMMON_SH)
       @echo "==> Starting Celery Beat scheduler ..."
       @echo "    日志: $(CELERY_BEAT_LOG)"
       @require_backend_env
       @start_celery_beat foreground
   
   celery-beat-restart: celery-beat-stop ## 重启 Celery Beat（后台运行）
       @. $(COMMON_SH)
       @echo "==> Restarting Celery Beat ..."
       @require_backend_env
       @start_celery_beat background
       @sleep 3
       @tail -20 $(CELERY_BEAT_LOG) | grep "Scheduler" && echo "✅ Celery Beat restarted" || echo "⚠️  请检查日志"
   
   celery-beat-stop: ## 停止 Celery Beat
       @. $(COMMON_SH)
       @echo "==> Stopping Celery Beat ..."
       @stop_celery_beat
   
   celery-beat-status: ## 检查 Celery Beat 运行状态
       @if ps aux | grep "celery.*beat" | grep -v grep > /dev/null; then \
           echo "✅ Celery Beat is running"; \
       else \
           echo "❌ Celery Beat is NOT running"; \
           exit 1; \
       fi
   ```

3. **更新 dev-golden-path** (1小时)
   ```bash
   # scripts/dev_golden_path.sh
   # 在启动 Celery Worker 后添加：
   echo "4️⃣  启动 Celery Beat（后台）..."
   start_celery_beat background
   sleep 3
   tail -20 $CELERY_BEAT_LOG | grep "Scheduler" && echo "✅ Celery Beat started" || echo "⚠️  请检查日志"
   ```

4. **创建数据积累监控脚本** (3小时)
   ```python
   # backend/scripts/monitor_data_accumulation.py
   """监控数据积累状态"""
   
   def check_data_growth(days: int = 7):
       """检查最近N天的数据增长"""
       # 1. 查询每日新增帖子数
       # 2. 计算平均增长率
       # 3. 检查社区覆盖度
       # 4. 生成监控报告
   
   def check_celery_beat_health():
       """检查 Celery Beat 运行状态"""
       # 1. 检查进程是否运行
       # 2. 检查最近的任务执行记录
       # 3. 检查任务成功率
   
   def generate_accumulation_report():
       """生成数据积累报告"""
       # 1. 数据池规模
       # 2. 每日增长趋势
       # 3. 社区覆盖度
       # 4. 抓取成功率
   ```

5. **添加 Makefile 监控命令** (30分钟)
   ```makefile
   # Makefile
   .PHONY: monitor-data-accumulation ## 监控数据积累状态
   monitor-data-accumulation:
       $(PYTHON) -u backend/scripts/monitor_data_accumulation.py --days 7
   
   .PHONY: check-beat-health ## 检查 Celery Beat 健康状态
   check-beat-health:
       $(PYTHON) -u backend/scripts/monitor_data_accumulation.py --check-beat
   ```

#### 验收标准

```bash
# 1. Celery Beat 进程运行
make celery-beat-status
# 预期: ✅ Celery Beat is running

# 2. 定时任务调度
redis-cli KEYS "celery-task-meta-*" | wc -l
# 预期: >0 (有任务执行记录)

# 3. 数据开始增长
make monitor-data-accumulation
# 预期: 显示最近7天的数据增长趋势

# 4. Beat 日志正常
tail -50 /tmp/celery_beat.log
# 预期: 看到定时任务调度记录
```

#### 产出物

- ✅ `scripts/makefile-common.sh` 新增 `start_celery_beat` 函数
- ✅ `makefiles/celery.mk` 新增 4 个 Beat 相关命令
- ✅ `scripts/dev_golden_path.sh` 包含 Beat 启动
- ✅ `backend/scripts/monitor_data_accumulation.py` 监控脚本
- ✅ Celery Beat 持续运行 24 小时

---

### Phase 1 – 扩充社区池 (P0 - 3天)

**目标**: 将社区池从 200 扩充到 300+，优化 Tier 分级

#### 任务清单

1. **导入 Top1000 社区** (1小时)
   ```bash
   # 已有命令，直接执行
   make pool-import-top1000
   
   # 验证导入结果
   make pool-stats
   ```

2. **执行语义评分回灌** (2小时)
   ```bash
   # 已有命令，直接执行
   make semantic-refresh-pool
   
   # 验证回灌结果
   psql -c "SELECT COUNT(*) FROM community_pool WHERE metadata->>'semantic_score' IS NOT NULL"
   ```

3. **优化 Tier 分级策略** (4小时)
   ```python
   # backend/scripts/optimize_tier_allocation.py (新增)
   """优化 Tier 分级策略"""
   
   def optimize_tier_allocation():
       """基于语义评分和历史表现优化 Tier 分配"""
       # 1. 读取社区池
       # 2. 计算综合评分（语义 + 活跃度 + 质量）
       # 3. 重新分配 Tier (T1:20, T2:80, T3:200+)
       # 4. 更新 community_pool
   ```

4. **添加持续发现机制** (6小时)
   ```python
   # backend/app/tasks/community_discovery_task.py (新增)
   """社区持续发现任务"""
   
   @celery_app.task(name="tasks.community.discover_from_user_tasks")
   def discover_from_user_tasks():
       """每周从用户任务中发现新社区"""
       # 1. 分析最近7天的用户任务
       # 2. 提取高频提及的社区
       # 3. 自动添加到待审核表
       # 4. 通知管理员审核
   ```

5. **添加到 Celery Beat 调度** (30分钟)
   ```python
   # backend/app/core/celery_app.py
   celery_app.conf.beat_schedule["discover-new-communities"] = {
       "task": "tasks.community.discover_from_user_tasks",
       "schedule": crontab(day_of_week="0", hour="2", minute="0"),  # 每周日 02:00
       "options": {"queue": "crawler_queue"},
   }
   ```

#### 验收标准

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

# 4. 持续发现任务调度
redis-cli KEYS "*discover-new-communities*"
# 预期: 有调度记录
```

#### 产出物

- ✅ 社区池规模 ≥300
- ✅ Tier 分级优化完成
- ✅ 语义评分回灌完成
- ✅ 持续发现机制上线
- ✅ `reports/phase-log/phase013-phase1.md` 验收报告

---

### Phase 2 – 数据积累期 (P1 - 14-30天)

**目标**: 持续监控数据积累，达到 20,000+ 帖子储备

#### 任务清单

1. **每日数据增长监控** (持续)
   ```bash
   # 每天执行
   make monitor-data-accumulation
   
   # 预期输出示例：
   # Day 1: +1,234 posts (total: 11,753)
   # Day 2: +1,456 posts (total: 13,209)
   # Day 3: +1,123 posts (total: 14,332)
   # ...
   ```

2. **每周生成积累报告** (每周1小时)
   ```python
   # backend/scripts/generate_weekly_accumulation_report.py (新增)
   """生成每周数据积累报告"""
   
   def generate_weekly_report():
       """生成每周数据积累报告"""
       # 1. 数据池规模变化
       # 2. 每日增长趋势图
       # 3. 社区覆盖度变化
       # 4. 抓取成功率统计
       # 5. 质量指标变化
   ```

3. **监控抓取任务成功率** (持续)
   ```bash
   # 每天检查
   psql -c "SELECT 
       DATE(created_at) as date,
       COUNT(*) as total_tasks,
       SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) as succeeded,
       ROUND(100.0 * SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
   FROM crawl_metrics
   WHERE created_at >= NOW() - INTERVAL '7 days'
   GROUP BY DATE(created_at)
   ORDER BY date DESC"
   ```

4. **监控 Redis 缓存命中率** (持续)
   ```bash
   # 每天检查
   redis-cli INFO stats | grep keyspace_hits
   redis-cli INFO stats | grep keyspace_misses
   ```

#### 验收标准

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

# 抓取成功率
# 预期: ≥80%

# 缓存命中率
# 预期: ≥70%
```

#### 产出物

- ✅ 每日监控报告（自动化）
- ✅ 每周积累报告（7 份）
- ✅ 数据池规模 ≥20,000
- ✅ 社区覆盖度 ≥100
- ✅ `reports/phase-log/phase013-phase2-week{N}.md` 周报

---

### Phase 3 – 数据质量优化 (P1 - 5天)

**目标**: 修复 Evidence/Sentiment/Competitor 三个质量缺口

#### 3.1 修复 Evidence URL 格式 (2天)

```python
# backend/scripts/backfill_real_evidence.py (新增)
"""从 posts_hot 回溯真实证据"""

def backfill_real_evidence(task_id: str = None):
    """修复 Evidence URL 格式错误"""
    # 1. 读取 insight_cards 和 evidences
    # 2. 根据 subreddit 匹配 posts_hot
    # 3. 提取真实 URL 和 excerpt
    # 4. 更新 evidences 表
    # 5. 验证 URL 可访问性
```

#### 3.2 添加 Neutral 情感类别 (2天)

```python
# backend/app/services/analysis/sentiment.py (扩展)
"""添加 neutral 情感类别"""

def classify_sentiment_with_neutral(text: str) -> str:
    """基于 TextBlob polarity 添加 neutral 类别"""
    polarity = TextBlob(text).sentiment.polarity
    
    # 弱情绪阈值
    if abs(polarity) < 0.1:
        return "neutral"
    elif polarity > 0:
        return "positive"
    else:
        return "negative"
```

#### 3.3 竞品分层多源汇总 (1天)

```python
# backend/app/services/analysis/competitor_layering.py (扩展)
"""竞品分层多源汇总"""

def aggregate_competitor_layers():
    """从多个数据源汇总竞品分层"""
    # 1. 从 YAML 读取基础分层
    # 2. 从 posts_hot 统计品牌提及频率
    # 3. 从 community_pool 读取标签
    # 4. 合并并按频率分层
    # 5. 确保 ≥2 层
```

#### 验收标准

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
```

#### 产出物

- ✅ `backend/scripts/backfill_real_evidence.py`
- ✅ `backend/scripts/check_evidence_quality.py`
- ✅ `backend/app/services/analysis/sentiment.py` (扩展)
- ✅ `backend/app/services/analysis/competitor_layering.py` (扩展)
- ✅ `backend/scripts/content_acceptance.py` (更新)
- ✅ `reports/phase-log/phase013-phase3.md` 验收报告

---

### Phase 4 – 验收与文档 (P1 - 2天)

**目标**: 完整闭环验收，生成 Phase 013 报告

#### 任务清单

1. **完整闭环验收** (4小时)
   ```bash
   # 执行完整验收流程
   make crossborder-acceptance
   
   # 验证所有步骤成功
   # 1. discover-crossborder
   # 2. pool-init
   # 3. pool-import-top1000
   # 4. semantic-build-L1
   # 5. crossborder-high-value
   ```

2. **质量门禁验证** (2小时)
   ```bash
   # 执行质量门禁
   make content-acceptance
   
   # 验证评分 ≥90
   cat reports/local-acceptance/content-acceptance-latest.json | jq '.score'
   ```

3. **生成 Phase 013 报告** (4小时)
   ```markdown
   # reports/phase-log/phase013.md
   
   ## Phase 013 验收报告
   
   ### 执行摘要
   - 启动时间: 2025-11-12
   - 完成时间: 2025-12-17
   - 总耗时: 35 天
   - 状态: ✅ 全部通过
   
   ### 里程碑达成
   - M0: Celery Beat 启动 ✅
   - M1: 社区池扩充完成 ✅
   - M2: 数据积累 Week 1 ✅
   - M3: 数据积累 Week 2 ✅
   - M4: 质量优化完成 ✅
   - M5: 完整闭环验收 ✅
   
   ### 关键指标
   - 数据池规模: 30,245 条 (目标 20,000+) ✅
   - 社区池规模: 312 个 (目标 300+) ✅
   - Evidence 可用性: 96.3% (目标 95%+) ✅
   - Neutral 占比: 23.5% (目标 10-40%) ✅
   - Competitor 分层: 2.4 层 (目标 ≥2) ✅
   - Content Acceptance: 92 分 (目标 ≥90) ✅
   ```

4. **更新文档** (2小时)
   - 更新 README.md
   - 创建 quickstart.md
   - 创建 monitoring.md

#### 验收标准

```bash
# 1. 所有里程碑达成
cat reports/phase-log/phase013.md | grep "✅"
# 预期: 6 个 ✅

# 2. 所有关键指标达标
cat reports/phase-log/phase013.md | grep "目标"
# 预期: 所有指标 ✅

# 3. 文档完整
ls .specify/specs/013-legacy-quality-gap/
# 预期: spec.md, plan-v2.md, tasks.md, quickstart.md, monitoring.md
```

#### 产出物

- ✅ `reports/phase-log/phase013.md` 完整验收报告
- ✅ `.specify/specs/013-legacy-quality-gap/quickstart.md`
- ✅ `.specify/specs/013-legacy-quality-gap/monitoring.md`
- ✅ README.md 更新
- ✅ 所有验收标准通过

---

## Success Criteria

### 整体验收标准

| 指标 | 当前值 | 目标值 | 实际值 | 状态 |
|------|--------|--------|--------|------|
| Celery Beat 运行 | ❌ | ✅ | - | 待验收 |
| 每日新增帖子 | 0 | ~1,500 | - | 待验收 |
| 数据池规模 | 10,519 | 20,000+ | - | 待验收 |
| 社区池规模 | 200 | 300+ | - | 待验收 |
| Evidence 可用性 | 0% | 95%+ | - | 待验收 |
| Neutral 占比 | 0% | 10-40% | - | 待验收 |
| Competitor 分层 | 0 | ≥2 | - | 待验收 |
| Content Acceptance | 60% | 90%+ | - | 待验收 |

---

## Next Steps

1. ✅ 创建 tasks.md 详细任务清单
2. ✅ 开始 Phase 0 实施
3. ✅ 每日监控数据积累
4. ✅ 每周生成进度报告

---

**文档状态**: ✅ Ready for Implementation  
**下次更新**: Phase 0 完成后更新实际值  
**最后更新**: 2025-11-12

