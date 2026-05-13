# Hotpost 小程序项目说明

最后更新：`2026-04-21`

## 1. 这是什么

`hotpost` 小程序不是一个“抓 Reddit 的工具页”，也不是一个“周报阅读器”。

它的产品定位是：

- 把 Reddit 上高价值、还新鲜、能形成业务判断的讨论，做成可持续上新的卡片流
- 用小程序承接正式发布后的卡片阅读、收藏和回看
- 让运营侧能稳定出卡、稳定发布、稳定同步到手机，而不是每次靠人工拼接内容和页面

一句话说：
**它是一个“持续上新”的 Reddit 商业信号前线，而小程序是正式发布层的消费面。**

## 2. 产品目标

当前项目真正追的不是固定模板数量，而是这几件事：

- 新信息能持续进入正式发布面
- 用户每天打开时，能明显感到“今天有新东西”
- 首页、详情、收藏、真机显示保持一致
- 运营补卡、评审、发布、同步的链路稳定，不靠口头记忆

当前正式口径已经切成：

- `value-threshold publishing`
- `yield-until-exhausted crawl`
- `all-scope` 为日常默认运营面
- `15 / 30` 是窗口和运营目标，不是硬模板

## 3. 产品边界

### 3.1 小程序负责什么

小程序只负责正式发布后的消费层：

- 首页浏览
- 分类筛选
- 卡片详情阅读
- 收藏与回看
- 登录绑定
- 真机云端读取

### 3.2 小程序不负责什么

这些都不在小程序里决策：

- Reddit 抓取
- freshness gate
- collect 配额
- candidate / draft 工作区
- 发布数量决定
- 争议图生成逻辑

这些都在主仓后端和运营 workflow 里完成。

## 4. 用户能看到的产品结构

入口配置在 [app.config.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/app.config.ts)。

当前页面结构是：

- `首页`：`/pages/index/index`
- `收藏`：`/pages/history/index`
- `我的`：`/pages/profile/index`
- `手机绑定`：`/pages/phone-bind/index`
- `详情页`：`/pages/velocity/index`
- `外链中转`：`/pages/link/index`
- `加载页`：`/pages/loading/index`
- `实验页`：`/pages/friction/index`、`/pages/alpha/index`

当前自定义 tab bar 只保留三项：

- 首页
- 收藏
- 我的

## 5. 首页和详情怎么工作

### 5.1 首页

首页实现见 [index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx)。

首页固定 4 个 tab：

- `全部`
- `潜力快帖`
- `跨区热议`
- `近期爆帖`

这 4 个 tab 对应的是正式发布后的 `lane` 视图：

- `signal` = 潜力快帖
- `breakdown` = 跨区热议
- `hot` = 近期爆帖

补充面 `supplement surface` 作为兼容分桶继续存在，但它不再决定前台哪些卡可见，也不再单独做前端 tab。

### 5.2 详情页

详情页实现见 [velocity/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx) 和 [clues.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/clues.ts)。

详情页按卡片类型和 lane 渲染不同结构：

- `signal validate`：痛点、场景、为什么现在试
- `hot validate`：爆点、争论线、为什么现在试
- `write`：论点、写法角度、标题钩子、引用包

也就是说，小程序不是拿一个通用 schema 硬渲染全部卡，而是按 lane 吃结构化字段。

### 5.3 收藏页

收藏页实现见 [history/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/history/index.tsx) 和 [favorites.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/favorites.ts)。

收藏链有两个模式：

- 本地开发 / 本地 API 模式：走 `/api/hotpost/wx-favorites`
- 云端模式：走 `miniFavorites` 云函数

旧的本地收藏会自动迁移到云端收藏集合。

## 6. 内容资产和状态分层

当前 hotpost 的内容真相源是分层的，合同见 [hotpost-storage-contract.md](/Users/hujia/Desktop/RedditSignalScanner/docs/reference/hotpost-storage-contract.md)。

### 6.1 原料池

- `backend/data/hotpost/candidates/*.json`

这是候选原料池，可以按 scope 覆盖。

### 6.2 工作区

- `backend/data/hotpost/drafts/*.json`

这是 draft 工作区，只能按 `draft_id` 精确改。

### 6.3 正式资产

- `backend/data/hotpost/releases/latest.json`
- `backend/data/hotpost/releases/<release_id>/cards/*.json`

这是正式发布真相源。

