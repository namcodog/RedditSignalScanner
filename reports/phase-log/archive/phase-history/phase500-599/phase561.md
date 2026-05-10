# Phase 561 - Mini Hotpost 联调地址与报错收口

## 发现了什么？
- 当前小程序截图里的 `request:fail` 不是 `rant` 内容质量问题，而是请求链路先断了。
- 已确认两个硬阻塞：
  1. `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts` 把后端地址写死成 `http://localhost:8006`
  2. 当前本机 `localhost:8006` 也没有后端在监听，`curl /api/v1/health` 直接失败
- 这意味着：
  - 微信开发者工具同机模拟至少要先起后端
  - 真机/预览环境则不能继续用 `localhost`，必须改成电脑局域网地址

## 是否需要修复？
- 需要。
- 否则用户在小程序上看到的只会是联调假故障，根本还没进入 `rant` 结果验证阶段。

## 精确修复方法
- 更新 `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts`
  - 小程序后端地址改为优先读取编译期常量 `__HOTPOST_API_BASE_URL__`
  - 保留 `localhost:8006` 作为开发默认值
  - 对 `localhost / 127.0.0.1 / 0.0.0.0` 做 loopback 识别
  - 把 `request:fail` 翻译成可执行的人话：
    - 先启动后端
    - 真机/预览改成电脑局域网地址
- 更新 `hotpost-mini/hotpost-mini-app/config/index.ts`
  - 通过 `defineConstants` 把 `TARO_APP_API_BASE_URL` 真正编译进产物
- 更新 `hotpost-mini/hotpost-mini-app/types/global.d.ts`
  - 增加 `TARO_APP_API_BASE_URL` 类型声明
- 更新 `hotpost-mini/hotpost-mini-app/.env.development`
  - 当前填入本机局域网地址：`http://192.168.50.252:8006`
- 更新 `hotpost-mini/hotpost-mini-app/.env.production`
  - 同步填入局域网地址，确保 `build:weapp` 产物也能直接联调

## 验证
- 初次检查：
  - `curl -sS -m 5 http://localhost:8006/api/v1/health`
  - 结果：`curl: (7) Failed to connect to localhost port 8006`
- 启动本机后端：
  - `make dev-backend`
  - 结果：服务已在 `0.0.0.0:8006` 运行
- 健康检查：
  - `curl -sS -m 5 http://localhost:8006/api/v1/health`
  - 结果：`{"status":"ok"}`
- 局域网地址检查：
  - `curl -sS -m 5 http://192.168.50.252:8006/api/v1/health`
  - 结果：`{"status":"ok"}`
- `rant` 接单检查：
  - `curl -sS -m 20 -X POST http://192.168.50.252:8006/api/v1/hotpost/search ...`
  - 结果：返回 `status="queued"`
- `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - 结果：`Compiled successfully`
- 产物确认：
  - `dist/common.js` 已内联 `http://192.168.50.252:8006`

## 下一步系统性计划
1. 重新进入小程序验证：
   - 是否能成功提交 query
   - loading 是否进入真实 `queued / processing`
   - `friction` 结果是否更聚焦
   - migration 区块是否已去掉脏词
2. 如果切换网络：
   - 同步更新 `.env.development / .env.production` 中的局域网 IP
   - 重新 `build:weapp`

## 这次执行的价值是什么？
- 这轮把“小程序报错”和“rant 质量差”彻底分开了。
- 先把联调层拉正，下一轮用户在小程序上看到的才是有效的产品信号，而不是 `localhost` 和后端未启动造成的假问题。
