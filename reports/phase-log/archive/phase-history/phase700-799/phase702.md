# phase702

## 本轮完成
- 把 `hotpost-mini v1.0` 的云开发方向正式收成实施方案。
- 方案已不再停留在“能不能做”，而是明确到：
  - 产品门槛
  - 云端资源
  - 代码改造清单
  - 阶段顺序
  - 测试与回滚

## 实施结论
- `v1.0` 正式方案：
  - `3-card meter`
  - 云端 `snapshot` 常驻分发
  - 用户/收藏/埋点进云数据库
  - 用户模型预留 `plan/status/entitlements`
- 不采用：
  - 首页首屏强登录
  - 卡片全量先拆库
  - 旧搜索链一起迁

## 关键工程判断
- 当前最小可逆方案仍然是 `snapshot-first`，不是 `DB-first`。
- 小程序当前最值钱的不是“复杂在线后端”，而是：
  - 稳定内容下发
  - 冷启动转化漏斗
  - 用户身份与收藏沉淀
- 未来收费与搜索扩展都可以在这版底座上继续长，不需要推翻 `v1.0`。

## 文档沉淀
- `docs/superpowers/specs/2026-04-08-hotpost-mini-cloudbase-implementation-plan.md`