### 6.4 运行时投影

- `published` 不是独立真相源
- 它只是 latest release 的运行时投影

### 6.5 小程序快照和云端派生层

- `backend/data/hotpost/mini_snapshots/`
- `hotpost-mini/.../cloudfunctions/miniRelease/data/`
- `hotpost-mini/.../cloudfunctions/miniFavorites/data/`

这些都是派生产物，不是内容真相源。
只能由 `push_mini_snapshot.py` 写入，不能手改。

## 7. 发布链和小程序同步链

这条链是整个项目最关键的结构。

### 7.1 正式发布链

运营 workflow 先做：

- collect
- review
- seed draft
- 人工评审
- publish

发布后，正式卡进入：

- `releases/latest.json`
- `releases/<release_id>/cards/*.json`

### 7.2 小程序快照链

推送脚本见 [push_mini_snapshot.py](/Users/hujia/Desktop/RedditSignalScanner/backend/scripts/hotpost/push_mini_snapshot.py)。

脚本会调用：

- `publish_mini_snapshot()`

然后完成几件事：

- 从正式 release 构建 `mini snapshot`
- 写本地 snapshot 文件
- 生成 cloud db 导入包
- 把数据 bundle 到 `miniRelease` / `miniFavorites` 云函数数据目录
- 跑一轮趋势审计

### 7.3 云端读取链

真机和云端读取逻辑见 [miniRelease/store.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js)。

云端只读两类集合：

- `mini_release_meta`
- `mini_release_cards`

当前小程序内容链就是：

`正式发布 -> mini snapshot -> cloud_db 导入 -> miniRelease/miniFavorites -> 小程序页面`

这条链的设计意义是：

- 小程序不碰 candidates / drafts
- 真机只消费已发布内容
- 本地和云端差异能被清晰隔离

## 8. 首页排序和展示逻辑

小程序前台看到的顺序，不等于简单按 release 文件顺序。

核心逻辑在 [mini_snapshot.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/mini_snapshot.py)。

当前规则是：

- 先按 `published_at` 倒序收正式卡
- 小程序 snapshot 保留全部已发布卡，不再按 freshness 把旧卡裁出列表
- 同一天新发卡优先前置
- 同一天内部再按首页货架规则混排，不让一种 lane 把首页占满
- 如果同一天已有 `breakdown`，首页展示窗口必须给 `breakdown` 代表位，不能因为发布时间较早被同日 hot/signal 全部挤出前 30
- 首页只重排前面的展示窗口，不影响后面的已发布卡继续保留在列表里

这里要分清两个时间：

- `source_event_at`：原始讨论发生时间
- `published_at`：我们正式发卡时间

当前首页“今天这批新卡要顶前”是按 `published_at` 认，不是按 `source_event_at` 抢前排。

## 9. 运营策略和节奏

日常产卡 SOP 见 [2026-04-08-日常产卡SOP.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2026-04-08-日常产卡SOP.md)。

### 9.1 固定节奏

当前日常默认是每天 `3` 轮：

- 第一轮：`all-scope` 基础盘
- 第二轮：定向补薄
- 第三轮：停机确认 / 再补一轮

### 9.2 停机逻辑

不是按固定数量停，而是按：

- `yield exhaustion`
- `publish_ready`
- `actual_total`
- collect 是否还有真实增量

### 9.3 运营目标

当前追的是：

- 新发现感
- 新社区命中
- candidate 到 publish 的穿透
- 供给厚度
- 首页显示层稳定

不是单纯追一个固定的“每天必须发多少张”。

## 10. 底层规则和硬门槛

### 10.1 lane 定义固定

- `signal`：潜力快帖
- `hot`：近期爆帖
- `breakdown`：跨区热议

### 10.2 `hot` 必须补争议图

发布规则见 [2026-04-08-评审与发布SOP.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2026-04-08-评审与发布SOP.md)。

当前 `hot` 卡不是“先发再补图”，而是：

- 缺 `controversy_chart`
- 或缺 `controversy_meta`

就不能发，也不能同步到小程序。

这一步属于发布前闸门，不属于前半段补货 workflow。

### 10.3 supplement 不是前端新 tab

合同见 [hotpost-card-supplement-contract.md](/Users/hujia/Desktop/RedditSignalScanner/docs/reference/hotpost-card-supplement-contract.md)。

当前正式口径是：

