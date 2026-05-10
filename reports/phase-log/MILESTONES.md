# 项目里程碑

最后更新：2026-05-08

## 里程碑 1：项目骨架与工具链建立

- 时段：`phase0 ~ phase121`
- 达成：
  - 建立 `backend / frontend / reports` 基础结构
  - MCP 工具链和基础工程工具完成接入
  - 开始清理未引用脚本和历史入口，避免主路径继续失控
- 今天仍然有效的结论：
  - 入口必须收口
  - 运行入口和历史脚本必须分层

## 里程碑 2：分析链、数据层与质量合同收紧

- 时段：`phase200 ~ phase399`
- 达成：
  - 分析层和 `facts_v2` 的“静默降级 / 兜底混层”问题被集中审计
  - 数据采集与冷存储合同逐步收紧
  - 测试与数据库约束开始从“能跑”转到“真相一致”
- 今天仍然有效的结论：
  - 不能用 fallback 和 silent degrade 伪装真实结果
  - 数据合同和展示合同必须分开

## 里程碑 3：主链报告、Dev DB 与真相源校准

- 时段：`phase400 ~ phase625`
- 达成：
  - `Full A` 报告漂移、机器腔、证据链不稳这些问题被重新拉回主链
  - Dev DB 的社区池 / cache / category map 失配被识别出来
  - open-question 主链逐步重新拿回 `A_full`
- 今天仍然有效的结论：
  - 真问题往往在数据底盘和质量门，不在表面 prompt
  - 社区真相源与分析主链必须保持同一口径

## 里程碑 4：hotpost 1.0 合同与 pack 方法论成型

- 时段：`phase626 ~ phase799`
- 达成：
  - `signal / hot / breakdown` 三条线形成 `1.0` 口径
  - density-first、pack-specific intake path、topic metadata、homepage shelf 等合同逐步成型
  - `organic-discovery / category-winds` 等 pack 有了稳定方法
- 今天仍然有效的结论：
  - 产品主线不是“精选周报”，而是“高密度、能持续上新”的 Reddit 前线
  - pack 能力必须靠供给、判断、写法一起收口

## 里程碑 5：稳态运营与 freshest supply 前沿

- 时段：`phase800 ~ now`
- 达成：
  - 发布口径切到 `value-threshold publishing`
  - `quota-aware yield-until-exhausted crawl` 被确认为当前正确 rollout target
  - `SociaVault` 被确认为 `assist / rescue` 层
  - 记录系统开始从 `800+` phase 的流水账仓库切到当前状态入口
  - 产品默认发卡范围已正式切到 `all-scope`
  - 默认全树 workflow 已真实跑通到 `yield_exhausted = true`
  - Hotpost 新出卡默认接入 V13 生产口径；`2026-04-30` 回补节奏已改为逐日验收：Day1-Day5 已补全，累计 `99` 张，最新同步链全绿；`2026-05-01` 又按众筹 / 预售 / 选品 / 礼物优先补发 `29` 张，最新 snapshot `release-e2fb5db69afa`，`card_count=565`，front30 已恢复 breakdown 代表位，但 trend 仍未 stable，严格停机字段不能夸大
  - 小程序上线准备已补齐手机号和积分关键链路：手机号绑定真机验通；奖励口径已收紧为“邀请新用户绑定奖励”，只有新用户通过邀请链接首次授权并绑定手机号后，邀请人才获得 `30` 积分；白名单详情免扣仍保留
  - Reddit Community Intelligence 已完成一次口径纠偏：Phase 0 / 1 / 2 社区治理和 Dev 写入只算数据准备，当前产品主线改为“系统从已有数据和语义库生成标签 / 赛道 -> 用户点击 -> 有证据、有理由、长尾优先的社区推荐”
  - 标签式社区推荐已落成合同修正版：`CAPABILITY_SEEDS` 已从 production code 移除，9 个用户可选业务标签、旧业务分类目录和 Phase 2 分类推断都改由配置真相源承载；后端应用服务入口已收口，CLI 和后续 API / 前端适配层必须共用同一 service；当前能生成 `9` 个具像化兴趣标签和 `64` 条推荐样例，后端验收为 `acceptance_passed=true / ready_count=32`
  - Hotpost 探索社区池到 `community_pool` 的 R10/R11 已落地：显式 probe 入口和只读回流 dry-run 都已具备；R11.5 社区价值评分算法已补上，人工发布验证降级为校准样本；`r/CursorAI` 当前为 `validated / score=56`，但还不是 `pool_candidate`
- 今天仍然有效的结论：
  - Hotpost 当前主问题是 `freshness / quota / freshest supply`；Community Intelligence 当前主问题已经从“后端能不能生成推荐”变成“用户是否认可推荐质量，以及是否需要补真实 Reddit 活跃探测和更深语义观察”
  - 当前阶段是稳态运营优化期，不是大架构重建期
  - 产品正式默认范围是 `all-scope`；单 slice 只用于显式局部修复
  - V13 阻塞时宁可少发，也不能静默切旧模型或旧 prompt 补量
  - 积分增长不能只看点击分享，必须看被邀请人完成授权和手机号绑定后的真实转化
  - `community_pool` 是社区总池，不是推荐结果页；下一步先做用户验收，再谈前端 / API / 生产写入

## 现在怎么看这个项目

如果只看今天仍然有效的判断，顺序是：

1. 先读 [CURRENT_STATUS.md](/Users/hujia/Desktop/RedditSignalScanner/reports/phase-log/CURRENT_STATUS.md)
2. 再读 [OPEN_ITEMS.md](/Users/hujia/Desktop/RedditSignalScanner/reports/phase-log/OPEN_ITEMS.md)
3. 再读本文件
4. 需要细节时，再进对应的阶段摘要和 archive
