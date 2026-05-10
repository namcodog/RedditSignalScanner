# Phase 825

## 本轮目标
- 修复小程序本地开发态 `wx-auth/login` 的 500，恢复登录链。

## 发现
- 第一层根因：`Settings` 未定义 `wx_mini_appid / wx_mini_secret`，路由读取属性直接抛异常，导致 `/api/hotpost/wx-auth/login` 返回 500。
- 第二层根因：mini 登录链的 token 合同与当前 `security` 实现脱节：
  - `mini_auth_service` 调 `create_access_token(..., source="mini")`
  - `create_access_token` 不接受 `source`
  - `decode_mini_jwt_token` 又依赖 `payload.source`

## 修复
- `backend/app/core/config.py`
  - 增加 `wx_mini_appid`
  - 增加 `wx_mini_secret`
  - `get_settings()` 接入 `WX_MINI_APPID / WX_MINI_SECRET`
- `backend/app/core/security.py`
  - `TokenPayload` 增加 `source`
  - `create_access_token()` 增加 `source` 参数并写入 JWT
- `backend/app/services/hotpost/mini_auth_service.py`
  - 补 `Optional` 导入，避免这条 mini 链后续再被类型解析打断
- `backend/tests/core/test_config_defaults.py`
  - 增加微信小程序配置读取回归测试

## 验证
- `cd backend && pytest tests/core/test_config_defaults.py tests/api/test_hotpost_wx_auth.py tests/services/hotpost/test_wx_session_service.py tests/core/test_security.py -q`
  - 14 passed
- 重启本地 backend：`make dev-backend-restart`
- 直接请求：
  - `POST /api/hotpost/wx-auth/login`
  - 现已从 500 变成 401（无效 code），说明服务端崩溃点已消失，接口恢复到正常错误语义

## 结论
- 当前登录链已经从“服务端异常”恢复到“可正常处理微信登录结果”。
- 后续若开发工具仍提示登录失败，需要看新的前端提示或真实微信 code 返回，不再是这轮 500 的问题。
