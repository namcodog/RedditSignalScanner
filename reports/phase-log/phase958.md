# phase958

## 这轮达到的目的

把小程序“微信登录 / 绑定手机号 / 用户资料显示”三条链的真实完成度审清楚，避免再把它们混成一件事。

## 当前状态变化

- 微信登录会话已完成：前端 `ensureLogin()` 已接通，本地走 `/api/hotpost/wx-auth/login`，生产走云函数 `miniAuth.login`
- 手机号绑定只在云函数链完成：`miniAuth.bindPhone` 已实现；本地 backend 没有绑定手机号接口、schema、字段和测试
- 真实微信昵称/头像联动未完成：虽有 `updateProfile` 能力，但前端没有 `chooseAvatar / 昵称录入 / 微信资料授权` 入口，当前仍是随机别名或占位头像

## 验证结果

- 审计了前端：`src/services/auth.ts`、`src/pages/profile/index.tsx`、`src/pages/phone-bind/index.tsx`
- 审计了后端：`backend/app/api/v1/endpoints/hotpost_wx_auth.py`、`backend/app/services/hotpost/mini_auth_service.py`、`backend/app/models/mini_user.py`
- 审计了云函数：`cloudfunctions/miniAuth/index.js`、`cloudfunctions/miniAuth/store.js`

## 下一步做什么

如果要收成统一链路，只能二选一：
1. 本地 backend 也补齐手机号绑定
2. 开发/生产统一都走云开发 auth
