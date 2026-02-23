# Phase 013 · Legacy Quality Gap（闭环记录）

日期: $(date)

## 统一反馈四问

1) 发现了什么问题/根因？
- 数据池不增长：`posts_hot` 最近30天仅约1万+，明显低于目标。根因是持续抓取未常驻运行（Celery Beat缺少统一启动入口，团队难以一键开启与核查）。
- 现状可观测性不足：缺少“最近7天增长曲线”、“任务执行痕迹”一键脚本；定位困难。
- 社区池扩充执行门槛：虽有 `pool-import-top1000`/`semantic-refresh-pool`，但缺少在规范流程中的明确指引与校验步骤。

2) 是否已精确定位？
- 是。代码中 Beat 调度与任务齐备（`backend/app/core/celery_app.py` 已配置多项调度），但 Make 命令未提供“Beat 常驻”快捷入口；开发日常容易只启动 Worker/Backend 而忘记 Beat。

3) 精确修复方法？
- 新增 `make dev-celery-beat`：后台启动 Celery Beat + Worker（日志落盘 `backend/tmp/*`）。
- 新增观测脚本/命令：
  - `make posts-growth-7d`：输出最近7天 `posts_hot` 日增量（CSV）。
  - `make celery-meta-count`：统计 Redis 中 `celery-task-meta-*` 数量，验证任务是否在跑。
- 预埋“每周社区发现”任务（可控开关）：`tasks.discovery.discover_new_communities_weekly`（默认跳过，`CRON_DISCOVERY_ENABLED=1` 时生效），后续可纳入 Beat。

4) 下一步做什么？
- Day 0（今天）：
  - 启动调度：`make dev-celery-beat`。
  - 观察增长：每小时跑 `make posts-growth-7d`，确认曲线抬升；`make celery-meta-count` 观察元数据增长。
- Phase 1（2-3天）：
  - 执行池扩充：`make pool-import-top1000` → `make semantic-refresh-pool` → `make pool-stats`。
  - 达到每日新增 1,000–1,500 帖子基线。
- Phase 2（3-5天）：
  - 评估并按需开启 `CRON_DISCOVERY_ENABLED=1`，每周自动发现补充长尾（Beat 纳入或人工触发）。

5) 这次修复的效果/结果？
- 预期 24–72 小时内：`posts_hot` 日增量明显增加；Redis/Celery 元数据出现稳定增长；7天后 `posts_hot` 总量 ≥ 10,000+
 级别，继续逼近 20k/40k 阶段目标，为 Spec 013 后续质量项（Evidence URL 修复、中性情感、竞品分层）创造可靠数据面。

## 本次提交内容（与代码路径）

- 新增 Make 入口：
  - `make dev-celery-beat`（makefiles/celery.mk: 追加目标）
  - `make posts-growth-7d`（makefiles/ops.mk: 新增目标；backend/scripts/posts_growth_7d.py）
  - `make celery-meta-count`（makefiles/ops.mk: 新增目标）
  - `make pipeline-health`（端到端快照）
  - `make autoheal-start`（本地自愈守护，失败自动重启 Beat+Worker）
- 预埋任务：`backend/app/tasks/discovery_task.py`（默认跳过，需 `CRON_DISCOVERY_ENABLED=1`）
- 明确帮助文案：`Makefile` help 新增相关命令说明。
 - 可靠性加固：`backend/app/core/celery_app.py` 加入 acks_late/reject_on_worker_lost/visibility_timeout/result_expires 等，Beat schedule 持久化（backend/scripts/start_warmup_crawler.sh）。

## 使用指引（核查用）

- 启动调度：
  - `make redis-start`
  - `make dev-celery-beat`
- 数据增长核查：
  - `make posts-growth-7d`
  - `make celery-meta-count`
- 扩充社区池：
  - `make pool-import-top1000`
  - `make semantic-refresh-pool`
  - `make pool-stats`

## 备注

- Beat 调度条目已在 `backend/app/core/celery_app.py` 配置齐全；若确认需要，也可将 `tasks.discovery.discover_new_communities_weekly` 纳入 Beat（建议数据稳定后再开启）。
