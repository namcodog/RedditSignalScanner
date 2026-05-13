# Phase 563 - Mini Hotpost 联调实例统一

## 发现了什么？
- 当前小程序“分析超时”的主因不是 `rant` 算法，而是联调目标服务错了。
- 本机同时存在两套 hotpost 后端：
  - `8006`：新起但不健康，`search/openapi` 都可能超时
  - `8016`：旧常驻进程，`trending` 能跑，但 `rant` 因旧 schema 直接失败
- 因此真正要做的不是继续改页面，而是统一小程序应该连哪套服务。

## 是否需要修复？
- 需要。
- 否则小程序一直会在：
  - 错误实例超时
  - 旧实例 schema 漂移
  之间来回撞，不可能得到稳定联调结果。

## 精确修复方法
- 把小程序环境地址改回当前实际可联调实例：
  - `hotpost-mini/hotpost-mini-app/.env.development`
  - `hotpost-mini/hotpost-mini-app/.env.production`
  - 当前统一为：`http://192.168.50.252:8016`
- 重启 `8016` 后端实例到当前代码状态：
  - 停止旧进程
  - 使用当前仓库代码重新启动：
    - `uvicorn app.main:app --host 0.0.0.0 --port 8016`
- 更新小程序服务层报错文案：
  - loopback 报错不再写死 `localhost:8006`
  - 直接显示当前实际连接地址
- 重新 `build:weapp`

## 验证
- `curl -sS -m 5 http://192.168.50.252:8016/api/v1/health`
  - 返回：`{"status":"ok"}`
- `trending` 验证：
  - query=`shopify chargeback evidence response workflow`
  - 结果：`queued -> degraded`
- `rant` 验证：
  - query=`why creators complain tiktok moderation hurts monetization`
  - 结果：`queued -> degraded`
  - 不再出现：
    - `HotpostDebugInfo extra_forbidden`
    - 联调超时假故障
- 小程序构建：
  - `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - 结果：`Compiled successfully`
- 产物确认：
  - `dist/common.js` 已内联 `http://192.168.50.252:8016`

## 下一步系统性计划
1. 回到小程序真机/开发者工具重试当前 query
2. 如果 `rant` 仍弱，就按真实结果继续收：
   - query 语义
   - 拿料精度
   - 页面表达
3. 不再把服务实例混乱问题和结果质量问题混为一谈

## 这次执行的价值是什么？
- 这轮把“联调故障”和“产品结果弱”彻底拆开了。
- 现在小程序看到的结果，已经基本是 hotpost 当前真实能力，而不是后端实例错乱带来的假问题。
