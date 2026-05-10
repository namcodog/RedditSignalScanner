# Phase 767 - 小程序真机 bug 与本地同步审计

## 发现

- 真机详情页 loading 锁死的根因已经修到位：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
    - `cancelled` 分支现在会先关闭 `loading`
    - `bind_phone` 分支现在会写入错误提示并关闭 `loading`
  - `hotpost-mini/hotpost-mini-app/src/pages/phone-bind/index.tsx`
    - 新增详情页来源的回退路由
    - 当来源是 `/pages/velocity/index` 时，点“继续逛逛”会直接回首页，不再回到旧详情页实例

- 生成产物里已经包含本次修复：
  - `dist/pages/velocity/index.js`
    - 已出现 `继续查看前，请先绑定手机号`
    - 已出现 `l(!1)` 对应 loading 关闭逻辑
  - `dist/pages/phone-bind/index.js`
    - 已出现 `/pages/velocity/index` -> `/pages/index/index` 的回退逻辑

- 开发态和手机体验版当前读的是同一个云开发环境：
  - `.env.development`
    - `TARO_APP_CLOUD_ENV_ID="cloud1-1gjqvb5l27cfb790"`
  - `.env.production`
    - `TARO_APP_CLOUD_ENV_ID="cloud1-1gjqvb5l27cfb790"`
  - `src/app.ts`
    - 启动时统一 `cloud.init({ env: __HOTPOST_CLOUD_ENV_ID__ })`

## 结论

- 数据层和云环境层：
  - 本地开发工具与手机端当前是同步的
  - 两边都指向同一个云环境，卡片、收藏、登录都走同一套云开发链路

- 代码产物层：
  - 当前 `dist/` 已经带着这次修复，所以如果开发工具当前加载的是这份最新 `dist`，它和手机端代码也是同步的

- 仍然存在的风险点：
  - `npm run build:weapp:prod`
    - 通过
  - `npm run build:weapp`
    - 仍失败，失败点是 Taro 清理 `dist/app.js.LICENSE.txt` 的旧构建问题
  - 这意味着：
    - 当前“本地开发工具看到的代码”如果来自最近一次成功的 `prod build`，就是同步的
    - 但“开发态增量构建链”本身还不稳定，后续改动不适合默认假设会自动同步进开发工具

## 当前判断

- 这次真机 bug 本身已经修到了位。
- “本地和手机是否同步”这件事，当前答案是：
  - 云环境和数据：同步
  - 当前已生成代码：同步
  - 开发态自动增量构建能力：还不稳，不能当成完全可靠

## 下一步

- 先让用户用最新体验版和当前开发工具各复测一轮详情页路径，确认 bug 已消失。
- 后续如果还要继续依赖开发工具实时看效果，应单独修掉 `npm run build:weapp` 的清理链问题，不然本地热更新仍可能假同步。
