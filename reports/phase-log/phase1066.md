# phase1066

## 这轮达到的目的

把分享奖励口径落成代码：被分享用户必须完成微信授权和绑定手机号后，邀请人才获得 30 积分。

## 当前状态变化

`miniAuth.login` 不再结算邀请奖励；前端会把 invite token 保留到 `bindPhone`，绑定手机号成功后再由 `miniAuth.bindPhone` 完成 referral、邀请人加分和积分流水。积分页、分享标题、详情弹窗和流水文案已统一写成“好友完成授权并绑定手机号”。验证结果：小程序云函数测试 `52 passed`，`npm run build:weapp:prod` 通过。

## 还没完成什么

线上还没部署新版 `miniAuth / miniPoints` 云函数，也还没用两个真实微信账号跑完整分享链路。

## 下一步做什么

部署云函数并上传新版体验版；用账号 A 分享、账号 B 完成授权和绑定手机号，确认 A 增加 30 积分、流水为 `invite_reward`，referral 状态变成 `completed`，B 写入手机号字段和邀请来源。
