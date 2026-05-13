# Phase 828 - 首页 all 首屏旧缓存顶替最新 release 修复

## 发现

- 用户真机截图显示首页 `all` 第一张分别出现：
  - `breakdown`：`有用户把保命装备当钥匙扣，一用十几年`
  - `signal`：`Etsy 卖家开始先庆祝小里程碑，不再先抱怨流量波动`
- 但当前最新 release `release-d982bc4849eb` 的真实首页前 10 张里：
  - 第 1 张是 `hot`
  - 上述两张分别在第 `5`、`10` 位
- 说明问题不是 display-order 规则失效，而是首页首屏在真机上先渲染了旧的 `all` 列表缓存。

## 根因

- `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx` 会优先读取 `getCachedCardList(cardType)`。
- `hotpost-mini/hotpost-mini-app/src/pages/index/card-list-cache.ts` 的缓存键只有 `cardType`，没有 release/version 维度。
- 首页默认 tab 是 `all`，所以旧 release 的 `all` 列表会先顶到首屏，随后才异步刷新。
- 对首页首屏来说，这种策略会制造“规则正确但用户先看到旧排序”的假象。

## 修复

- 只改首页首屏缓存策略，不改 publish plan / prompt / named topic / schema。
- 在 `index.tsx` 中新增：
  - `const allowImmediateCache = cardType !== 'all'`
  - `all` tab 首屏不再直接吃缓存，始终先请求最新列表。
- 其他 tab（`validate` / `write` / `hot`）继续保留缓存策略，避免整体体验倒退。

## 验证

- 重新执行：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp:prod`
- 结果：
  - 生产构建通过
  - 开发态 `watch` 已停，不再覆盖 `dist`

## 结论

- 当前问题不是首页 display-order winner 配错，也不是 cloud_db 数据没更新。
- 真正缺口是：首页 `all` 首屏不该先渲染旧缓存。
- 该问题已在前端主链修复，后续真机应以最新 release 顺序直接出首屏。
