# Phase 576 - 收掉 recrawl 调度旧口径并完成社区层真相源结案审计

## 发现了什么？

在最后一轮横向审计里，还剩一条真正会影响抓取资格的旧判断：

- `backend/app/services/crawl/recrawl_scheduler.py`

它之前还通过：

- `community_pool.is_active`
- `community_pool.is_blacklisted`

来决定“哪些社区应该进入低质量补采名单”。

如果不改，这条补采链还是会把旧表资格带回主链。

## 是否需要修复？

需要，而且这轮已经完成。

## 精确修复方法

- 文件：
  - `backend/app/services/crawl/recrawl_scheduler.py`
  - `backend/tests/services/crawl/test_recrawl_scheduler.py`

### 本轮调整

- `find_low_quality_candidates()` 改成只通过 truth-source 判定正式资格：
  - `community_registry.is_enabled`
  - `community_runtime_state.is_enabled`
  - `community_runtime_state.crawl_status in ('active', 'needs_backfill')`
  - `community_domain_membership.is_current`
  - `community_governance_decision.decision = 'approved'`
- `community_cache` 继续只承担：
  - `last_crawled_at`
  - `avg_valid_posts`
  这类运行投影指标

### 验证

- `SKIP_DB_RESET=1 python -m pytest backend/tests/services/crawl/test_recrawl_scheduler.py -q`
- 结果：`1 passed`

- `python -m py_compile backend/app/services/crawl/recrawl_scheduler.py backend/tests/services/crawl/test_recrawl_scheduler.py`
- 结果：通过

## 当前审计结论

截至这轮，社区层还保留旧表引用的地方，已经只剩 4 类：

1. 后台管理 / 运营界面
   - 例如 `admin_community_pool.py`
   - 作用：列表展示、筛选、人工维护
   - 不是主链正式判断

2. bootstrap / 恢复 / reconciliation 工具
   - 例如：
     - `truth_source_reconciler.py`
     - `truth_source_batch_service.py`
     - `gold_dev_community_restore_service.py`
     - `dev_truth_source_compaction_service.py`
   - 作用：迁移、恢复、对账
   - 本来就需要读旧表

3. 兼容投影 / 指标展示
   - 例如：
     - `crawl_metrics_service.py`
     - `reports.py` 里的 `tier / priority` 展示
   - 作用：展示或统计
   - 不再定义正式资格

4. 运营建议 / 非主链智能层
   - 例如：
     - `tier_intelligence.py`
     - `tier_intelligence_task.py`
   - 作用：给运营生成调级建议
   - 不直接决定社区是否进入抓取主链

## 这次执行的价值是什么？达到了什么目的？

到这一步，社区层“会影响真实抓取、分析、语义、报告的正式判断链”已经收干净了。

可以把这条线按下面这句话结案：

- 社区层主链正式判断：`100%` 切到唯一真相源
- 剩余旧表引用：仅限后台、投影、迁移工具、运营建议，不再参与主链正式资格判断
