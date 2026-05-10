# phase807

- 时间：2026-04-14
- 类型：审计

## 结论

- 开发态配置已切到本地 backend：
  - `.env.development` 使用 `http://127.0.0.1:8006`
  - 开发构建产物中云开关为 `Boolean("")`
- 生产态仍走云开发：
  - `.env.production` 保持 `cloud1-1gjqvb5l27cfb790`
- 本地 backend 当前进程已是新版本：
  - `uvicorn app.main:app --host 0.0.0.0 --port 8006`
- 本地接口已返回新数据：
  - `GET /api/hotpost/cards?card_type=hot` 返回 `controversy_chart`
  - `GET /api/hotpost/cards/card-cand-ai-automation-1sk82sc-validate` 返回 `controversy_chart`
- 本地 snapshot 与小程序 cloudfunctions 内置 release 数据一致：
  - `release-5d6a952f346a`

## 风险

- 如果微信开发者工具仍显示旧卡面，剩余风险只在工具缓存/未重新载入本次开发构建，不在代码和接口。
