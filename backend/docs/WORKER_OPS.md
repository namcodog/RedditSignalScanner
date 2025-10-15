# Celery Worker 运维手册（Day 4 / PRD-04）

## 启动 Worker

```bash
make celery-start ARGS="--concurrency 2"
```

默认队列为 `analysis_queue`，脚本会自动校验 Redis / PostgreSQL 连接并生成唯一 hostname。

## 验证 Worker 状态

```bash
celery -A app.core.celery_app inspect active
celery -A app.core.celery_app inspect stats
```

也可以使用

```bash
make celery-verify
```

检查路由配置、Broker、Result backend。

## 创建/清理测试任务

```bash
make celery-seed              # 创建默认测试任务
make celery-seed-unique       # 创建随机邮箱的测试任务
make celery-purge             # 清理脚本生成的测试数据
```

## 常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| Worker 无法连接 Redis | 检查 `CELERY_BROKER_URL` / `TASK_STATUS_REDIS_URL` 是否指向可达实例；本地可使用 `redis-cli ping` 验证。 |
| Worker 启动后无任务 | 确认 API 层已入队任务；查看 `backend/app/tasks/analysis_task.py` 日志或执行 `celery -A app.core.celery_app inspect reserved`。 |
| 任务进度一直停留在 0% | 查看 Redis `task-status:{task_id}` 缓存是否更新；若缓存缺失，可执行 `make celery-seed` 再触发任务，或检查 Celery 日志中是否有异常。 |
| DuplicateNodenameWarning | Day4 起脚本已自动附带唯一 hostname。如需多实例，可通过 `make celery-start ARGS="--hostname analysis@node-1"` 显式设置。 |
