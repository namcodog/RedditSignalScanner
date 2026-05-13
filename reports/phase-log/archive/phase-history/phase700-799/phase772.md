# Phase 772 - 近期爆帖详情卡二次收敛

## 发现

- 上一轮虽然给 `getCardDetail` 增加了单卡直查，但 `miniRelease/index.js` 入口仍然在动作分支前先执行 `loadSnapshot(db)`。
- 这意味着详情页请求进入云函数后，仍会先整包加载当前 release，再去查单卡，前一轮优化没有真正切断详情页的重路径。

## 结果

- 已把 `miniRelease` 云函数入口改成：
  - `getCardDetail` 先分支处理
  - 仅详情请求走 `loadCardDetail(db, cardId)`
  - 只有列表类动作才会执行 `loadSnapshot(db)`
- 现有云函数单测继续通过：
  - `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`

## 下一步

- 本轮只需要重新部署 `miniRelease` 云函数。
- 重新部署后，真机只验证：
  - 首页 -> 近期爆帖 -> 任意卡片详情
