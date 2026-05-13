# phase966

## 这轮达到的目的
把小程序 P0 用户系统主链真正接到云开发：登录、绑手机号、首次赠分、详情扣分、签到、邀请奖励、积分页和个人页积分卡都已落地。

## 当前状态变化
- 新增云函数 [miniPoints/index.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/miniPoints/index.js)，统一承接积分汇总、详情扣分、签到、流水、邀请 token。
- 扩展 [miniAuth/index.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/miniAuth/index.js) 和 [miniAuth/store.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/miniAuth/store.js)，首次绑手机号后发放 60 积分，并在新用户完成授权+绑手机号时给邀请人发 30 积分。
- 前端认证改成统一走云开发，见 [auth.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/auth.ts)；开发态通过 `TARO_APP_USER_CLOUD_ENV_ID` 只把用户系统切云，内容链仍走原开发链。
- 详情页改成登录+绑手机号+积分门禁，见 [velocity/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx)；旧的试看逻辑已移除。
- 绑定页改成“两步式”，见 [phone-bind/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/phone-bind/index.tsx) 和 [phone-bind/index.scss](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/phone-bind/index.scss)。
- 新增积分服务 [points.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/points.ts) 和积分页 [points/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/points/index.tsx)。
- 个人页增加积分卡、签到入口、分享入口，见 [profile/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/profile/index.tsx)。
- 首页品牌名改成 `深蓝singal`，见 [index/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx) 和 [app.config.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/app.config.ts)。
- 明确保留阻塞项：`关注公众号 +100` 这轮只保留产品位，不发真积分。

## 验证结果
- 云函数测试通过：
  - `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-auth.test.mjs hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-points.test.mjs hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-favorites.test.mjs`
- 开发构建通过：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 生产构建通过：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp:prod`
- 语法检查通过：
  - `node --check hotpost-mini/hotpost-mini-app/cloudfunctions/miniAuth/index.js`
  - `node --check hotpost-mini/hotpost-mini-app/cloudfunctions/miniPoints/index.js`

## 下一步做什么
- 在微信开发者工具里部署云函数 `miniAuth` 和 `miniPoints`。
- 在云数据库确认/创建集合：
  - `mini_users`
  - `mini_user_points_ledger`
  - `mini_user_referrals`
- 真机验收顺序只看 5 条：
  1. 列表可直接滑动
  2. 点详情先登录，再绑手机号
  3. 首次绑手机号后积分变成 60
  4. 看详情扣 10 分
  5. 分享给新用户，新用户完成授权+绑手机号后，老用户 +30
