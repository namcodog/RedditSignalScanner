# Phase 634 - 小程序独立用户体系与云端收藏落地

## 时间
- 2026-04-05

## 目标
- 按最终收口方案落地小程序独立用户体系：
  - `mini_users`
  - `mini_user_favorites`
  - `wx-auth`
  - `wx-favorites`
- 把收藏从本地缓存迁到云端，并保持首页/详情/收藏/我的四处链路不变。

## 实现
- 后端新增小程序独立模型：
  - `backend/app/models/mini_user.py`
  - `MiniUser`
  - `MiniUserFavorite`
- 新增 Alembic migration：
  - `backend/alembic/versions/20260405_000001_add_mini_users.py`
- 新增微信登录与云端收藏接口：
  - `backend/app/api/v1/endpoints/hotpost_wx_auth.py`
  - `backend/app/api/v1/endpoints/hotpost_wx_favorites.py`
- JWT 复用现有安全模块，但补了 mini token 隔离：
  - `backend/app/core/security.py`
  - `backend/app/core/mini_auth.py`
- 新增小程序登录与收藏服务：
  - `backend/app/services/hotpost/wx_session_service.py`
  - `backend/app/services/hotpost/mini_auth_service.py`
  - `backend/app/services/hotpost/mini_favorite_service.py`
- 前端新增静默登录服务：
  - `hotpost-mini/hotpost-mini-app/src/services/auth.ts`
- 前端收藏从本地改成云端 API，并保留一次性迁移：
  - `hotpost-mini/hotpost-mini-app/src/services/favorites.ts`
- 前端请求层补 Bearer token：
  - `hotpost-mini/hotpost-mini-app/src/services/clues.ts`
- 小程序启动时自动静默登录并迁移旧收藏：
  - `hotpost-mini/hotpost-mini-app/src/app.ts`
- “我的”页接入 mini 用户信息、收藏数、云端收藏状态：
  - `hotpost-mini/hotpost-mini-app/src/pages/profile/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/profile/index.scss`

## 验证
- 后端定向测试：
  - `cd backend && python -m pytest tests/api/test_hotpost_wx_auth.py tests/services/hotpost/test_wx_session_service.py -q`
  - `7 passed`
- 小程序构建：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
  - 通过
- 本地迁移：
  - `set -a && source backend/.env && set +a && cd backend && python -m alembic upgrade head`
  - 已成功执行
- 后端运行态：
  - `make dev-backend-restart`
  - 已正常拉起 `8006`
- 运行态核实：
  - `GET /api/hotpost/wx-favorites` 未带 token 返回 `401`
  - `GET /api/hotpost/wx-favorites` 带坏 token 返回 `401 {"detail":"Invalid authentication credentials"}`
  - `POST /api/hotpost/wx-auth/login` 带测试 code 返回 `{"detail":"invalid code, rid: ..."}`，说明 `WX_MINI_APPID/WX_MINI_SECRET` 已被后端正确读取，并已真实打到微信 `code2Session`

## 风险与边界
- 当前唯一未完成项不再是代码或配置，而是**微信开发者工具/真机人工联调**：
  - 需要真实 `wx.login()` code 才能跑通完整登录闭环
  - 当前已证明后端能和微信服务端成功通信，但还没在小程序里完成最终登录、收藏写云端、清缓存恢复的人工验收
- Alembic 不是缺数据库，而是命令需要显式导出 `backend/.env`。

## 当前判断
- 小程序用户体系这轮已经从“本地收藏”进入“独立身份 + 云端收藏”状态。
- 架构边界是对的：
  - 不复用主站 `users`
  - 不把微信用户塞进邮箱密码体系
  - 公共读卡接口保持匿名可读
  - 收藏/Profile 进入 mini token 保护
- 当前工程实现已完成，剩余工作是最后一段人工联调验收。

## 下一步
1. 跑一次真实微信开发者工具联调：
   - 静默登录
   - 收藏写云端
   - 清缓存后收藏恢复
2. 如果联调通过，再进入真正上线收尾。
