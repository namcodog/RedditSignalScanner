# Phase 768 - 小程序本地构建链复验与审计纠偏

## 发现

- `npm run build:weapp` 串行单跑通过。
- 上一轮把“开发态构建链有问题”记成风险，是误判。
- 误判根因不是项目代码，而是我当时并行跑了：
  - `npm run build:weapp`
  - `npm run build:weapp:prod`
- 两条构建同时清理同一个 `dist/`，把 `dist/app.js.LICENSE.txt` 的清理过程互相踩脏了。

## 结果

- 当前小程序构建链状态应修正为：
  - `build:weapp`
    - 通过
  - `build:weapp:prod`
    - 通过
- 因此“本地开发工具和手机端是否同步”的结论也需要同步修正：
  - 云环境：同步
  - 数据源：同步
  - 本地 weapp 构建产物：同步

## 当前判断

- 当前没有证据表明 `hotpost-mini` 的开发态构建链本身存在故障。
- 后续如果再看到类似 `ENOENT ... dist/app.js.LICENSE.txt`，应先排查是否有人并发跑了两个 weapp build，而不是先改业务代码或构建配置。

## 下一步

- 开发工具本地调试继续使用 `npm run build:weapp` 或正常开发者工具编译即可。
- 手机端要看到同一版优化，仍然需要上传最新体验版；这一点不是 bug，而是微信小程序本身的发布链路。
