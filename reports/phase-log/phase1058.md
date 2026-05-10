# phase1058

## 这轮达到的目的

恢复小程序“我的”页手机号绑定入口，用于验证主体变更后的手机号能力。

## 当前状态变化

前端已在已登录未绑手机状态露出“绑定手机号”，点击走微信 `getPhoneNumber`，再调用既有 `miniAuth.bindPhone`；已绑定用户显示脱敏手机号。新增守护测试防止入口再次被隐藏。

## 还没完成什么

还没做真机授权验证，也还没确认线上云函数已部署到包含 `phonenumber.getPhoneNumber` 权限的版本。

## 下一步做什么

上传新版小程序包，部署 `miniAuth` 云函数；真机登录后点“我的 -> 绑定手机号”，确认 `mini_users` 写入 `phone_masked / phone_bound_at`。
