# Reddit Signal Scanner 自动化系统启动确认

**启动时间**: 2025-10-17 17:04:00  
**状态**: ✅ 运行中  
**模式**: 完全自动化（开机自启 + 定时抓取 + 健康监控）

---

## 📊 系统运行状态

### 核心服务

| 服务 | 状态 | 进程数 | 说明 |
|------|------|--------|------|
| **Celery Worker** | ✅ 运行中 | 1 | 任务执行器 |
| **Celery Beat** | ✅ 运行中 | 1 | 定时调度器 |
| **Redis** | ✅ 运行中 | 1 | 消息队列 |
| **PostgreSQL** | ✅ 运行中 | 1 | 数据库 |

**总进程数**: 8 个 Celery 相关进程

### 数据库状态

| 指标 | 数值 |
|------|------|
| 社区总数（community_pool） | 0 |
| 帖子总数（冷库 posts_raw） | 12,068 |
| 帖子总数（热缓存 posts_hot） | 12,063 |
| 最近抓取时间 | 2025-10-17 15:29:29 |

**注意**: 社区总数为 0 是因为数据在 `community_cache` 表中，不在 `community_pool` 表。

---

## ⏰ 自动化任务调度

### 数据抓取任务（4 个）

| 任务名称 | 执行频率 | 目标社区 | 说明 |
|---------|---------|---------|------|
| **crawl-tier1-communities** | 每 2 小时 | Tier 1（高优先级） | priority ≥ 80 |
| **crawl-tier2-communities** | 每 6 小时 | Tier 2（中优先级） | priority 50-79 |
| **crawl-tier3-communities** | 每天 02:20 | Tier 3（低优先级） | priority < 50 |
| **targeted-recrawl-low-quality** | 每 4 小时 | 低质量社区 | 精准补抓 |

### 监控任务（7 个）

| 任务名称 | 执行频率 | 说明 |
|---------|---------|------|
| **monitor-api-calls** | 每 1 分钟 | 监控 API 调用频率 |
| **monitor-cache-health** | 每 5 分钟 | 监控缓存健康状态 |
| **monitor-crawler-health** | 每 10 分钟 | 监控爬虫健康状态 |
| **monitor-e2e-tests** | 每 10 分钟 | 监控 E2E 测试 |
| **monitor-warmup-metrics** | 每 15 分钟 | 监控预热期指标 |
| **collect-test-logs** | 每 5 分钟 | 收集测试日志 |
| **update-performance-dashboard** | 每 15 分钟 | 更新性能仪表板 |

---

## 🔄 自动重启机制

### Crontab 配置

```cron
# Reddit Signal Scanner - Celery Auto-Restart
# Start Celery services on reboot (wait 30 seconds for system to stabilize)
@reboot sleep 30 && /Users/hujia/Desktop/RedditSignalScanner/scripts/start_celery_services.sh >> /Users/hujia/Library/Logs/reddit-scanner/cron.log 2>&1

# Health check every 5 minutes, restart if needed
*/5 * * * * /Users/hujia/Desktop/RedditSignalScanner/scripts/celery_health_check.sh --all >> /Users/hujia/Library/Logs/reddit-scanner/cron.log 2>&1 || /Users/hujia/Desktop/RedditSignalScanner/scripts/start_celery_services.sh >> /Users/hujia/Library/Logs/reddit-scanner/cron.log 2>&1
```

**功能**:
- ✅ 系统重启后 30 秒自动启动 Celery
- ✅ 每 5 分钟健康检查
- ✅ 检查失败时自动重启服务
- ✅ 所有操作记录到日志

---

## 📝 日志文件

### 日志位置

| 日志类型 | 路径 | 说明 |
|---------|------|------|
| **Worker 日志** | `~/Library/Logs/reddit-scanner/celery-worker.log` | 任务执行日志 |
| **Beat 日志** | `~/Library/Logs/reddit-scanner/celery-beat.log` | 定时调度日志 |
| **Cron 日志** | `~/Library/Logs/reddit-scanner/cron.log` | 自动重启日志 |

### 最近任务执行记录

```
[2025-10-17 17:00:00] monitor-api-calls: ✅ succeeded (0.006s)
[2025-10-17 17:00:00] monitor-warmup-metrics: ✅ succeeded (0.036s)
[2025-10-17 17:00:00] monitor-cache-health: ✅ succeeded
[2025-10-17 17:00:00] monitor-e2e-tests: ✅ succeeded
[2025-10-17 17:00:00] update-performance-dashboard: ✅ succeeded
[2025-10-17 17:00:00] monitor-crawler-health: ✅ succeeded
```

**所有监控任务正常执行中！**

---

## 🔍 监控命令

### 查看系统状态

