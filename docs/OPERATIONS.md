# Reddit Signal Scanner – 运维手册 (Day 11)

> 适用对象：Backend B / DevOps / 值班工程师  
> 上游文档：`docs/PRD/PRD-07-Admin后台.md`、`docs/PRD/PRD-04-任务系统.md`、`docs/2025-10-10-质量标准与门禁规范.md`  
> 验收依据：Day 11 任务「文档完善 + 部署准备」(`reports/phase-log/DAY10-12-EXECUTION-CHECKLIST.md`)

---

## 1. 服务拓扑概览
```
用户 -> Frontend (React SPA @ app.example.com)
      -> Backend API (FastAPI @ /api/*)
            -> PostgreSQL 15 (主库)
            -> Redis 7 (缓存 + Celery Broker)
            -> Celery Workers (分析任务队列)
            -> External Reddit API (受速率限制)
```

| 组件 | 位置 | 说明 | 运维责任 |
| --- | --- | --- | --- |
| Frontend | Nginx/Vercel | 静态文件，SSE 客户端 | DevOps |
| Backend | uvicorn/gunicorn | FastAPI 服务，含 Admin API | Backend B |
| Celery | systemd service | 分析流水线执行 | Backend B |
| Redis | Managed / 自建 | 任务队列 + 缓存 | DevOps |
| PostgreSQL | Managed / 自建 | 业务数据 | DBA / Backend B |

---

## 2. 运行状态监控

### 2.1 必备监控指标
| 服务 | 指标 | 目标阈值 | 监控工具建议 |
| --- | --- | --- | --- |
| Backend | HTTP 5xx < 1%, P95 < 500ms | Prometheus + Grafana / CloudWatch | 
| Celery | active_tasks, failed_tasks | 活跃 <= 20, 失败=0 | Celery Flower / custom exporter |
| Redis | used_memory_mb, hit_rate | 内存<80%, 命中率>70% | Redis INFO / Prometheus redis_exporter |
| PostgreSQL | connections, slow_queries | 连接<100, 慢查询=0 | pg_stat_activity / pmm |
| Frontend | LCP / error rate | LCP<2.5s, error rate<1% | Web Vitals / Sentry |

### 2.2 健康检查脚本
```bash
# Backend
curl -f http://localhost:8006/api/healthz

# Celery queue size
redis-cli -n 0 llen celery

# Worker活跃状态
celery -A app.core.celery_app.celery_app inspect active
```

---

## 3. 日常运维流程

### 3.1 每日开班
1. 检查 `systemctl status rss-backend rss-celery`
2. `redis-cli ping`，`psql -c "SELECT 1"`
3. 运行 `make test-admin-e2e` (预发布环境) —— 验证 Admin 面板
4. 记录结果于 `reports/phase-log/phase{N}.md`

### 3.2 日常巡检
- API 日志无批量 5xx (`journalctl -u rss-backend`)
- Celery 日志无 `Task failed` (`journalctl -u rss-celery`)
- Redis keyspace hits/misses 正常
- PostgreSQL `pg_stat_activity` 无长事务
- 前端 Sentry/Dashboard 无高频报错

### 3.3 版本更新流程
1. 在 staging 环境执行部署手册 Step 1-8
2. 运行：`pytest`、`npm test -- --run`、`make test-e2e`、`make test-admin-e2e`
3. QA 验收通过后再推进生产
4. 生产发布：窗口内执行部署手册 Step 4-7
5. 发布后 30 分钟密切观察指标

---

## 4. 故障排查手册

### 4.1 Backend 5xx 激增
1. `journalctl -u rss-backend -n 200`
2. 检查依赖 (PostgreSQL/Redis) 是否可访问：
   - `psql <DATABASE_URL> -c "SELECT 1"`
   - `redis-cli ping`
3. 若为应用异常，记录堆栈，紧急回滚至上一版本

### 4.2 Celery 任务堆积
1. `redis-cli -n 0 llen celery`
2. `celery -A app.core.celery_app.celery_app inspect active`
3. 若 worker 掉线 → `sudo systemctl restart rss-celery`
4. 若外部 Reddit API 限流 → 暂停流量，调整 `reddit_rate_limit` 配置

### 4.3 Admin Dashboard 空数据
1. 确认 `ADMIN_EMAILS` 设置正确，`test-admin-e2e` 是否通过
2. 后端 API `/api/admin/dashboard/stats` cURL 调试
3. 检查数据库 `analysis` / `tasks` 表是否有数据
4. 检查 Celery 是否正常写入结果

### 4.4 数据库连接失败
1. `psql` 手动连接测试
2. 查看 PostgreSQL 日志（`/var/log/postgresql/postgresql-15-main.log`）
3. 检查连接池配置（`POOL_SIZE`）是否过高
4. 必要时 Failover 至备用数据库

### 4.5 Redis 内存飙升
1. `redis-cli info memory` -> 确认 `used_memory_human`
2. 清理过期缓存：`redis-cli FLUSHDB`（需确认后执行）
3. 调整缓存 TTL (`reddit_cache_ttl_seconds`)
4. 考虑升级 Redis 实例或开启持久化

---

## 5. 数据备份 & 恢复

### 5.1 PostgreSQL
- 定时任务：`pg_dump -Fc reddit_scanner > backup.dump`
- 恢复：`pg_restore -d reddit_scanner backup.dump`
- 建议使用 WAL 归档提升恢复点目标 (RPO)

### 5.2 Redis
- 如使用自建实例，开启 `save 900 1`，定期备份 `dump.rdb`
- 恢复：将旧的 `dump.rdb` 放入数据目录，重启 Redis

---

## 6. 性能指标 & 优化建议
| 指标 | 目标 | 监控位置 | 优化手段 |
| --- | --- | --- | --- |
| 分析耗时 | <270s | `make test-e2e` 输出 | 增加并发、缓存命中率>60% (PRD-03) |
| SSE 延迟 | <3s | 浏览器 Network | 调整 `TASK_STREAM_POLL_INTERVAL` |
| API P95 | <500ms | API Gateway / Prometheus | 添加索引、优化查询 |
| Redis 命中率 | >70% | `redis-cli info stats` | 调整缓存 TTL / key 粒度 |

---

## 7. 升级 / 变更记录
- **Day 11**: 创建运维手册 v1.0（当前文档）
- 待添加：上线后实际巡检经验、性能调优参数、告警阈值

---

## 8. 联系方式 & 升级链路
- **值班负责人**: Backend B
- **备份**: QA Agent (验证脚本)、Frontend Agent (Admin UI)
- **通报渠道**: Slack #rss-production、Email ops@example.com

出现紧急情况请先通知 Lead 并记录于 `reports/phase-log/phase{N}.md`。
