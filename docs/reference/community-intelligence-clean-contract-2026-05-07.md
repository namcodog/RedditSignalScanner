# Community Intelligence Clean Contract

日期：2026-05-07
状态：当前产品口径合同

本文件用于纠正 `Community Governance` 阶段产生的口径漂移。后续判断 Reddit Community Intelligence 主线时，先看本文件，再看治理审计报告。

2026-05-08 补充硬合同：`docs/superpowers/specs/2026-05-08-community-recommendation-interest-tag-contract-design.md`。若本文件中的标签示例、preview 口径或旧测试与补充合同冲突，以补充合同为准；生产代码禁止硬编码产品标签、社区名单、关键词包、排序权重或用户推荐文案。

2026-05-08 归档补充：`docs/reference/community-discovery-legacy-archive-2026-05-08.md`。旧社区发现 / 社区池治理链只保留为历史审计、数据准备、Dev 写入追溯和 rollback 参考，不再作为当前标签式社区推荐产品的主判断链。

## 1. 当前目标

主项目不再做“用户输入空白检索框，系统实时抓取并回答任意问题”。

当前目标是：系统先根据已有数据、语义库和社区覆盖能力，生成一组用户能直接点击的标签 / 赛道；用户点击后，系统给出一组有价值的 Reddit 社区，并说明为什么这些社区值得看、证据来自哪里、近期是否仍活跃。

标签 / 赛道不是用户输入项。它们必须来自系统已经有证据能服务的方向，例如 `semantic_terms`、`content_labels`、`content_entities`、`semantic_observation`、Hotpost 出卡证据、topic profile 和社区池覆盖。

输出重点：
- 推荐长尾、有业务价值、真实用户讨论密度高的社区。
- 泛社区可以作为热点和真相源参考，但不能挤掉长尾社区。
- 结果必须带理由，不能只给社区名。

## 2. 数据边界

`community_pool` 是干净的社区总池，不是推荐结果页。

可以进入 `community_pool` 的社区：
- 原 Dev DB 里已有的社区。
- Hotpost / 小程序已经产出过有价值卡片的社区。
- 发现链、供应配置、历史分析中有证据的社区。

推荐给用户的社区，必须再过一层推荐筛选：
- 与用户选择的标签 / 赛道相关。
- 近期有活跃度证据；当前默认看 `15D`。
- 有可解释证据：Hotpost 卡、旧 DB 帖子 / 评论 / 标签、社区统计、发现链记录。
- 长尾社区优先；泛社区只用于热点兜底和平台大盘参照。

没有 `15D` 新数据，不等于社区没价值；只表示当前不默认推荐，进入冷却 / 复查。旧 DB 数据可以继续用于社区 DNA、趋势和历史深度判断。

## 3. Hotpost 与主项目关系

Hotpost / 小程序是用户端和新社区探测器。

它提供：
- 每天真实运营产生的新信号。
- 哪些社区能持续出有价值卡片的证据。
- 新社区回流到 `community_pool` 的来源。

它不承担：
- 替代主项目深度分析。
- 证明没有出卡的旧 DB 社区没价值。
- 决定社区是否应该被删除。

主项目负责深度：
- 用 `community_pool` 做社区资产底座。
- 用旧 DB 的帖子、评论、标签、分析结果做社区 DNA。
- 用轻量 `15D` 活跃探测判断当前是否值得推荐。
- 不做重型实时抓取；维护 6-12 个月历史数据储备即可。

## 4. 已落地事实

这些是已经落地的资产，但不能被夸大成产品完成：

- `HotpostCommunityActivityProvider`：能从 Hotpost published cards 只读聚合社区证据。
- `community_governance_audit.py`：能生成社区治理审计；当前已归档为历史治理工具。
- `community_pool_phase1_planner.py`：能生成 dry-run 入池差异和泛社区预算信息；当前已归档为历史治理工具。
- `community_pool_phase2_dev_writer.py`：已在 Dev 库写入 `56` 个社区，Dev active pool 从 `300` 到 `356`，并有 rollback SQL；当前只保留为 Dev 写入追溯和 rollback 参考。
- `CommunityDiscoveryService`：已有社区发现服务，但不接成当前标签式推荐产品主链。
- `community_ranker.compute_ranking_scores`：已有信号密度打分能力，但尚未接成当前推荐闭环。
- `semantic_terms / UnifiedLexicon / content_labels / content_entities / semantic_observation / embedding`：已有语义库、标签账本和混合检索能力；当前推荐设计必须优先复用这些资产，而不是重新做一套手工标签系统。

## 5. 必须纠正的漂移

以下口径不能再作为当前产品判断依据：

- Phase 0 / 1 / 2 治理完成，不等于社区推荐产品完成。
- `community_pool` 扩容，不等于这些社区都会推荐给用户。
- `strong / medium / weak` 只是历史证据密度标签，不是入池门禁，不是产品等级。
- 泛社区 cap 是输出和学习预算控制，不是排除泛社区的理由。
- Hotpost 没出卡不是旧 DB 社区无价值的证据。
- `stale_review` 不是删除队列，只是需要旧 DB 和近期活跃度复查。
- 当前阶段不做 UserTrack、Web/API、前端入口、开放搜索框、实时重抓。
- 当前默认不新建表；除非后续证明确实需要持久化推荐快照。
- 旧社区发现 / 社区池治理链不能再被当作当前产品推荐链；它只负责历史审计、数据准备和追溯。

## 6. 下一步执行口径

下一步先做离线、可验证的标签式社区推荐预览，不直接上前端，不直接写 Gold DB。

最小闭环：
1. 标签生成：从语义库、旧 DB 标签 / 实体、Hotpost topic、社区覆盖里生成“我们能提供什么价值”的标签 / 赛道。
2. 用户选择：用户只点击系统提供的标签 / 赛道，不输入自由标签。
3. 候选：从 `community_pool` 取社区，合并 Hotpost 证据、旧 DB 证据、发现链证据和语义账本证据。
4. 筛选：语义相关性、`15D` 活跃度、长尾优先、泛社区限额。
5. 输出：社区列表、推荐理由、证据来源、是否活跃、是否泛社区。
6. 验收：用跨境电商、AI 工具、宠物 / 小商品三个切片检查结果是否像真实推荐，而不是库存清单。

当前产品合同的成功标准：用户选择一个标签后，能看到一组说得清楚、证据站得住、长尾不被泛社区淹没的社区推荐。
