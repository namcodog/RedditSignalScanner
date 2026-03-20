# Phase 247 - Round 1 数据采集层深度复核

执行时间: 2026-03-13

## 1. 发现了什么

- 按 `系统全量审计扫描计划.md` 复核 Round 1 后，确认数据采集层的高风险仍然集中在 3 个文件：`crawl_execute_task.py`、`comments_ingest.py`、`crawler_task.py`。
- 旧的 `audit_round_1.md` 有两个数字口径需要纠正：
  - Round 1 可执行文件实际是 **21 个**，不是 20 个。`services/crawl/` 真实是 17 个非 `__init__` 文件，再加 `tasks/` 4 个目标文件。
  - `comments_ingest.py` 的 UPSERT SQL 常量真实是 **12 个**，不是 16 个；风险依旧高，只是数字要改准。
- 采集层不是普遍失控。`data_collection.py` 这种模块结构清楚，说明可以做**点状治理**，不用全层重构。

## 2. 是否需要修复

- 需要，但这轮只做深度审计，不动代码。
- 优先级建议仍是：
  - P0: `crawl_execute_task.py`
  - P0: `comments_ingest.py`
  - P1: `crawler_task.py`

## 3. 精确修复方法

### 3.1 P0 - `crawl_execute_task.py`

- 问题 1：黑名单安全检查失败会被静默吞掉。
  - 证据：`backend/app/tasks/crawl_execute_task.py:668-700`
  - 风险：如果 `community_pool` 查询异常，任务会继续执行，等于把“黑名单保护”降级成 best-effort。
- 问题 2：完成态写库失败会被静默吞掉，但函数仍然返回成功。
  - 证据：`backend/app/tasks/crawl_execute_task.py:1140-1148`
  - 风险：调用方看到 success，数据库里的 target 却可能还停在 `running` 或未完成状态，后续补偿/重试会乱。
- 建议：
  - 提取统一的 `_safe_commit_or_rollback()` / `_record_target_failure()`。
  - 黑名单检查失败不要 `pass`，至少要记录并转成显式失败态。
  - `complete_crawler_run_target()` 失败不能继续返回成功结果。

### 3.2 P0 - `comments_ingest.py`

- 问题 1：当 schema 要求 `comments.post_id` 且关联帖子查不到时，整批评论会直接 `return 0`，没有日志。
  - 证据：`backend/app/services/crawl/comments_ingest.py:575-591`
  - 风险：评论整批丢弃，外层只会看到“处理了 0 条”，很难分辨是空数据还是 FK 关联失败。
- 问题 2：UPSERT 语句和分支组合仍然膨胀。
  - 证据：文件内 `COMMENT_UPSERT_SQL_*` 常量共 12 个；执行分支集中在 `648-692`。
  - 风险：后面再加列，必须同时改 SQL 常量和分支选择，极容易漏。
- 建议：
  - `post_id is None` 时改成显式告警/失败计数，不要静默返回。
  - 用 `_build_comment_upsert_sql(has_expires, has_post_id, has_crawl_run_id, has_community_run_id)` 这类生成器替代常量排列。

### 3.3 P1 - `crawler_task.py`

- 问题：调度层的部分异常被当成“正常没抢到锁/正常回退”处理，但没有日志。
  - 证据：`backend/app/tasks/crawler_task.py:172-189`
  - 现象：advisory lock 获取或释放异常时，代码只会把 `acquired=False` 或直接 `pass`。
  - 风险：真实的 DB 错误、锁异常、连接问题，会伪装成普通竞争，排查时看不到现场。
- 附加观察：
  - 文件内 `type: ignore` 共有 9 处，类型系统对任务装饰器和部分依赖基本失守。
- 建议：
  - 这类调度兜底仍然可以保留，但至少补 `logger.warning`。
  - 后面单独做一轮 Celery/SQLAlchemy 类型修正，把 `type: ignore` 往下压。

## 4. 健康样本

- `backend/app/services/crawl/data_collection.py`
  - `collect_posts()` 的缓存 -> hot -> cold -> API 回退链路清楚，异常也基本有日志。
  - 说明 Round 1 的问题是**集中爆点**，不是整层代码都同样糟。

## 5. 验证依据

- Serena 符号概览:
  - `crawl_execute_task.py`：24 个函数，`_execute_target_impl` 单函数 630 行
  - `comments_ingest.py`：3 个函数，UPSERT 常量集中
  - `crawler_task.py`：32 个函数，调度/规划/派发职责混在一个大文件
- 定量扫描:
  - `crawl_execute_task.py`: 1168 行 / 60 个 `except` / 15 处 SQL
  - `comments_ingest.py`: 728 行 / 9 个 `except` / 18 处 SQL 文本
  - `crawler_task.py`: 1696 行 / 42 个 `except` / 9 个 `type: ignore`

## 6. 这次执行的价值

- 这次不是重复旧报告，而是把 Round 1 的口径重新校准了。
- 我确认了真正该优先修的不是“except 数量”本身，而是：
  - **静默吞掉会改变状态机结果的异常**
  - **会让数据整批消失的静默返回**
  - **会让 schema 维护继续爆炸的 SQL 排列**
