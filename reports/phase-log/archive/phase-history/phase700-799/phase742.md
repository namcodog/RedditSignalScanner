# Phase 742

## 时间

- 2026-04-10 00:22:46 CST

## 本轮目标

- 把 `1.0` 验收口径从“精选刊物”改成“密度优先 + 讲人话优先”
- 让调度器真正按新的 `1.0` 目标工作，而不是文档和代码继续打架

## 实际完成

1. 更新 `1.0` 合同
   - [docs/superpowers/specs/2026-04-09-v1-density-first-contract.md](/Users/hujia/Desktop/RedditSignalScanner/docs/superpowers/specs/2026-04-09-v1-density-first-contract.md)
   - 明确：
     - 用户每次来，应该能刷到足够多的卡，而不是看精选周报
     - 每天至少 `5` 次上新
     - 每次至少新增 `6` 张卡
     - 每天累计至少新增 `30` 张卡

2. 更新稳态运营 SOP
   - [docs/sop/2026-04-09-稳态运营成功SOP.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2026-04-09-%E7%A8%B3%E6%80%81%E8%BF%90%E8%90%A5%E6%88%90%E5%8A%9FSOP.md)
   - 把运营窗口从“最近 `20` 张”切到“最近 `30` 张”
   - 新目标改成：
     - lane：`18 / 8 / 4`
     - scope：`10 / 10 / 10`

3. 更新真实调度目标
   - [backend/config/hotpost_supply_discovery_v2.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_supply_discovery_v2.yaml)
   - `global_rules.rolling_publish_mix` 已改成：
     - `window_size = 30`
     - `lane_targets = signal 18 / hot 8 / breakdown 4`
     - `scope_targets = 10 / 10 / 10`

4. 修测试
   - [backend/tests/services/hotpost/test_card_selection_policy.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_card_selection_policy.py)
   - 让测试口径跟新目标对齐

## 验证

- `cd backend && pytest tests/services/hotpost/test_card_selection_policy.py -q`
  - `6 passed`

- 当前真实最近 `30` 张：
  - lane：`signal=24 / hot=5 / breakdown=1`
  - scope：`AI=12 / 增长=10 / 电商=8`

## 本轮结论

- 这轮不是只改了文档，调度器已经开始按 `1.0` 新口径工作
- 真实问题也更清楚了：
  - 不是信息太少
  - 是 `signal` 仍然吃掉窗口
  - `hot + breakdown` 供给仍然不够

## 下一步

1. 不再继续补 `signal`
2. 优先补 `hot + breakdown`
3. 把“每天 5 次上新、每天至少 30 张新增”从合同继续推进到真实运营节奏
