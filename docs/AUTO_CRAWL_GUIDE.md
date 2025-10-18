# 24 小时自动抓取系统使用指南

## 🚀 快速启动

### 首次启动（推荐）

```bash
make warmup-clean-restart
```

这个命令会：
1. 强制停止所有现有的 Celery 进程
2. 清理 PID 文件
3. 验证清理结果
4. 重新启动干净的系统

### 常规启动

```bash
make warmup-start
```

适用于系统已经干净停止的情况。

---

## 📊 系统功能

### 自动抓取

系统会按照分级策略自动抓取 Reddit 社区数据：

- **Tier 1 (高质量社区)**: 每 2 小时抓取一次
  - 时间: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00

- **Tier 2 (中等质量社区)**: 每 6 小时抓取一次
  - 时间: 00:00, 06:00, 12:00, 18:00

- **Tier 3 (低质量社区)**: 每 24 小时抓取一次
  - 时间: 每天 00:00

### 自动监控

- **API 调用监控**: 每 1 分钟检查一次，确保不超过限额
- **缓存健康监控**: 每 5 分钟检查一次缓存命中率
- **系统指标收集**: 每 15 分钟收集一次系统运行指标

### 数据存储

抓取的数据会自动存储到以下数据库表：

- `posts_raw`: 原始帖子数据（冷存储，永久保存）
- `posts_hot`: 热门帖子缓存（热存储，定期更新）
- `community_cache`: 社区缓存元数据（记录抓取状态）
- `crawl_metrics`: 抓取指标记录（监控数据质量）

---

## 🔍 监控与管理

### 查看系统状态

```bash
make warmup-status
```

显示：
- Redis 运行状态
- Celery Worker 进程状态
- Celery Beat 进程状态
- 最近的定时任务执行记录

### 查看日志

**查看历史日志**（最近 50 行）：
```bash
make warmup-logs
```

**实时查看日志**：
```bash
# Worker 日志（任务执行）
tail -f /tmp/celery_worker.log

# Beat 日志（定时调度）
tail -f /tmp/celery_beat.log
```

### 查看详细说明

```bash
make warmup-info
```

显示完整的系统说明、时间表和使用建议。

---

## 🛑 停止系统

### 常规停止

```bash
make warmup-stop
```

优雅地停止 Celery Worker 和 Beat 进程。

### 强制清理

如果遇到进程无法停止的情况：

```bash
make warmup-clean-restart
```

这会强制杀死所有 Celery 进程并重新启动。

---

## 💡 使用建议

### 1. 首次启动

第一次启动系统时，建议使用：

```bash
make warmup-clean-restart
```

这样可以确保没有遗留的进程干扰。

### 2. 日常使用

系统启动后，您只需要：
- ✅ 保持网络连接
- ✅ 保持电脑开机
- ✅ 让 Redis 保持运行

系统会自动完成所有抓取、存储和监控工作。

### 3. 定期检查

建议每天检查一次系统状态：

```bash
make warmup-status
```

如果发现异常，查看日志：

```bash
make warmup-logs
```

### 4. 遇到问题

如果发现：
- 重复的进程
- 任务不执行
- 日志报错

执行清理重启：

```bash
make warmup-clean-restart
```

---

## 🔧 常见问题

### Q1: 如何确认系统在工作？

**A**: 查看日志，等待下一个整点（例如 02:00），您会看到类似这样的日志：

```
[2025-10-18 02:00:00] Scheduler: Sending due task crawl-tier1-communities
[2025-10-18 02:00:05] Task tasks.crawler.crawl_tier received
[2025-10-18 02:00:10] ✅ r/technology: 抓取成功，获得 50 个帖子
```

### Q2: 系统会一直运行吗？

**A**: 是的，只要：
- 电脑保持开机
- 网络保持连接
- Redis 保持运行
- Celery 进程没有崩溃

系统会 24/7 自动运行。

### Q3: 如何查看抓取了多少数据？

**A**: 连接数据库查询：

```bash
# 查看总帖子数
psql $DATABASE_URL -c "SELECT COUNT(*) FROM posts_raw;"

# 查看最近 1 小时的抓取
psql $DATABASE_URL -c "SELECT COUNT(*) FROM posts_raw WHERE created_at > NOW() - INTERVAL '1 hour';"

# 查看抓取指标
psql $DATABASE_URL -c "SELECT * FROM crawl_metrics ORDER BY metric_date DESC LIMIT 10;"
```

### Q4: 系统占用资源多吗？

**A**: 正常情况下：
- CPU: 空闲时 < 5%，抓取时 10-20%
- 内存: 约 200-500 MB
- 网络: 取决于抓取频率，平均 < 1 MB/s

### Q5: 可以修改抓取频率吗？

**A**: 可以，编辑 `backend/app/core/celery_app.py` 中的 `beat_schedule` 配置，然后重启系统：

```bash
make warmup-clean-restart
```

---

## 📋 Makefile 命令总结

| 命令 | 说明 | 使用场景 |
|------|------|---------|
| `make warmup-start` | 启动系统 | 常规启动 |
| `make warmup-stop` | 停止系统 | 常规停止 |
| `make warmup-restart` | 重启系统 | 常规重启 |
| `make warmup-clean-restart` | 清理并重启 | 首次启动、遇到问题 |
| `make warmup-status` | 查看状态 | 检查运行状态 |
| `make warmup-logs` | 查看日志 | 查看历史日志 |
| `make warmup-info` | 查看说明 | 了解系统详情 |

---

## 🎯 最佳实践

1. **首次启动**: 使用 `make warmup-clean-restart`
2. **日常检查**: 每天执行一次 `make warmup-status`
3. **问题排查**: 先查看 `make warmup-logs`，再考虑重启
4. **定期维护**: 每周执行一次 `make warmup-clean-restart` 清理可能的僵尸进程
5. **数据验证**: 定期查询数据库确认数据在增长

---

## 📞 技术支持

如果遇到无法解决的问题：

1. 查看日志文件：`/tmp/celery_worker.log` 和 `/tmp/celery_beat.log`
2. 检查 Redis 状态：`redis-cli ping`
3. 检查数据库连接：`psql $DATABASE_URL -c "SELECT 1;"`
4. 查看进程状态：`ps aux | grep celery`

---

**最后更新**: 2025-10-18  
**版本**: 1.0.0

