## 这轮达到的目的

把“什么时候停”正式收进 SOP，并按这条双重停机规则真实跑完一轮 all-scope 出卡链。

## 当前状态变化

- 本轮新增发布 `4` 张，最新 release = `release-dfc7383d1f14`
- 第 3 轮标准链已跑到：`dry_cycles = 3`、`yield_exhausted = true`、`actual_total = 0`
- 当前停机原因已固定成：采集侧耗尽 + 发布侧无新卡，不再按张数停

## 还没完成什么

- `publish-until-exhausted` 仍是运行纪律，不是自动整夜循环器
- 下一波 fresh inventory 什么时候再长出来，还要靠后续真实 collect 继续看

## 下一步做什么

- 后续继续按同一条 all-scope 标准链出卡
- 只要重新出现净新增价值，就继续发；否则继续按双重停机条件停
