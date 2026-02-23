# phase56：更新 README / 文档阅读指南到“抓取SOP v3.2 + DB Atlas”最新版口径

## 这次要解决什么
Key 指出的问题是对的：`README.md` 和 `docs/2025-10-10-文档阅读指南.md` 里很多内容停留在旧版本，读者会误以为“看 README 就够了”，但实际抓取系统与 DB 的唯一参照已经变成：

- 抓取口径：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
- DB 事实：`docs/2025-12-14-database-architecture-atlas.md`（从 `localhost:5432/reddit_signal_scanner` 导出）

所以本次目标就是：把 README/阅读指南更新到“先看唯一参照，再看其他文档”的顺序。

## 做了什么

### 1) 更新 README（把唯一参照写到首页）
- 更新 `README.md`
  - 顶部状态改为：抓取 SOP v3.2 + DB Atlas 已对齐
  - 增加「抓取系统 & 数据库（唯一参照）」快速入口（SOP + DB Atlas + 配置地图）
  - 修复失效链接：`docs/DEPLOYMENT.md` → `docs/本地启动指南.md`（并保留 `docs/OPERATIONS.md`）
  - 文档导航里新增必读项：抓取 SOP v3.2 / DB Atlas

### 2) 更新文档阅读指南（新人第一天就能看对）
- 更新 `docs/2025-10-10-文档阅读指南.md`
  - 新人阅读顺序里加入：
    - `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
    - `docs/2025-12-14-database-architecture-atlas.md`
  - 更新文末 `最后更新` 日期到 2025-12-19

## 验收点（人工检查即可）
- 打开 `README.md`，能一眼看到：
  - 抓取系统口径指向 `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
  - DB 事实指向 `docs/2025-12-14-database-architecture-atlas.md`
- 打开 `docs/2025-10-10-文档阅读指南.md`，“新人开发者”阅读清单里已把 SOP/DB Atlas 放到前面