```bash
# 查看 Celery 进程
pgrep -afl celery

# 健康检查
bash /Users/hujia/Desktop/RedditSignalScanner/scripts/celery_health_check.sh --all

# 查看 Crontab 配置
crontab -l | grep -A 3 "Reddit Signal Scanner"
```

### 查看日志

```bash
# 实时查看 Worker 日志
tail -f ~/Library/Logs/reddit-scanner/celery-worker.log

# 实时查看 Beat 日志
tail -f ~/Library/Logs/reddit-scanner/celery-beat.log

# 实时查看 Cron 日志
tail -f ~/Library/Logs/reddit-scanner/cron.log

# 查看最近 50 行 Worker 日志
tail -50 ~/Library/Logs/reddit-scanner/celery-worker.log
```

### 查看数据库状态

```bash
# 查看社区和帖子数量
psql -d reddit_scanner -c "
SELECT 
    '社区总数' as metric, COUNT(*)::text as value FROM community_cache
UNION ALL
SELECT 
    '帖子总数（冷库）', COUNT(*)::text FROM posts_raw
UNION ALL
SELECT 
    '帖子总数（热缓存）', COUNT(*)::text FROM posts_hot
UNION ALL
SELECT 
    '最近抓取时间', MAX(created_at)::text FROM posts_raw;
"

# 查看最近抓取的帖子
psql -d reddit_scanner -c "
SELECT 
    subreddit,
    title,
    created_at
FROM posts_raw
ORDER BY created_at DESC
LIMIT 10;
"
```

---

## 🛠️ 管理命令

### 启动/停止服务

```bash
# 手动启动 Celery（如果未运行）
bash /Users/hujia/Desktop/RedditSignalScanner/scripts/start_celery_services.sh

# 停止所有 Celery 进程
pkill -f celery

# 重启 Celery
pkill -f celery && sleep 2 && bash /Users/hujia/Desktop/RedditSignalScanner/scripts/start_celery_services.sh
```

### 使用 Makefile

```bash
# 查看所有可用命令
make help

# 启动完整开发环境（黄金路径）
make dev-golden-path

# 启动后端服务
make dev-backend

# 启动前端服务
make dev-frontend

# 运行测试
make test-all
```

---

## 📈 预期行为

### 每日数据抓取

**高优先级社区（Tier 1）**:
- 执行时间: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00
- 频率: 每 2 小时
- 预计抓取: 12 次/天

**中优先级社区（Tier 2）**:
- 执行时间: 00:10, 06:10, 12:10, 18:10
- 频率: 每 6 小时
- 预计抓取: 4 次/天

**低优先级社区（Tier 3）**:
- 执行时间: 02:20
- 频率: 每天 1 次
- 预计抓取: 1 次/天

**低质量社区补抓**:
- 执行时间: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
- 频率: 每 4 小时
- 预计抓取: 6 次/天

### 监控任务

- **API 调用监控**: 每分钟检查一次，确保不超过 55 次/分钟
- **缓存健康监控**: 每 5 分钟检查一次，确保 Redis 正常
- **爬虫健康监控**: 每 10 分钟检查一次，确保爬虫正常
- **E2E 测试监控**: 每 10 分钟运行一次，确保系统端到端正常

---

## ✅ 验证清单

- [x] Celery Worker 运行中
- [x] Celery Beat 运行中
- [x] Redis 运行中
- [x] PostgreSQL 连接正常
- [x] Crontab 自动重启已配置
- [x] 健康检查脚本可用
- [x] 日志文件正常生成
- [x] 监控任务正常执行
- [x] 数据库有历史数据（12,068 条帖子）
- [x] Makefile 语法错误已修复

---

## 🎯 下一步建议

1. **观察 24 小时**: 监控系统运行情况，确认定时任务按预期执行
2. **检查数据增长**: 明天同一时间检查帖子数量是否增加
3. **查看日志**: 定期查看日志，确认没有错误
4. **测试重启**: 可选择性测试机器重启后是否自动恢复

---

## 📞 故障排查

### 问题 1: Celery 进程未运行

**检查**:
```bash
pgrep -afl celery
```

**解决**:
```bash
bash /Users/hujia/Desktop/RedditSignalScanner/scripts/start_celery_services.sh
```

### 问题 2: 定时任务未执行

**检查**:
```bash
tail -50 ~/Library/Logs/reddit-scanner/celery-beat.log
```

**解决**: 查看日志中的错误信息，确认 Beat 进程正在运行

### 问题 3: 数据未增长

**检查**:
```bash
psql -d reddit_scanner -c "SELECT MAX(created_at) FROM posts_raw;"
```

**解决**: 查看 Worker 日志，确认抓取任务是否执行成功

---

**报告生成时间**: 2025-10-17 17:04:00  
**系统状态**: ✅ 完全自动化运行中  
**下次检查建议**: 2025-10-18 17:00:00（24 小时后）

