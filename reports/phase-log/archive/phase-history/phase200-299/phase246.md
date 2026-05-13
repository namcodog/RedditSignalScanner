# Phase 246 - embedding_task NOW() 治理补漏

执行时间: 2026-03-12

## 1. 发现了什么

- 额外排查时发现 `backend/app/tasks/embedding_task.py` 里还有 2 处数据库侧时间窗，分别在评论高分样本查询和长尾样本查询里。
- 这两处虽然不在主报告链路里，但继续留着会让“关键链路禁止数据库当前时间函数”的门禁口径不完整。
- 同时顺手看到这个文件里还有 `ORDER BY random()`，它也是独立的非确定性来源。不过这次只按新增需求收口时间窗，没有扩大到抽样策略重构。

## 2. 是否需要修复

- 需要，已经修掉。
- 这次不只改 SQL，还把门禁范围扩到了 `embedding_task.py`，避免以后又长回来。

## 3. 精确修复方法

- 在 `embedding_task.py` 新增 `_comment_cutoff_utc(lookback_days)`，统一用 Python 先算 UTC 截止时间。
- `_fetch_missing_comments()` 里两条 SQL 都改成 `c.created_utc >= :cutoff_utc`。
- `Makefile` 的 `check-determinism` 扩到 `backend/app/tasks/embedding_task.py`。
- `backend/tests/services/report/test_determinism_regression.py` 新增 `test_no_now_in_embedding_task`。

## 4. 验证结果

- `python -c "import ast; ast.parse(open('backend/app/tasks/embedding_task.py').read()); print('✅ embedding_task AST OK')"` -> 通过
- `rg -n "NOW\\(\\)" backend/app/tasks/embedding_task.py` -> 无命中
- `make check-determinism` -> 通过
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_determinism_regression.py -v` -> `5 passed`
- `SKIP_DB_RESET=1 make test-quality-gate` -> `24 passed`

## 5. 这次执行的价值

- 确定性门禁从“报告主链路”进一步补齐到 embedding backfill 任务，协议更完整了。
- 以后再有人把数据库当前时间函数写回这个文件，`make check-determinism` 和回归测试会直接拦住。
- 另外留下一条后续线索：`ORDER BY random()` 还在，后面如果要继续收紧 embedding 抽样的可复现性，可以直接从这里入手。
