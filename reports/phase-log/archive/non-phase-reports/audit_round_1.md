# System Audit — Round 1: 数据采集层深度审计报告

> **日期**: 2026-03-13
> **方法**: Serena 符号级分析 + Sequential Thinking 综合诊断 + 定量指标扫描
> **范围**: `services/crawl/` 17 文件 + `tasks/` 4 文件 = 共 20 个文件

---

## 一、全量扫描结果

| 文件 | 行数 | 裸SQL | except | type:ignore | Serena 结构 | 风险 |
|------|------|-------|--------|-------------|------------|------|
| `crawl_execute_task.py` | 1,168 | 13 | **60** | 3 | 23 函数，630行单函数 `_execute_target_impl` | 🔴 |
| `crawler_task.py` | 1,696 | 9 | **43** | **9** | 30 函数 + 16 常量，`_crawl_seeds_impl` 内嵌子函数 | 🟡 |
| `incremental_crawler.py` | 1,587 | 11 | 16 | 0 | `IncrementalCrawler` 类 18 方法，含双写逻辑 | 🟢 |
| `execute_plan.py` | 797 | 4 | 13 | 0 | `execute_crawl_plan` 内嵌 3 子函数 | 🟢 |
| `comments_ingest.py` | 728 | **18** | 9 | 0 | **16 个 UPSERT SQL 常量排列爆炸** | 🔴 |
| `comments_task.py` | 582 | 1 | 7 | 1 | 8 个 Celery task 各嵌 `_run` 子函数 | 🟢 |
| `data_collection.py` | 408 | 0 | 7 | 0 | `DataCollectionService` 11 方法，清晰 | 🟢 |
| `crawler_run_targets_service.py` | 280 | 9 | 0 | 0 | 纯 SQL 服务 | 🟢 |
| `ingest_task.py` | 273 | 0 | 7 | 2 | `_ingest_jsonl_backfill_impl` 嵌 `_flush` | 🟢 |
| `comments_parser.py` | 269 | 0 | 3 | 0 | 解析函数 | 🟢 |
| `search_sharder.py` | 179 | 1 | 3 | 0 | 搜索分片 | 🟢 |
| `plan_contract.py` | 154 | 0 | 0 | 0 | Pydantic 模型 | 🟢 |
| `community_discovery_v2.py` | 151 | 0 | 2 | 0 | 发现逻辑 | 🟢 |
| `crawl_plan.py` | 143 | 0 | 1 | 0 | `CrawlPlanBuilder` 5 方法 | 🟢 |
| `common.py` | 105 | 0 | 0 | 0 | 工具函数 | 🟢 |
| `recrawl_scheduler.py` | 86 | 0 | 0 | 0 | 调度器 | 🟢 |
| `adaptive_crawler.py` | 81 | 0 | 0 | 0 | `AdaptiveCrawler` 3 方法 | 🟢 |
| `adaptive_scheduler.py` | 78 | 0 | 1 | 0 | 自适应调度 | 🟢 |
| `time_slicer.py` | 66 | 0 | 0 | 0 | 时间切片 | 🟢 |
| `crawler_runs_service.py` | 72 | 3 | 0 | 0 | 运行记录 | 🟢 |

---

## 二、深层诊断（Sequential Thinking）

### 🔴 风险 #1: `crawl_execute_task.py` — 缺少统一异常处理框架

**本质问题**: 不是 except 多，而是**同一个模式被复制了 ~15 次**。

重复的模式：
```python
try:
    await partial_crawler_run_target(session, ...)
    await session.commit()
except Exception:
    try:
        await session.rollback()
    except Exception:
        pass
```

这个 try-fail-rollback-compensate 组合在 timeout / rate_limit / general_error / community_locked / schema_mismatch 五个分支中几乎一模一样。

**影响**: 如果要加日志/改回滚策略/加监控，必须改 15 处。
**建议**: 提取 `_safe_db_op(session, coro)` 和 `_record_failure(session, target_id, reason, metrics)` 两个工具函数。

---

### 🔴 风险 #2: `comments_ingest.py` — 16 个 SQL UPSERT 排列爆炸

**本质问题**: 4 个布尔条件的全排列产生了 16 个 SQL 常量：

```
has_expires × has_post_id × has_run_id × has_run_ids = 2⁴ = 16
```

每个常量是一个完整的 INSERT...ON CONFLICT 语句。任何字段变更要改 16 处。

**Serena 确认的 16 个常量名**:
- `COMMENT_UPSERT_SQL_WITH_EXPIRES`
- `COMMENT_UPSERT_SQL_NO_POST_ID_WITH_EXPIRES`
- `COMMENT_UPSERT_SQL_WITH_EXPIRES_AND_RUN_ID`
- `COMMENT_UPSERT_SQL_WITH_EXPIRES_AND_RUN_IDS`
- ... (共 16 个)

**建议**: 替换为 `_build_upsert_sql(has_expires, has_post_id, has_run_id)` 动态生成函数。

---

### 🟡 风险 #3: `crawler_task.py` — type:ignore 集中 + 高 except

**type:ignore 9 处**: 集中在 Celery task 签名和 SQLAlchemy session 的类型不兼容。mypy --strict 对这些区域实际上是放行的。

**except 43 处**: 大部分是调度层的防御性捕获（任务失败不能让调度器崩溃），属于**可接受的模式**，不算 bug —— 但缺少 logger.warning 记录。

---

## 三、健康的模块（无需治理）

以下 17 个文件均结构清晰、风险低：
- `incremental_crawler.py` — 大但结构好，18 方法各司其职
- `execute_plan.py` — 网络层 except 合理
- `data_collection.py` — 最干净的服务之一
- `plan_contract.py` — 纯 Pydantic 模型
- 其余 13 个 <300 行的工具/服务文件

---

## 四、结论

| 优先级 | 模块 | 问题 | 建议治理方式 |
|--------|------|------|------------|
| 🔴 P0 | `crawl_execute_task.py` | 异常处理模式 ×15 重复 | 提取 `_safe_db_op()` + `_record_failure()` |
| 🔴 P0 | `comments_ingest.py` | 16 个 SQL 排列爆炸 | 改为 `_build_upsert_sql()` 动态生成 |
| 🟡 P1 | `crawler_task.py` | except 缺少日志 + type:ignore | 加 `logger.warning` + 类型修正 |
| 🟢 — | 其余 17 文件 | 健康 | 无需操作 |

**数据采集层总体评价**: 20 个文件中 17 个健康（85%），2 个高风险集中在异常处理和 SQL 维护性，1 个中风险在类型安全。核心写入路径（`incremental_crawler`）结构良好。
