# Phase 831 - 小程序 dev/prod 构建输出彻底隔离

## 发现

- 用户持续反馈：
  - 本地开发工具可用
  - 手机预览仍然“无法加载”
- 进一步核实后确认，核心问题不是单纯云函数或数据，而是：
  - `build:weapp`
  - `build:weapp:prod`
  之前都共用同一个 `dist/`
- 结果是：
  - 谁最后构建，谁就覆盖掉另一条链的产物
  - dev 包和 prod 包互相污染

## 证据

- 修改前：
  - `config/index.ts` 的 `outputRoot` 固定为 `dist`
  - `ensure-weapp-config.cjs` 也只处理 `dist/project.config.json`
- 直接检查编译产物可见：
  - dev 包会写入 `127.0.0.1:8006`
  - prod 包会写入云环境 `cloud1-1gjqvb5l27cfb790`
  - 但二者共享 `dist/`，因此非常容易互相覆盖

## 修复

- `config/index.ts`
  - development 输出改为：`dist-dev`
  - production 输出改为：`dist-prod`
- `scripts/ensure-weapp-config.cjs`
  - 根据 `NODE_ENV` 动态改写：
    - `project.config.json`
    - `project.private.config.json`
    - 对应输出目录里的 `project.config.json`
  - 自动把 `miniprogramRoot` 指向当前模式对应目录
  - 清理对应输出目录下的 `cloudfunctions`

## 验证

- dev 构建：
  - `npm run build:weapp`
  - 生成目录：`dist-dev/`
- prod 构建：
  - `npm run build:weapp:prod`
  - 生成目录：`dist-prod/`
- 直接检查编译产物常量：
  - `dist-dev/common.js`
    - `hasLocalhost = true`
    - `hasCloudEnv = false`
    - `hasEmptyCloudFlag = true`
  - `dist-prod/common.js`
    - `hasLocalhost = true`（fallback 字符串仍保留）
    - `hasCloudEnv = true`
    - `hasEmptyCloudFlag = false`
- 当前项目配置文件在最近一次 prod 构建后已指向：
  - `miniprogramRoot = dist-prod/`

## 结论

- 这次把“小程序本地调试链”和“手机预览链”的构建产物真正隔离开了。
- 后续规则：
  - 本地调试：`npm run build:weapp`，看 `dist-dev/`
  - 真机预览：`npm run build:weapp:prod`，看 `dist-prod/`
- 以后不会再出现“我只是重编了本地包，却把手机预览包覆盖掉”的结构性问题。
