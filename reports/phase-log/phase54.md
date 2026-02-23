# phase54：落地第4/8/9 + comments 统一收口（验毒回填 / warzone / semantic_rules / backfill_comments）

## 这次要解决什么
把 Key 拍板的 4 个块一次性落地，并且不把 DB 越改越乱：

- 第4：新社区先“验毒回填 30 天（有硬配额）”，回填完成后才评估/入池
- 第8：warzone（8 战区）规则版归类，能解释、能筛选
- 第9：语义回流口径以 `semantic_rules(term)` 为唯一真相（candidate→active 也要写进 semantic_rules）
- comments：评论回填也要纳入 `CrawlPlan → execute_target` 的 partial/补偿体系

## 做了哪些落地改动（代码）

### 1) 第4：candidate 验毒回填链路（先回填、后评估）
- 新增 `backend/app/services/discovery/candidate_vetting_service.py`
  - `ensure_candidate_vetting_backfill(...)`：对 `discovered_communities.status=pending` 自动下单一组 `backfill_posts`（reason=`candidate_vetting`，`budget_cap=true`）
  - `check_vetting_and_trigger_evaluation(...)`：当所有切片 targets 都 `completed/partial` 时，触发单社区评估 `tasks.discovery.evaluate_community`
- `backend/app/tasks/discovery_task.py`
  - `tasks.discovery.evaluate_community`：单社区评估入口
  - `tasks.discovery.check_candidate_vetting`：验毒完成聚合检查入口
  - `run_community_evaluation` 增加“先确保验毒回填”的预处理（幂等，不重复下单）
- `backend/app/services/discovery/evaluator_service.py`
  - 评估前强制 gate：`DISCOVERY_REQUIRE_VETTING=1` 时，vetting 没完成直接 `skipped`
  - 优先用 DB 样本（`posts_raw`）评估，不足才回退 Reddit API
  - 写回 metrics 改为 merge（不再覆盖掉 vetting/warzone 字段）
- `backend/app/tasks/crawl_execute_task.py`
  - backfill_posts 且 reason=`candidate_vetting` 时，target 结束后会 best-effort 触发 `tasks.discovery.check_candidate_vetting`

### 2) comments 统一进执行器（backfill_comments）
- `backend/app/services/crawl/plan_contract.py`：补齐 `plan_kind=backfill_comments` 合同校验（必须 `target_type=post_ids` + `comments_limit>0` + `meta.subreddit`）
- `backend/app/services/crawl/execute_plan.py`
  - 新增 `plan_kind=backfill_comments` 执行分支：统一 `reddit_client.fetch_post_comments → persist_comments`
  - 支持 `meta.label_after_ingest=true` 时做评论打标（保持原功能不丢）
- `backend/app/tasks/comments_task.py`
  - `comments.fetch_and_ingest` / `comments.backfill_full` 改为：只生成 plan + enqueue `tasks.crawler.execute_target`
  - `comments.backfill_recent_full_daily` 同样改为下单 targets（不再在任务里直抓直写）

### 3) 第8：warzone 归类 v0
- 新增规则词典：`backend/config/warzones.yaml`
- 新增 `backend/app/services/discovery/warzone_classifier.py`（规则版、可解释）
- `backend/app/services/crawl/execute_plan.py`（probe 执行器）
  - probe 执行完会 best-effort 把 warzone_guess 写回 `discovered_communities.metrics.warzone` 并追加 `tags=warzone:<name>`

### 4) 第9：语义回流口径收口到 semantic_rules(term)
- `backend/app/repositories/semantic_candidate_repository.py`
  - candidate 产生时：同步写入 `semantic_rules`（concept=`candidate_terms`，rule_type=`candidate_term`，`is_active=false`）
  - candidate 审核通过时：把同一条 rule 切成 `is_active=true`（semantic_rules 成为运行时唯一真相）

## 新增/更新的测试
- `backend/tests/services/test_candidate_vetting_service.py`
- `backend/tests/services/test_plan_contract_backfill_comments.py`
- `backend/tests/services/test_backfill_comments_executor.py`
- `backend/tests/services/test_warzone_classifier.py`
- `backend/tests/services/test_semantic_repositories.py`：增强断言（approved 必须落到 `semantic_rules`）

## 关键开关（默认值）
- `DISCOVERY_CANDIDATE_VETTING_ENABLED=1`：pending 自动验毒回填
- `DISCOVERY_REQUIRE_VETTING=1`：评估前必须 vetting completed
- `DISCOVERY_VETTING_DAYS=30` / `DISCOVERY_VETTING_SLICE_DAYS=7` / `DISCOVERY_VETTING_TOTAL_POSTS_BUDGET=300`

## 验收（我本地跑过的命令）
- `pytest -q backend/tests/services/test_candidate_vetting_service.py`
- `pytest -q backend/tests/services/test_plan_contract_backfill_comments.py`
- `pytest -q backend/tests/services/test_backfill_comments_executor.py`
- `pytest -q backend/tests/services/test_warzone_classifier.py`
- `pytest -q backend/tests/services/test_probe_search_executor.py::test_probe_search_writes_evidence_posts_and_upserts_discovered_communities_idempotently`
- `pytest -q backend/tests/services/test_probe_hot_executor.py`
- `pytest -q backend/tests/services/test_semantic_repositories.py`

## 对外口径（给 Key / 工程师）
- 新社区：先下单 `candidate_vetting` 回填 targets，跑完再评估，评估通过才入池/巡航
- comments：不再有“单独体系”，全部走 `execute_target`
- warzone：规则版先跑起来，写回 discovered_communities，后续再做更聪明的模型版
- 语义：运行时只认 `semantic_rules(is_active=true)`；candidate→active 也要同步到 semantic_rules