- `supplement surface` 继续保留
- 但它只是后台分桶
- 前端不再增加 `15天补充` tab

### 10.4 小程序只读正式发布层

小程序不能读：

- candidates
- drafts
- review queue

它只读：

- latest mini snapshot
- cloud db 同步后的正式快照

## 11. 当前配置真相源

当前配置主入口是 [hotpost_supply_discovery_v2.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_supply_discovery_v2.yaml)。

当前比较关键的默认值有：

- `runs_per_day = 3`
- `feed_initial_page_size = 30`
- `feed_max_page_size = 30`
- `review_queue_limit = 20`
- `breakdown_materialize_limit = 20`
- `rolling_publish_mix.window_size = 30`
- lane target：
  - `signal = 18`
  - `hot = 8`
  - `breakdown = 5`

这份 YAML 现在是运营层和 discover 层的主要配置真相源，不应该再把这些默认值藏回 Python 常量。

## 12. 本地开发、正式包和真机怎么看

这部分最容易混，所以单独写清。

### 12.1 本地开发

本地开发看：

- `dist-dev`
- 本地后端 `127.0.0.1:8006`

也就是说，本地开发重点是：

- 本地 API
- 本地 build
- 本地 snapshot / 本地后端

### 12.2 真机 / 手机预览

真机看：

- `dist-prod`
- cloud db
- `miniRelease / miniFavorites` 云函数

如果只是内容更新，正常步骤是：

1. 发布卡
2. `push_mini_snapshot.py`
3. `check_mini_release_sync.py`
4. 导入两份 `wechat-import` 到云数据库

如果只是内容更新，通常不用重传云函数代码。

## 13. 当前项目状态

截至 `2026-04-21`，当前可确认状态是：

### 13.1 正式发布层

- latest release：`release-50f4c26a18d3`
- 当前正式卡资产数：`375`

### 13.2 小程序快照层

- latest mini snapshot：`release-28f7e52ecfa7`
- `card_count = 72`
- `main_card_count = 60`
- `supplement_card_count = 12`
- 当前前台 feed 合同仍是：
  - 首屏 `30`
  - 最大页长 `30`

### 13.3 当前前台结构分布

当前 snapshot 中：

- `ecommerce-sellers = 40`
- `business-growth-ops = 18`
- `ai-automation = 14`

lane 分布是：

- `signal = 43`
- `hot = 24`
- `breakdown = 5`

### 13.4 当前项目已经收稳的东西

- 小程序不再把补充面做成前端 tab
- 首页排序已改成“今天新发优先 + 同日内部混排”
- `hot` 发布前补图已成为硬门槛
- 运营日志已独立成目录：
  - `reports/ops-log/`
- 小程序产品态已有基线文件：
  - `hotpost-mini/hotpost-mini-app/.product-baseline.json`

### 13.5 当前仍要持续盯的东西

- 真机云端导入与本地开发态的一致性
- `hot` 供给厚度是否持续稳定
- `all-scope` 运营下的新发现感和新社区命中
- 小商品 / AI / business 三条线的供给平衡

## 14. 常用入口命令

### 14.1 日常运营

```bash
make hotpost-publish-until-exhausted
make hotpost-workflow-dry-run
make hotpost-breakdown-materialize
make hotpost-breakdown-overlap
```

### 14.2 小程序同步

```bash
python backend/scripts/hotpost/push_mini_snapshot.py
python backend/scripts/hotpost/check_mini_release_sync.py
```

### 14.3 小程序构建

```bash
npm --prefix hotpost-mini/hotpost-mini-app run build:weapp
npm --prefix hotpost-mini/hotpost-mini-app run build:weapp:prod
```

### 14.4 运营日志导出

```bash
python backend/scripts/hotpost/export_ops_log.py
```

## 15. 这份文档和 key-os 的关系

按当前仓库和 `key-os` 的新边界：

- 这份详细项目说明文档属于当前业务仓
- 它记录的是 hotpost 小程序的完整产品说明、逻辑说明和当前状态
- `key-os` 不应该直接存这一整份业务细节

正确做法是：

- 详细文档留在当前仓库
- 只把“高价值、跨项目仍成立的判断”通过 `keyos` CLI 回填到 `key-os`
- 如果需要让 `key-os` 可检索这份文档，就走 `keyos wiki ingest`

也就是说：
**当前仓库保留业务真相，key-os 只接高价值摘要和知识索引。**
