# phase967

## 这轮达到的目的
把小程序用户系统从“必须绑手机号”正式改收成“只需要微信授权登录”，并把积分、签到、邀请奖励的触发条件一起切到首次登录。

## 当前状态变化
- 云函数 [miniAuth/index.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/miniAuth/index.js) 改成首次授权登录即发 `60` 分，并在新用户首次授权登录成功时给邀请人发 `30` 分。
- 云函数 [miniPoints/index.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/miniPoints/index.js) 与公共存储 [mini-points-store.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/common/mini-points-store.js) 去掉了手机号强依赖；详情扣分、签到、邀请奖励都只依赖登录。
- 前端 [auth.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/auth.ts) 在登录时透传 `inviteToken`，并在成功登录后清掉本地邀请 token。
- 前端门禁 [access-meter.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/access-meter.ts)、首页 [index/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx) 和详情页 [velocity/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx) 全部去掉了“先绑手机号”要求。
- 个人页 [profile/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/profile/index.tsx) 隐藏了绑手机号入口，只保留微信授权登录、积分卡、签到和退出登录。
- 积分页 [points/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/points/index.tsx) 的积分文案改成“首次授权登录 +60 / 新用户首次授权登录后邀请人 +30”。

## 验证结果
- 云函数测试通过：
  - `cd hotpost-mini/hotpost-mini-app && node --test cloudfunctions/tests/mini-auth.test.mjs cloudfunctions/tests/mini-points.test.mjs cloudfunctions/tests/mini-favorites.test.mjs`
- 开发构建通过：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 生产构建通过：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp:prod`

## 下一步做什么
- 在微信开发者工具里重新部署云函数：
  - `miniAuth`
  - `miniPoints`
  - `miniFavorites`
- 在云开发数据库里继续验三件事：
  1. 首次授权登录后 `mini_users.points_balance = 60`
  2. `mini_user_points_ledger` 出现 `+60` 初始化流水
  3. 邀请新用户成功后出现 `+30` 奖励流水
- 真机只验 4 条：
  1. 点详情先微信授权登录
  2. 首次登录后积分变成 `60`
  3. 看一次详情扣 `10`
  4. 每日签到 `+10`
