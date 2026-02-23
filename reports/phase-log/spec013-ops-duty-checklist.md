# Spec 013 运维值班清单

**参考**: `.specify/specs/013-legacy-quality-gap/ops-runbook.md` 第12节  
**创建日期**: 2025-11-12  
**适用范围**: Day 1 至数据积累达标

---

## 📅 每日值班流程

### 08:00 早间巡检
```bash
# 快速巡检
bash scripts/daily_ops_check.sh morning

# 或手动执行
make posts-growth-7d
make celery-meta-count
```

**检查重点**:
- ✅ 所有服务运行正常
- ✅ 日增数据趋势
- ✅ Redis 任务痕迹增长

**记录**: 将输出保存到 `reports/phase-log/daily-check-YYYYMMDD-morning.txt`

---

### 12:00 中午快照
```bash
# 完整快照
bash scripts/daily_ops_check.sh noon

# 或手动执行
make pipeline-health
```

**检查重点**:
- ✅ Celery Beat 调度正常
- ✅ 社区池统计
- ✅ 缓存命中率

**记录**: 快照自动保存到 `reports/phase-log/daily-check-YYYYMMDD-*.txt`

---

### 18:00 晚间确认
```bash
# 晚间巡检
bash scripts/daily_ops_check.sh evening

# 或手动执行
make posts-growth-7d
make pool-stats
```

**检查重点**:
- ✅ 今日目标达成情况
- ✅ 是否需要执行提拉策略
- ✅ 自愈日志检查

**记录**: 更新 `reports/phase-log/spec013-daily-summary.md`

---

## 🚨 异常处理

### 场景1: 日增 <1,000 条
**触发条件**: 连续2天日增 <1,000 条

**处理步骤**:
```bash
# 1. 检查 Celery Beat 是否正常
ps aux | grep "celery.*beat"

# 2. 检查最近的抓取任务
tail -100 backend/tmp/celery_beat.log

# 3. 执行提拉策略（扩池）
make discover-crossborder LIMIT=10000
make import-crossborder-pool
make pool-stats

# 4. 验证池规模
# 预期: 池规模增加 100-200 个
```

**记录**: 在 `reports/phase-log/spec013-ops-incidents.md` 记录异常和处理

---

### 场景2: Celery Beat 停止
**触发条件**: `ps aux | grep "celery.*beat"` 无输出

**处理步骤**:
```bash
# 1. 检查日志
tail -50 backend/tmp/celery_beat.log

# 2. 重启 Beat
make celery-beat-restart

# 3. 验证重启成功
sleep 5
ps aux | grep "celery.*beat"

# 4. 检查调度恢复
tail -20 backend/tmp/celery_beat.log | grep "Scheduler"
```

**记录**: 在 `reports/phase-log/spec013-ops-incidents.md` 记录重启时间和原因

---

### 场景3: 自愈守护失败
**触发条件**: `ps aux | grep autoheal` 无输出

**处理步骤**:
```bash
# 1. 检查自愈日志
tail -50 reports/local-acceptance/autoheal.log

# 2. 重启自愈守护
make autoheal-start

# 3. 验证重启成功
ps aux | grep autoheal
```

**记录**: 在 `reports/phase-log/spec013-ops-incidents.md` 记录失败原因

---

### 场景4: Redis 任务痕迹不增长
**触发条件**: 连续2小时 `celery-meta-count` 无变化

**处理步骤**:
```bash
# 1. 检查 Celery Worker
ps aux | grep "celery.*worker"

# 2. 检查 Worker 日志
tail -100 backend/tmp/celery_worker.log

# 3. 检查 Redis 连接
redis-cli ping

# 4. 如需重启 Worker
make celery-worker-restart
```

**记录**: 在 `reports/phase-log/spec013-ops-incidents.md` 记录问题和解决方案

---

## 📊 SLO 达成监控

### 3天目标
- **阶段目标**: 20,000 条
- **3天目标**: ≥12,000 条（60%）
- **日均需求**: ≥4,000 条

### 监控方法
```bash
# 查询最近3天总数
psql -d reddit_signal_scanner -c "
SELECT COUNT(*) as total_3d
FROM posts_hot
WHERE created_at >= NOW() - INTERVAL '3 days'
"

# 查询每日增长
make posts-growth-7d
```

### 达成判断
- ✅ **达标**: 3天累计 ≥12,000 条
- ⚠️ **偏低**: 3天累计 8,000-12,000 条 → 执行提拉策略
- ❌ **未达标**: 3天累计 <8,000 条 → 紧急扩池 + 节奏调优

---

## 🔧 提拉策略执行

### 优先级1: 扩池（语义优先）
```bash
# 1. 发现新社区
make discover-crossborder LIMIT=10000

# 2. 评分（可选，耗时较长）
# make score-crossborder INPUT=backend/data/crossborder_candidates.json LIMIT=1777 TOPN=200

# 3. 导入池
make import-crossborder-pool

# 4. 验证
make pool-stats
# 预期: 池规模增加 100-200 个
```

### 优先级2: 节奏调优（谨慎）
⚠️ **仅在池已充足但日增仍 <1,000 时执行**

```bash
# 1. 检查当前配置
cat backend/config/crawler.yml | grep -A 5 "tier_config"

# 2. 调整 T3 频率（从 6h 改为 4h）
# 手动编辑 backend/config/crawler.yml

# 3. 重启 Celery Beat
make celery-beat-restart

# 4. 验证调度更新
tail -20 backend/tmp/celery_beat.log
```

⚠️ **注意**: 保持 `REDDIT_MAX_CONCURRENCY=2`，不激进

---

## 📝 每日总结模板

### 文件: `reports/phase-log/spec013-daily-summary.md`

```markdown
# Spec 013 每日运维总结

## YYYY-MM-DD

### 数据增长
- 今日新增: XXX 条
- 7天累计: XXX 条
- 日均: XXX 条
- 状态: ✅/⚠️/❌

### 服务健康
- Redis: ✅/❌
- Celery Worker: ✅/❌
- Celery Beat: ✅/❌
- 自愈守护: ✅/❌

### 社区池
- 总数: XXX 个
- 新增: XXX 个
- 状态: ✅/⚠️/❌

### 异常事件
- 无 / 详见 spec013-ops-incidents.md

### 执行动作
- 无 / 执行了提拉策略 / 重启了服务

### 下一步
- 继续监控 / 执行扩池 / 调整节奏
```

---

## 🎯 达标退出条件

当满足以下所有条件时，可退出密集监控，转为常规监控：

1. ✅ 连续7天日增 ≥1,000 条
2. ✅ 数据池规模 ≥20,000 条（30天）
3. ✅ 社区池规模 ≥300 个
4. ✅ Celery Beat 稳定运行 ≥7天
5. ✅ 无重大异常事件

**转为常规监控**:
- 每日巡检改为每周巡检
- 快照频率降低为每周1次
- 继续执行自愈守护

---

## 📁 相关文件

- 运维手册: `.specify/specs/013-legacy-quality-gap/ops-runbook.md`
- 巡检脚本: `scripts/daily_ops_check.sh`
- 自愈脚本: `scripts/autoheal.sh`
- 快照脚本: `scripts/pipeline_health_snapshot.sh`
- 日志目录: `backend/tmp/*.log`
- 报告目录: `reports/phase-log/`

---

**文档状态**: ✅ Ready for Use  
**适用期**: Day 1 至数据积累达标  
**最后更新**: 2025-11-12

