# PRD-06: 用户认证系统（后端现状对齐版）

## 1. 背景
系统采用 JWT 无状态认证，所有任务/报告以 `user_id` 做隔离。注册与登录必须轻量，支持后续会员等级扩展。

## 2. 目标
- **JWT 无状态**：Bearer Token 认证。
- **多租户隔离**：所有任务与报告按用户隔离。
- **简单注册/登录**：邮箱 + 密码。
- **会员等级**：保留 `membership_level` 字段。

## 3. 现状实现

### 3.1 接口
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### 3.2 密码与令牌
- 密码哈希：`PBKDF2-SHA256`（`passlib`）
- Token 默认有效期：24 小时
- Payload：`sub`(user_id) + `email` + `exp` + `iat`

### 3.3 用户表关键字段
- `email`, `password_hash`, `membership_level`, `is_active`
- 注册默认 `membership_level=free`

### 3.4 Admin 角色与前端存储
- Admin 判定：`is_superuser` 或 `ADMIN_EMAILS` 白名单（服务端鉴权）
- 前端 token 存储键：`auth_token`（统一由 `apiClient` 读取）

---

**文档状态**：已按本地实现对齐（backend）。
