# Phase 820 - Mini app local backend startup chain recovery

## 发现
- 微信开发者工具白屏解除后，首页继续报 `卡片加载失败`，控制台实际错误是 `GET http://127.0.0.1:8006/api/hotpost/cards?card_type=all net::ERR_CONNECTION_REFUSED`。
- 开发态 `.env.development` 已明确指向本地 `http://127.0.0.1:8006`，所以问题不在云函数串线，而在本地 backend 未成功启动。
- 本地 backend 启动链存在一组启动级注解错误：
  - `backend/app/api/v1/endpoints/hotpost_card_candidates.py`
  - `backend/app/api/v1/endpoints/hotpost_card_drafts.py`
  - `backend/app/api/v1/endpoints/hotpost_card_review.py`
  - `backend/app/schemas/hotpost_card_review.py`
  - `backend/app/schemas/hotpost_wx_auth.py`
  - `backend/app/models/mini_user.py`

## 修复
- 为缺失的 `Optional` 注解补齐模块级导入。
- 将 `MiniUser` 中不合法的 `Optional[Mapped[T]]` 改为 SQLAlchemy 2 合法写法：
  - `Mapped[str | None]`
  - `Mapped[datetime | None]`
- 用与启动脚本一致的环境验证：
  - `cd backend && ../.venv/bin/python -c "import app.main"`
  - 通过
- 重新拉起本地 backend：
  - `make dev-backend-start`
  - 通过

## 验证
- `curl -fsS http://127.0.0.1:8006/openapi.json` -> `OPENAPI_OK`
- `GET /api/hotpost/cards?card_type=all` -> `200`
- 返回卡片数：`30`
- 监听状态：
  - `Python ... TCP *:8006 (LISTEN)`

## 当前结论
- 当前问题已经从“前端加载失败”收敛为“本地 backend 启动链损坏”，并已修复。
- 此轮不需要继续改小程序页面或云函数。
- 下一步只需验证微信开发者工具在本地开发态是否能正常加载首页卡片。
