# Phase 521 - Live 门禁双重化 + 300行硬门禁落地

## 1) 发现了什么

- 现有 `live_report_preflight_gate.py` 只检查队列积压，没有检查 DB 真相源健康，导致“数据池异常”也可能继续跑 live。
- 当前 Dev 库真实快照（本次实测）显示：
  - `active_pool_count=1`
  - `active_pool_category_map_coverage_ratio=0.0`
  - `recent_posts_llm_label_coverage_ratio=0.0`
  - 同时 backlog stale 很高
- 结论：当前问题不是“偶发 prompt 漂移”，而是“门禁层没有拦住坏输入状态”。

## 2) 是否需要修复

- 需要，且必须是 P0。
- 不修复会持续出现“靠运气验收”的假稳定。

## 3) 精确修复方法

- 重构 preflight 为双门禁：
  - 队列门禁（原有）
  - DB 真相源门禁（新增）
- 新增 DB 指标：
  - `active_pool_count`
  - `active_pool_with_cache_count`
  - `active_pool_cache_gap_ratio`
  - `active_pool_missing_categories_count`
  - `active_pool_category_map_coverage_ratio`
  - `recent_posts_count`
  - `recent_posts_llm_label_coverage_ratio`
- 修改文件：
  - `backend/scripts/acceptance/live_report_preflight_core.py`（新）
  - `backend/scripts/acceptance/live_report_preflight_gate.py`（改为轻量 CLI 包装）
  - `makefiles/test.mk`（接入新门禁参数）
- 新增测试：
  - `backend/tests/scripts/acceptance/test_live_report_preflight_gate.py`

## 4) 下一步系统性计划

1. 先把 preflight 输出里暴露的真实 DB 问题修到“门禁通过”（不是降阈值）。
2. 再跑 `acceptance-live-smoke` / `acceptance-live-final`，验证主链稳定。
3. 最后跑 warzone/topic-profile 横向矩阵，做跨主题复验。

## 5) 这次执行的价值

- 把“坏数据状态也能开跑”的系统漏洞堵上了。
- 验收链路从“运行即成功”升级为“状态健康才允许运行”。
- 同时落地了代码习惯硬门禁：改动文件默认 `<=300` 行。

## 附：300行硬门禁

- 新增：
  - `backend/scripts/quality/check_file_length_gate.py`
  - `backend/config/quality_gates/file_length_allowlist.txt`
- 接入：
  - `makefiles/test.mk` 增加 `test-file-length-gate`
  - `acceptance-offline-gate` 前置执行该门禁
- 当前策略：
  - `scope=changed` + 非回归校验（历史超长文件只记录在 allowlist，不允许新增超长文件）
