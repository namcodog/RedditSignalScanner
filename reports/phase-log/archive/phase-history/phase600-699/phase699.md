# phase699

## 本轮完成
- 对 `hotpost-mini` 是否适合迁微信云开发做了范围重审
- 核查了小程序当前真实接口依赖与仓库残留旧链
- 产出一份收口设计结论：
  - `docs/superpowers/specs/2026-04-08-hotpost-mini-cloudbase-design.md`

## 本地代码证据
- 当前卡片阅读链真实依赖的是轻接口：
  - `src/services/clues.ts`
  - `src/services/auth.ts`
  - `src/services/favorites.ts`
- 这些接口主要是：
  - 卡片列表 / 详情 / 分类
  - 微信登录
  - 收藏增删查
  - 埋点
- 仓库里仍残留旧搜索链：
  - `src/services/hotpost.ts`
  - `pages/loading/index`
  - `/api/v1/hotpost/search`
  - `/api/v1/hotpost/result/{queryId}`

## 结论
- 如果范围严格缩到“卡片阅读链 + 登录 + 收藏 + 埋点”，微信云开发是可行且更省事的方向。
- 如果旧 `search/result/loading` 也算小程序正式范围，方案就不稳，不建议迁。
- 进一步收口后，`v1.0` 更合适的不是 “DB-first 全部上云数据库”，而是：
  - **卡片走发布快照分发**
  - **用户/收藏/埋点走云数据库**
- 原因：
  - 当前卡片源本来就是 `hotpost_clues.json`
  - 这样推送最轻、回滚最简单、也不阻塞后续恢复搜索能力

## 决策建议
- 推荐方向：
  - 小程序只保留卡片阅读链，上云开发
  - 本地继续保留产卡炼油厂
  - `v1.0` 先把已发布卡片作为发布快照推到云端
  - 用户、收藏、埋点进入云数据库
  - 登录先做微信身份登录，不把头像昵称授权绑成阻塞项
- 明确不做：
  - 整个仓库迁云开发
  - 旧搜索分析链一起迁
  - 把云数据库当正式真相源
