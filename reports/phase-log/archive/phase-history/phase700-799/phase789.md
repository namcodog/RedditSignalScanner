# phase789 - offline publish plan 缩量 lane target 修复

## 本轮目标

修复 `backend/app/services/hotpost/offline_publish_plan.py` 在 `limit < 30` 时的 lane target 缩量逻辑。

目标不是改 prompt，也不是改 lane 定义，而是让离线投影重新回到 key-os 的编排合同：

- `limit=10` 时不再输出 `signal=0 / hot=5 / breakdown=5`
- 而是收敛到：
  - `signal = 5`
  - `hot = 3`
  - `breakdown = 2`

## 实际改动

- `backend/app/services/hotpost/offline_publish_plan.py`
  - 重写 `_resolve_lane_targets()` 的缩量逻辑
  - 从“先把 overflow 从 signal 开始砍掉”改成：
    - 先按 lane 配额份额缩放
    - 再做四舍五入
    - 如总数超出目标，从大头 lane 回扣
    - 如总数不足目标，再按剩余份额补齐
- `backend/tests/services/hotpost/test_offline_publish_plan.py`
  - 新增两个硬断言：
    - `30 -> 17 / 8 / 5`
    - `10 -> 5 / 3 / 2`

## 修复前后

### 修复前

- `offline_publish_plan(limit=10)` 输出：
  - `signal = 0`
  - `hot = 5`
  - `breakdown = 5`

根因：

- 当前配置 lane target 是 `18 / 8 / 5`
- 旧逻辑在总量超出时，按固定顺序先从 `signal` 直接往下砍
- 结果缩到 `10` 时，把 `signal` 先砍成了 `0`

### 修复后

- `offline_publish_plan(limit=10)` 输出 target：
  - `signal = 5`
  - `hot = 3`
  - `breakdown = 2`

新的 publish_list 结果：

- `signal = 5`
- `hot = 3`
- `breakdown = 2`

## 验证

- 测试：
  - `2 passed`
- 本地离线命令：
  - `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 10 --output backend/tmp/offline-publish-plan.json`
- 结果：
  - lane target 已回到合同口径
  - publish_list 仍然完全基于本地库存
  - 没有调用 Reddit API

## 发布链影响

- 本轮没有改 prompt
- 没有改 signal/hot/breakdown lane 定义
- 没有改 schema
- 没有重建 release
- 当前 release 仍是：
  - `release-6fb115e4b88a`

## 结论

- `limit < 30` 的编排投影逻辑已修正到 key-os 合同口径。
- 当前下一步不该再争论“为什么 signal 没露出来”，因为这次真正的缩量 bug 已经修掉了。
