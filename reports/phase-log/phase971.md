# phase971

## 这轮达到的目的
把小程序登录前合规链改成正式授权页：先勾选协议，再触发微信隐私同意，再执行微信授权登录。

## 当前状态变化
- 详情入口、收藏登录入口、个人页登录入口、积分页登录入口，统一改成跳转授权页。
- 授权页保留在 `pages/phone-bind/index`，但职责改成“登录合规页”，不再走手机号绑定主流程。
- 新增本地《用户协议》页 `pages/legal/index`。
- 隐私政策链接改成调用微信 `openPrivacyContract`。
- 小程序全局配置打开 `__usePrivacyCheck__`，允许 `requirePrivacyAuthorize` 触发微信隐私同意流程。

## 验证结果
- `npm run build:weapp` 通过。
- `dist-dev/app.json` 已确认包含：
  - `pages/phone-bind/index`
  - `pages/legal/index`
  - `__usePrivacyCheck__: true`
- 登录入口静态核对通过：
  - 首页详情前登录入口已跳授权页
  - 收藏页登录入口已跳授权页
  - 个人页登录入口已跳授权页
  - 积分页登录入口已跳授权页

## 下一步做什么
- 在开发者工具里清缓存并重新编译。
- 真机验证两件事：
  1. 未登录点详情，先进入授权页。
  2. 勾选协议后点“微信授权登录”，微信侧弹出隐私同意流程，再完成登录并跳回原页面。
