# phase707

## 本轮完成
- 已修复 `hotpost-mini` 本地开发工具因为未配置云环境而直接报 `cloud.callFunction` 权限错误的问题。

## 根因
- 当前仓库没有配置任何 `TARO_APP_CLOUD_ENV_ID`。
- 微信开发者工具本地项目也没有绑定可用云环境。
- 但小程序内容读取已经被切到 `cloud.callFunction`，所以开发态会必然报：
  - `errCode: -601034`
  - `请先开通云开发或者云托管`

## 修法
- 不是去乱改页面，也不是让开发态强依赖未配置的云环境。
- 改成明确的双模式：
  - 配了 `TARO_APP_CLOUD_ENV_ID`：走云函数
  - 没配：继续走本地 HTTP 联调

## 代码改动
- `hotpost-mini/hotpost-mini-app/src/app.ts`
  - 只有在存在 `__HOTPOST_CLOUD_ENV_ID__` 时才初始化 `cloud`
- `hotpost-mini/hotpost-mini-app/src/services/clues.ts`
  - `listCategories / listCards / getCardDetail / trackCardEvent` 增加显式传输开关
  - 开发态未配云环境时回到已有 `/api/hotpost/*` HTTP 联调链

## 验证
- `npm run build:weapp`
  - 构建成功
- `npm run build:weapp:prod`
  - 构建成功

## 当前结论
- 这次报错不是“页面坏了”，而是开发态误走了未配置的云函数路径。
- 现在本地开发已恢复可用；后续真要切真云开发，再补 `TARO_APP_CLOUD_ENV_ID` 和开发者工具云环境即可。
