# phase1065

## 这轮达到的目的

完成小程序手机号绑定真机验收。

## 当前状态变化

用户反馈新版体验版已能成功绑定手机号。说明微信隐私声明、合并按钮 `getPhoneNumber|agreePrivacyAuthorization`、前端取 `code`、云函数 `miniAuth.bindPhone` 这条链路已经打通。

## 还没完成什么

还需确认云数据库 `mini_users` 中 `phone_masked / phone_bound_at` 已写入；分享奖励当前仍按好友首次授权登录结算，还没收紧到绑定手机号完成。

## 下一步做什么

先查库确认手机号字段落库；然后把邀请奖励结算点改成“好友绑定手机号成功后才发放”，再做一次分享链路真机验证。
