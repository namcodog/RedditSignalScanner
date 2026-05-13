# phase806

- 时间：2026-04-14
- 结论：小程序开发态与生产态的数据链已拆开。

## 本次改动

- 更新 [hotpost-mini/hotpost-mini-app/.env.development](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/.env.development)
  - 开发态默认走 `http://127.0.0.1:8006`
  - 开发态关闭 `TARO_APP_CLOUD_ENV_ID`
- 生产态保持不变，继续走云开发环境 `cloud1-1gjqvb5l27cfb790`

## 验证

- `npm run build:weapp` 通过
- `npm run build:weapp:prod` 通过
- 开发构建产物中 `Boolean(\"\")` 生效，收藏/登录/卡片列表都会回落到本地 backend
- 生产构建产物仍保留云环境链路

## 影响

- 微信开发者工具本地联调：看本地 backend 的最新实现
- 体验版 / 正式版：继续看云函数和云数据库
- 以后本地 UI 验收不再被云端旧 release 干扰
