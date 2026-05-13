# Phase 819 - 小程序白屏启动链审计与最小修复

## 发现
- 白屏报错是启动阶段 `Cannot read property 'mount' of null`，不是业务页面渲染报错。
- 首先排除了首页卡片、详情页和服务层的直接 DOM 调用；源码里没有手写 `mount` / `ReactDOM` / `document.querySelector` 之类逻辑。
- 风险集中在构建与开发者工具运行配置：
  - `project.config.json`
  - `project.private.config.json`
  - `scripts/ensure-weapp-config.cjs`
  - `config/index.ts`
- 当前配置里存在两类高风险项：
  - `lazyCodeLoading: "requiredComponents"`
  - mini 端 webpack 强行覆盖 `mainFields` 和 `target: ['web', 'es5']`

## 修复
- 关闭了开发者工具的 `lazyCodeLoading`：
  - `project.config.json`
  - `project.private.config.json`
  - `scripts/ensure-weapp-config.cjs`
- 去掉了 mini 端 webpack 的两项危险覆盖，只保留输出环境降级：
  - `config/index.ts`

## 验证
- 已重新执行：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 构建通过。
- 当前 `dist/project.config.json` 已确认不再包含 `lazyCodeLoading`。

## 结论
- 这轮修复只动了启动链配置，没有污染已验收的业务页面和视觉层。
- 下一步只需要在微信开发者工具里做一次“清缓存并重新编译”，验证白屏是否解除。
