# Phase 763 - 已发布语义刷新提速

时间：2026-04-11 10:30 CST

## 发现

- 当前已发布 `signal` 共 `48` 张。
- 已完成语义刷新 `9` 张，剩余约 `39` 张。
- 旧版 `refresh_published_card_semantics.py` 在 dry-run 阶段是逐张串行刷新：
  - `for item in selected`
  - `await refresh_published_card_semantics(item)`
- 真正慢的不是 apply，而是 dry-run 逐张等 LLM。

## 修复

- 给 CLI 增加受控并发参数：
  - `--workers`
  - 默认值 `3`
- dry-run / live generation 现在走有上限并发：
  - 保留结果顺序
  - 不改变 plan-first 合同
  - `apply-plan` 仍然只读 plan，不吃并发参数

## 验证

- `python -m py_compile backend/scripts/hotpost/refresh_published_card_semantics.py`
- `pytest backend/tests/scripts/hotpost/test_refresh_published_card_semantics.py -q --tb=short -p no:schemathesis`

结果：

- 编译通过。
- 脚本测试 `5 passed`。
- 新增验证：
  - `--workers <= 0` 会直接失败
  - 并发刷新下返回顺序不乱

## 判断

- 按旧节奏，如果每批最终只落 `3` 张，`39` 张剩余量大约还要 `10` 批。
- 现在先把 dry-run 提速后，建议切到：
  - 每次 dry-run 先跑 `8-10` 张
  - 从中筛 `5-7` 张过线卡进入 apply-plan
- 这样总批次数可以从大约 `10` 批，压到大约 `6` 批左右。
