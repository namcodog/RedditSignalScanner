# 小程序数据资产保护规划

日期：2026-05-03

## 目标

保护已经上线的小程序内容资产，重点不是承诺“完全防爬”，而是把直接批量搬走数据的成本抬高，并让异常行为能被发现、限速、阻断。

当前最该保护的资产：

- 详情页完整内容：`detail / quotes / source_link / source_module`。
- 最新发布快照：当前小程序快照为 `release-c0a4c90f59bb`，共 `572` 张卡。
- 用户行为和积分状态：`mini_users / mini_user_points_ledger / mini_user_events / mini_user_favorites`。

## 当前审核结论

### P0：详情数据出口没有服务端保护

`miniRelease.getCardDetail` 现在直接按 `cardId` 返回完整详情，没有读取 `OPENID`，也没有在云函数内做积分扣减、已购校验或限速。

证据：

- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/index.js:12` 直接调用 `loadCardDetail(db, event.cardId)`。
- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js:56` 按最新 `release_id + card_id` 查询详情并返回。
- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js:230` 返回完整 `item`，其中包含详情、quotes、source link 等字段。

这意味着：只要拿到卡片 id，就可以绕过前端页面和积分系统，直接调用云函数批量拿详情。

### P0：积分保护发生在前端流程之后

详情页当前流程是：先请求详情，再调用 `miniPoints.consumeDetail` 扣积分。

证据：

- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx:84` 先执行 `getCardDetail(cardId)`。
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx:88` 后执行 `consumeDetailPoints(detail.card_id, detail.title)`。
- `hotpost-mini/hotpost-mini-app/src/services/access-meter.ts:19` 只用本地登录状态判断是否能看详情。

这类保护只能约束正常用户界面，不能约束直接调用云函数的人。

### P1：列表可以被顺序分页拉完

列表接口有分页上限，但没有用户维度限速。当前 `feed_contract.max_page_size=30`，总量 `572` 张，理论上二十次左右请求就能拉完主数据的摘要层。

证据：

- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js:127` 支持 cursor 分页。
- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js:135` 只限制 page size，不限制请求频率。
- `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx:51` 首页还会预取其它 tab 的列表，正常体验更快，但也扩大了批量拉取面。

列表摘要本来可以开放，但需要限速和行为记录，否则容易被完整复制。

### P1：事件日志不足以做反爬判断

`miniEvents` 目前记录的是前端主动上报事件，而且失败会被吞掉；服务端没有把每次 `listCards / getCardDetail` 作为强制访问日志记录下来。

证据：

- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniEvents/store.js:56` 只写 `openid / event_type / card_id / category_id / created_at`。
- `hotpost-mini/hotpost-mini-app/src/services/mini-events.ts:83` 上报失败只 `console.warn`，不会影响主流程。

这意味着：真正需要监控的云函数访问，目前没有稳定审计链。

### P2：收藏批量导入缺少上限

`miniFavorites.batchAdd` 要求 `OPENID`，但没有限制 `cardIds` 数量。

证据：

- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniFavorites/index.js:70` 直接循环写入所有传入的 `cardIds`。

这不是内容泄露主风险，但会放大写库成本，应该顺手加上限。

## 保护原则

1. 关键保护必须放在云函数出口，不依赖前端按钮、页面跳转或本地缓存。
2. 列表可以相对开放，详情必须强制校验。
3. 不做“假加密”：小程序端拿到的数据都可被复制，真正有效的是少给、慢给、记账、限速。
4. 先保护完整详情，再优化摘要层字段。
5. 先做不需要微信审核的云函数改动，再决定是否发新版小程序包。

## 分阶段计划

### P0：先锁详情出口

目标：直接调用 `miniRelease.getCardDetail` 也必须走积分和权限。

改动：

- 在 `miniRelease` 云函数入口读取 `cloud.getWXContext().OPENID`。
- `getCardDetail` 返回详情前，先查询 `mini_users`。
- 复用 `miniPoints` 当前规则：白名单 / `free_detail_access` 不扣分；已看过同一张卡不重复扣分；普通用户扣 `10` 积分；积分不足直接返回 `POINTS_INSUFFICIENT`，不能返回详情。
- 扣分和写流水成功后，再读取并返回详情。
- 保持 `miniPoints.consumeDetail` 幂等，兼容当前前端仍会二次调用扣分的情况，避免重复扣分。

验收：

- 未登录或没有用户档案时，`getCardDetail` 不返回详情。
- 积分不足时，`getCardDetail` 返回积分不足，不返回 `detail / quotes / source_link`。
- 同一用户重复查看同一张卡，不重复扣分。
- 白名单用户仍可免扣查看。
- 旧版小程序包无需改动即可继续工作。

部署：

- 只部署 `miniRelease` 云函数即可先挡住详情绕过，不需要重新提交小程序审核。
- 如果后续清理前端重复扣分流程，则需要上传新版小程序包并走微信审核。

### P0：给列表和详情加基础限速

目标：正常用户不受影响，脚本批量拉取会被限制。

建议阈值：

- `listCards`：同一 `OPENID` 每小时最多 `80` 次；单次 `pageSize` 继续锁死 `max_page_size=30`。
- `getCardDetail`：同一 `OPENID` 每小时最多 `40` 次；积分扣减仍是主保护，限速只挡异常频率。
- 同一 `OPENID` 连续触发限速后，写入 `mini_access_abuse_flags`，便于后续人工封禁或降低额度。

实现方式：

- 新增 `mini_access_rate_limits` 集合，按 `openid + action + hour_bucket` 计数。
- 云函数内先检查计数，再执行数据读取。
- 限速失败返回 `RATE_LIMITED`，不返回任何业务数据。

验收：

- 正常打开首页、切 tab、加载更多不触发限速。
- 脚本连续请求超过阈值后返回 `RATE_LIMITED`。
- 详情限速不会误伤已购详情的低频重复查看。

### P1：建立服务端访问日志

目标：以后能回答“谁在批量拉、拉了什么、拉了多快”。

改动：

- 新增 `mini_access_events` 集合。
- `miniRelease` 每次处理 `listCards / getCardDetail` 时写服务端日志。
- 字段建议：`openid / action / card_id / card_type / cursor / page_size / release_id / result / points_delta / error / created_at / request_id`。
- 前端 `miniEvents` 保留做产品行为分析，但不再承担安全审计职责。

验收：

- 每次详情成功、积分不足、限速失败都有记录。
- 每次列表请求都有 `cursor / page_size / release_id`。
- 可以用一个脚本按小时查出高频 openid。

### P1：收紧摘要层字段

目标：列表仍能判断是否值得点开，但不把过多资产提前暴露。

候选调整：

- 保留：标题、摘要、一句话 why now、类别、热度、发布时间、基础来源计数。
- 谨慎保留：`preview_quote`，如果被批量复制价值过高，可改成更短片段或只在详情返回。
- 延后到详情：完整 `source_module.primary_communities`、完整争议图解释、原帖链接、quotes。

验收：

- 首页卡片仍能支撑用户决策。
- `listCards` 返回字段不含 `detail / quotes / source_link`。
- 摘要层单卡 payload 明显小于详情层。

### P2：补运营控制和追责能力

目标：对持续异常账号有运营手段。

改动：

- 增加 `mini_access_blocks`：按 `openid` 临时封禁或降低限额。
- 详情响应中加入服务端 `access_trace_id`，用于用户反馈和问题追查。
- 收藏 `batchAdd` 增加单次最多 `100` 个 id 的上限。
- 清理云函数包内不必要的快照数据，避免派生产物在多个云函数里重复打包。

验收：

- 被 block 的 `openid` 无法继续拉详情。
- 客服或运营可以按 `access_trace_id` 查到一次详情访问。
- 收藏批量导入超限会被拒绝。

## 不做什么

- 不承诺禁止截图、复制或人工转发。
- 不把保护寄托在前端隐藏字段、混淆字段名或本地加密上。
- 不把所有列表都改成登录后可见；这会明显伤害新用户浏览体验。
- 不引入复杂风控系统；先用云函数内的计费、限速、日志解决当前风险。

## 推荐执行顺序

1. 先做 `miniRelease.getCardDetail` 服务端积分闸门。
2. 同步加 `miniRelease` 访问日志。
3. 加 `listCards / getCardDetail` 基础限速。
4. 跑云函数测试和小程序生产构建。
5. 只部署 `miniRelease` 云函数，先不动小程序包。
6. 观察 24 小时访问日志，再决定是否调限额和收紧摘要字段。

## 完成标准

- 直接调用 `miniRelease.getCardDetail` 不能绕过积分。
- 详情失败路径不返回任何详情字段。
- 异常高频列表和详情请求会被限速。
- 服务端能查到列表和详情访问记录。
- 旧版已上线小程序不会因为云函数先行部署而双倍扣分。
