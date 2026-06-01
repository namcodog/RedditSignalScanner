# Task Plan — Hotpost 5 天缺口回补

## 2026-06-01 V13 预检优化后运营计划

- [x] 真实链路验证 -> 验证点：抽样 seed `2` 张 validate draft，不发布；两张均成功生成，`generation_trace.allow_breakdown=false`，重复 seed 被 `Draft already exists` 提前拦截。
- [x] 缺口判断 -> 验证点：工程链路已稳定，但 AI 预检过宽；`PASS` 没拦住半截英文原话、`min_test_action=去看原始讨论`、废词跟踪等低质字段。
- [x] 预检规则优化 -> 验证点：补上确定性后处理，模型误判 `PASS` 时，遇到 `weak_min_test_action / truncated_quote / junk_tracking_terms` 会强制转 `REWRITE`。
- [x] 回归验证 -> 验证点：相关回归 `109 passed`；刚才真实生成的两张旧 PASS，本地复验均转为 `REWRITE`。

下一步出卡节奏：

- 先不发布刚才两张测试 draft，除非人工改掉 `why_test_now / min_test_action / continue_signal` 后重新 review。
- 重新跑 validate queue，优先挑 `电商与卖家 / 产品品牌众筹 / 1688进货观察 / 商业增长` 的新候选做 `2-3` 张小样本 seed。
- 每张 seed 后必须先看 `show-draft`：
  - `PASS`：继续人工 review。
  - `REWRITE`：先改稿或换候选，不直接发布。
  - `BLOCK`：默认不发，除非人工能明确说明预检误判。
- 小样本复验通过后，再恢复日常出卡；今日不追硬数量，目标是验证优化后 `precheck` 能不能提前拦住低质稿。
- 发布链仍按原 SOP：发布后才跑 `push_mini_snapshot.py`、同步检查、社区探索 post 和品牌 sidecar。

今日判断边界：

- 这次优化解决的是“AI 预检太宽松”，不是模型路线切换；不静默换旧模型或旧 prompt。
- 如果新规则导致 REWRITE 变多，这是预期结果，不算模型失败；只有重复误杀高质量稿，才回头调规则。
- 1688 / 产品品牌众筹继续作为观察重点，但不因方向重要就降低证据标准。

## 2026-06-01 运营补全执行结果

- [x] 小配额定向采集 -> 验证点：`crossborder-sku-selection-7d` 跑出 `13` 个候选，`crossborder-sku-brand-ebay-7d` 跑出 `23` 个候选，`china-sourcing-1688-7d` 跑出 `10` 个候选；Kickstarter/Crowdfunding 信号已在 SKU profile 内覆盖。
- [x] 产品 / 品牌 / 众筹继续补厚 -> 验证点：已在原 `6` 张基础上补发 `1` 张渠道特供 / 品牌溢价卡；当前相关卡 `7` 张，仍低于目标 `10-12`。
- [x] 1688 / 进货继续观察 -> 验证点：本轮仍未发布纯 1688 卡；强候选集中在中国验厂、Alibaba sourcing 和履约问题，但证据不够支撑 `3-5` 张发布。
- [x] 商业增长补齐 -> 验证点：新增 `3` 张，覆盖改版后低转化、Shopify bot 流量污染、广告扣款现金流错配；今日商业增长达到 `5` 张。
- [x] AI 补充 -> 验证点：新增 `1` 张 Claude 自动发 TikTok 的内容污染信号；今日 AI 到 `4` 张，仍低于目标 `5-7`。
- [x] 发布同步 -> 验证点：新增 `5` 张后，`push_mini_snapshot.py` 生成 `release-26a0d6956396 / card_count=1258`；`check_mini_release_sync.py` 通过，`feed_contract=30/30`、`miniRelease / miniFavorites / cloud_db` 一致，hot controversy guard 和 copy guard 均通过。

当前缺口：

- 总量：`17/25-30`，未完成。
- 产品 / 品牌 / 众筹：`7/10-12`，缺 `3-5` 张。
- 1688 / 进货：`0/3-5`，缺口保留，不硬发弱证据。
- AI：`4/5-7`，缺 `1-3` 张。
- 商业增长：`5/5-6`，达标。

阻塞判断：

- `make hotpost-publish-until-exhausted` 完成采集侧 `yield_exhaustion`，但最终 `decision=rewrite`，原因是 `hot_over_age_limit / stale_ratio_above_threshold`。
- 模型侧仍有坏 JSON / 空 JSON / 总超时 / Gemini 503；这不是候选池空，而是生成链稳定性和 hot 过龄共同限制。
- 预检规则有效：多张草稿被挡在 `weak_min_test_action`、半截英文引用和垃圾追踪词上；只对可人工明确修复的字段做了修补后发布。

## 2026-05-31 日常出卡计划

- [x] 计划校准 -> 验证点：5/28、5/29 已有正式运营日志和 release；当前真正缺口是 `2026-05-30` 空窗 + `2026-05-31` 今日运营。实际执行跨过本地零点，正式发布日志归到 `reports/ops-log/2026-06-01.md`，不倒填 `published_at=2026-05-30`。
- [x] 状态复核 -> 验证点：已确认 latest release、review queue、topic tree、hot lane、V13 precheck；发现 `task_plan.md` 与正式 ops-log 的 5/29 发卡数冲突时，以 `reports/ops-log/2026-05-29.md` 为准。
- [x] 探索社区 pre -> 验证点：显式 probe，只写 `experimental_candidates`，不直接写正式 candidates / drafts / release / DB；结果 `probe_count=4 / experimental_candidate_count=8`。
- [x] 第 1 轮 all-scope 基础盘 -> 验证点：`make hotpost-publish-until-exhausted` 约 3 分钟无输出后终止，改用可观测的 topic tree、hot lane、validate/write queue 和定向 collect 推进。
- [x] 第 2 轮定向补薄 -> 验证点：已补 `商业增长与运营`、`AI 与自动化`、`1688/进货/供应链`、`产品/品牌/众筹`；电商没有只围绕 eBay/Etsy/咖啡/钢笔老面孔。
- [x] r/Entrepreneur 新方向复核 -> 验证点：本轮没有继续从 r/Entrepreneur 硬发；商业增长侧改发画廊转化和 Meta Ads 公开信。
- [x] 1688 / 进货观察 -> 验证点：`china-sourcing-1688-7d` 跑出 `watch_count=3 / candidate_count=10`；纯 1688 卡仍未过发布线，保留观察。
- [x] 产品 / 品牌 / 众筹深挖 -> 验证点：发布 `6` 张相关卡，覆盖 Kickstarter 预热预算、AI 众筹页信任、扫地机溢价、钢笔笔尖、情侣露营装备和 onebag 极简装备。
- [x] 人审发布 -> 验证点：`show-draft` 已先看 V13 precheck；`Openclaws` 被 precheck 标为 `BLOCK` 未发布；已发布草稿均通过人工 review。
- [x] 第 3 轮停机确认 -> 验证点：本轮未达到完整日运营停机条件；停止原因是基础 workflow 无输出、breakdown materialize 超时、部分 seed 超时或重复已发布。
- [x] 发布后收口 -> 验证点：`push_mini_snapshot.py`、`check_mini_release_sync.py`、`community-exploration-post`、`brand-ops-sidecar`、小程序 snapshot data 检查已完成。

今日目标：

- 总量目标 `35-45` 张；低于 `30` 张必须写明供给、模型或质量门阻塞，不包装成完整双日恢复。
- 领域结构：`电商与卖家 16-20`、`AI 与自动化 8-12`、`商业增长与运营 8-10`、`breakdown 2-4`。
- 1688 / 进货观察目标 `2-4` 张；如果只有弱单帖或泛采购教程，只保留观察，不硬发。
- 产品 / 品牌 / 众筹目标 `4-6` 张；优先覆盖品牌信任、平替、预售/众筹、产品验证，不把普通晒单当品牌信号。
- r/Entrepreneur 目标 `4-6` 张；作为商业增长新方向，不抢占全部首页。

今日探索方向：

- `business-growth-ops:6:r/Entrepreneur 市场验证与渠道选择`
- `ecommerce-sellers:6:1688进货与供应链风控`
- `ecommerce-sellers:6:品牌溢价、平替与众筹预售风险`
- `ecommerce-sellers:6:eBay/reselling 平台费用、退货与单位经济`
- `ai-automation:4:Agent工具链、模型能力争议与开发者真实反馈`

今日判断边界：

- 5/30 缺口用今天新发卡覆盖，不倒填历史发布时间。
- `r/Entrepreneur` 已证明有价值，但仍是持续观察源，不因“新方向”降低证据标准。
- 1688 现在仍是 `电商与卖家 / SKU 选品 / 供应链进货判断` 的观察线，不独立成成熟栏目。
- 产品 / 品牌 / 众筹必须有“用户为什么信或不信、为什么愿意多付或转向平替、为什么预售/众筹可能交付失败”的判断增量；纯开箱、纯晒图、纯新品广告不发。
- 品牌 sidecar 继续只做上下文增强和观察；没有新品牌候选时不硬造品牌卡。
- V13 超时在正常范围内等待；超过运营窗口就换候选或留队列，不静默切旧模型。

执行结果：

- 正式发布 `12` 张：`hot 7 / signal 5`。
- 类别分布：`电商与卖家 7 / AI 与自动化 3 / 商业增长与运营 2`。
- 产品 / 品牌 / 众筹相关 `6` 张，是本轮最有效的新增方向。
- 最新快照：`release-5bd6c336831a`，`card_count=1253`；同步链、hot controversy guard、copy guard、小程序 snapshot data 检查通过。
- 社区探索 post：`already_in_pool=18 / keep_testing=8 / promote_candidate=0 / reject=0`，本轮没有新的 R12 入池对象。
- 品牌 sidecar：`brands_observed=217 / verified=15 / candidate=185 / rejected=17 / new_brand_candidates=0 / db_writes=false`。
- 本轮结论：发布链健康，但总量低于完整恢复线；`trend audit` 仍为 `rebound`，不能写 stable。

## 2026-05-29 日常出卡计划

- [x] 计划校准 -> 验证点：今天按正常日运营执行，不再按双日补发冲量；正式发布时间只记 `2026-05-29`。
- [x] 第 1 轮 all-scope 基础盘 -> 验证点：跑 `make hotpost-publish-until-exhausted`、`make hotpost-topic-tree-audit`、`audit_hot_lane.py` 和 validate queue，确认自然供给、hot 争议面和薄领域。
- [x] 第 2 轮定向补薄 -> 验证点：优先补 `AI 与自动化`、`商业增长与运营` 和 `1688/进货/供应链`；电商继续保主线但不把首页打成单一 eBay/Etsy 面。
- [x] 1688 小配额观察 -> 验证点：跑 `collect_named_topics.py --watch-profile china-sourcing-1688-7d --mode safe`；只发有真实商品、供应商风险、质检/物流、利润核算或用户踩坑的卡。
- [x] 新社区持续观察 -> 验证点：显式跑 pre probe，不直接写正式 candidates / drafts / release；重点看 `r/ebaysellers`、`r/reselling` 写入 Dev 后是否继续产出可发布信号。
- [x] 人审发布 -> 验证点：hot 必须有争议图；signal 必须有判断增量；breakdown 必须有强 thesis；V13 超时在合理范围内等待，超出运营窗口则换候选，不静默切旧模型。
- [x] 第 3 轮停机确认 -> 验证点：再次跑 all-scope 确认 `yield_exhausted` 与 `publish_ready=false`；若 `trend audit` 仍为 `rebound / watching`，只能写“今日发布完成”，不能写系统 stable。
- [x] 发布后收口 -> 验证点：`push_mini_snapshot.py`、`check_mini_release_sync.py`、`community-exploration-post`、`brand-ops-sidecar`、`hotpost-release-trend-audit` 全部记录结果。

今日目标：

- 总量目标 `25-35` 张；低于 `25` 张写明供给或模型阻塞，不包装成完整日运营。
- 领域结构：`电商与卖家 12-16`、`AI 与自动化 7-10`、`商业增长与运营 5-8`、`breakdown 2-3`。
- 1688 / 进货观察目标 `2-4` 张；如果只有泛教程、搬运帖或纯采购入口介绍，只保留观察，不硬发。
- 新社区目标：`r/ebaysellers / r/reselling` 先作为观察增强源，不设硬发卡数；只有出现平台政策、退货风控、单位经济或类目拥挤的强信号才转正式卡。

今日探索方向：

- `ecommerce-sellers:6:1688进货与卖家供应链`
- `ecommerce-sellers:6:eBay reselling与平台风控`
- `business-growth-ops:4:广告投放异常与GEO/AEO可见性`
- `ai-automation:4:Agent工具链与模型能力争议`

今日判断边界：

- 1688 不是独立成熟主线，今天仍归入 `电商与卖家 / SKU 选品 / 供应链进货判断`。
- 品牌侧只做 sidecar 观察；没有新品牌候选时不要为“品牌探索”硬造卡。
- 新社区“收录”不等于提高权重或自动发布；持续观察要看真实可发布证据。
- 5/28 已达到最低完整线但 `trend audit=rebound`，今天的目标是恢复稳态节奏和补薄结构，不是追 `40-50` 的补发口径。

执行结果：

- 正式发布 `21` 张：`hot 12 / signal 9 / breakdown 0`。
- 类别分布：`电商与卖家 11 / AI 与自动化 6 / 商业增长与运营 4`。
- 最新快照：`release-24445df394bd`，`card_count=1236`；`snapshot / miniRelease / miniFavorites / cloud_db / hot controversy guard / copy guard` 检查通过。
- 三轮 all-scope 最终均未回到 publish-ready：`stopped_by=yield_exhaustion / publish_ready=false / stale_ratio_out_of_control`。
- 1688 纯进货候选仍未过质量门；`1tpwcir` 命中中国工厂验货但被 `single_thread_weak_evidence / single_community_weak_evidence` 挡住。
- 社区探索 post：`already_in_pool=16 / keep_testing=8 / promote_candidate=0 / reject=0`，本轮没有新的 R12 入池对象。
- 品牌 sidecar：`brands_observed=217 / verified=15 / candidate=185 / rejected=17 / new_brand_candidates=0 / db_writes=false`。
- 本轮结论：发布链同步健康，但总量低于 `25`，不能写成完整日运营；`trend audit` 仍为 `rebound`，系统健康未 stable。

## 2026-05-28 补 05-27 + 05-28 双日出卡计划

- [x] 计划校准 -> 验证点：正式发布时间按 `2026-05-28` 记录，运营日志明确覆盖 `05-27 + 05-28` 内容窗口，不倒填 `published_at=2026-05-27`。
- [x] 1688 观察线接入 -> 验证点：新增 `china-sourcing-1688-7d` 只作为手动补货 profile，不进入默认 daily watchlist；目标测试通过。
- [x] 基础盘审计 -> 验证点：跑 `make hotpost-workflow-dry-run`、`make hotpost-topic-tree-audit`、`audit_hot_lane.py` 和 validate queue，确认当前可发面不是旧弱草稿。
- [x] 5/27 空窗补发段 -> 验证点：优先补 `eBay / reselling / SKU品牌舆情 / FBA供应商涨价 / Etsy-Shopify摩擦 / GEO-AEO / PPC转化`，不让 AI 抢主线。执行结果：已补 PPC / Meta Ads / Etsy / Shopify / FBA / eBay / SKU品牌舆情 / 选品信号；达到最低完整线，但未达理想目标。
- [x] 5/28 新鲜盘段 -> 验证点：重新跑 `7d fresh supply`，只有 `decision=publish` 且有净新增价值才继续 seed / review / publish。执行结果：已按 queue 人审发布新鲜候选；`make hotpost-publish-until-exhausted` 长链路无输出后终止，未拿到 clean final no-collect gate。
- [x] 1688 小配额观察 -> 验证点：跑 `collect_named_topics.py --watch-profile china-sourcing-1688-7d --mode safe`；只收真实商品、供应商、质检、物流、利润和用户踩坑，不发泛教程。
- [x] 探索社区 pre -> 验证点：只写 `experimental_candidates`，不写正式 candidates / drafts / release / DB。
- [x] 人审发布 -> 验证点：hot 必须有争议图；signal 必须有判断增量；breakdown 必须有强 thesis；V13 `402/503/连接失败` 时不静默换旧模型。
- [x] 发布后收口 -> 验证点：`push_mini_snapshot.py`、`check_mini_release_sync.py`、`community-exploration-post`、`brand-ops-sidecar`、`hotpost-release-trend-audit` 全部记录结果。

今日目标：

- 总量目标 `40-50` 张；低于 `30` 张必须写成补发未完整收口，不包装成正常双日运营。
- 领域结构：`电商与卖家 18-22`、`AI 与自动化 12-16`、`商业增长与运营 8-12`、`breakdown 2-4`。
- 1688 观察目标 `3-5` 张；若只有泛经验帖、搬运帖、教程帖，先保留观察，不硬发。

今日新增 1688 判断边界：

- 看商品信息：小件轻货、耗材/配件、宠物/户外/收纳/厨房小工具、可定制/贴牌、已被 Temu/TikTok/Amazon 卷过的同款、高认证或侵权风险品。
- 看用户声音：为什么去 1688 找货、质量/色差/尺寸/包装/发货/售后/沟通踩坑、代采/货代/质检是否变成关键环节、低价算完物流/退货/平台费用后是否仍赚钱。
- 只归入 `电商与卖家 / SKU 选品 / 供应链进货判断`，今天不作为独立成熟主线。

执行结果：

- 正式发布 `30` 张：`hot 15 / signal 13 / breakdown 2`。
- 类别分布：`电商与卖家 20 / AI 与自动化 6 / 商业增长与运营 4`。
- 最新快照：`release-80fdcbfc84b2`，`card_count=1215`；`snapshot / miniRelease / miniFavorites / cloud_db / hot controversy guard / copy guard` 检查通过。
- `trend audit` 仍为 `rebound`，`remaining_new_releases=5`，系统健康未回到 stable。
- 1688 观察线已接入并小配额采集；本日可发的是相邻进货/利润/售后/低价耗材寿命信号，未出现足够强的纯 1688 商品卡。
- V13 timeout 调整后部分 seed 成功，但 `make hotpost-publish-until-exhausted` 和个别商品 seed 仍会长时间无输出；后续需要继续补 collect/LLM 长链路可观测 timeout。
- 本轮结论：发布链达到最低完整线；理想总量 `40-50` 未达成，且 trend audit 仍为 `rebound`，系统健康收口未完成。

## 2026-05-09 日常发卡运营计划

- [ ] 回顾 05-06 至 05-08 运营日志，确认今天不是继续平均补 SEO/PPC，而是 `SKU 选品 + AI` 双主线。
- [ ] 第 1 轮基础盘：先跑 `all-scope 3D` / 默认 freshness workflow，确认自然发布面和首页排序基线。
- [ ] 第 2 轮 SKU 定向补厚：优先 `crossborder-sku-selection-7d`，但 review 时只收 3D 内强信号；7D 只作为 3D 不够时的补货池。
- [ ] 第 3 轮 AI 定向补厚：优先 `ai-7d-llm-agent`，只收 OpenAI / xAI / Gemini / agent 工具链 / AI product adoption 的强事件和强使用反馈。
- [ ] 实验社区小配额探索：显式跑 `probe_community_discovery.py --scope ai-automation` 和 `--scope ecommerce-sellers`；只产候选和报告，不自动入正式社区池、不污染默认 daily collect。
- [ ] Review / publish：按 V13 semantic -> writer -> 人审发布链路执行；热点必须有争议图；标题继续执行中文扫读规则。
- [ ] 发布后验收：`push_mini_snapshot.py --refresh-hot-controversy`、`check_mini_release_sync.py`、小程序 snapshot data 检查；确认首页前两张为 hot，今天新卡按运营时间块排在旧卡前。
- [ ] 收口记录：更新 `reports/ops-log/2026-05-09.md`；只在关键状态变化时更新 phase-log。

今日目标：

- 运营目标约 `40` 张，不为数字放水。
- SKU 选品目标约 `24-28` 张：跨境 SKU、商品替代、众筹/预售、产品页/主图/价格/变体验证。
- AI 目标约 `10-14` 张：OpenAI / xAI / Gemini / agent 工具链 / AI adoption 强信号。
- 其他最多 `0-4` 张，只收 GEO 或平台风向强信号，不让普通 SEO/PPC 抢位。

验收边界：

- 默认先看 `3D`，只有 3D 明显不够厚才使用 `7D` 补货。
- 实验社区只算探索证据，不等于进入 `primary_communities / community_pool`。
- 首页排序继续执行：前两张优先 `hot`，当天运营块排在旧卡前，不做旧卡混排。

## 2026-05-06 日常发卡运营计划

- [x] 回顾 05-03 至 05-05 运营日志：05-03 偏电商 SKU，05-04 偏商业/GEO，05-05 较均衡但 breakdown 为 0。
- [x] 核实 05 月以来新增社区：`r/3Dprinting`、`r/AsianBeauty`、`r/AutoDetailing`、`r/Coffee`、`r/DIY`、`r/NewParents`、`r/SkincareAddiction`、`r/VacuumCleaners`、`r/carcamping`、`r/agi`。
- [x] 基础轮：跑 `all-scope 7d`，先拿今天自然候选，不直接锁死数量。
- [x] 新社区深挖轮：
  - AI：围绕 `r/agi`，并联 `r/singularity / r/OpenAI / r/artificial`，只收 OpenAI/xAI/Gemini/agent 工具链的强争议或强判断增量。
  - SKU 用户需求：`r/AsianBeauty / r/SkincareAddiction / r/Coffee / r/VacuumCleaners / r/AutoDetailing / r/NewParents / r/carcamping / r/DIY / r/3Dprinting`。
  - SKU 验证层：只在商品机会成立后，再用 `AmazonSeller / EtsySellers / shopify / ecommerce / FulfillmentByAmazon` 验证利润、转化、图文、变体或履约。
- [x] GEO 补厚轮：优先 `GEO / AI citation / AI Overview / LLM 引用 / 品牌可见性`，少发普通 SEO/PPC。
- [x] Review / publish：只发布过 V13 semantic、标题去模板化、争议图和 freshness workflow 的卡。
- [x] 发布后收口：推小程序 snapshot、检查 cloud_db / bundle 同步，更新 `reports/ops-log/2026-05-06.md`，新社区继续写入社区收录。

执行结果：

- 第一轮正式发布 `11` 张：`hot 3 / signal 8 / breakdown 0`。
- 类别分布：`AI 与自动化 4 / 商业增长与运营 3 / 电商与卖家 4`。
- 最新快照：`release-6e41636c3a58`，`card_count=678`。
- `snapshot / miniRelease / miniFavorites / cloud_db / hot controversy guard / 小程序 snapshot data` 检查通过。
- 未发布项：GPT-5.5 卡坏 JSON；Demis Hassabis 卡 V13 校验失败；FBAds 情绪帖、SEO 版规帖、Etsy 抱怨帖、Amazon/FBA 操作帖继续挡掉。
- post-publish gate 仍为 `publish_ready=true / actual_total=13`，剩余项不自动发；`trend audit` 仍为 `rebound`。

今日目标窗口：

- `AI 与自动化`：8-10 张，重点是大事件和工具链真实争议。
- `商业增长与运营`：7-9 张，GEO 优先，SEO/PPC 控量。
- `电商与卖家 / SKU`：8-11 张，优先新社区里的真实购买、替代、耐用性、使用场景和众筹/实物信任。
- `breakdown`：1-3 张，有强 thesis 才发，不为结构硬凑。

停机口径：

- 至少完成基础轮、定向补薄轮、停机确认轮。
- 不把固定数量当完成条件；真正停机仍看 `yield_exhausted / publish_ready / final decision / trend audit`。
- 如果新社区进正式发布，必须同步写入运营日志，并确认小程序 `communities` 索引已随 release 生成。

## 2026-05-03 前天 / 昨天 / 今天发卡运营节奏规划

- [x] 回顾最近运营日志：`2026-05-01` 有 `29` 张发布，`2026-05-02 / 2026-05-03` 暂无运营日志。
- [x] 核对当前门禁：V13 和小程序同步链通过，但 no-collect freshness gate 为 `fail`，当前不能直接发。
- [x] 核对当前队列：validate 只有 `1t0d021` 候选和旧草稿 `1su9hhp`；write queue 仍有较多 GiftIdeas / 宽泛 BIFL / Kickstarter 候选，不能当成可直接发布库存。
- [x] 第 1 轮：先跑 `all-scope 7d` 基础轮，拿今天的新鲜盘面，不从旧 publish surface 硬挑。
- [x] 第 2 轮：跑 `crossborder-sku-selection-7d` 定向补薄，重点找 SKU / 产品 / 众筹 / 预售机会；`GiftIdeas` 只作显式礼品线，不算默认 SKU 选品。
- [x] 第 3 轮：重跑 freshness gate + topic tree + queue，按 V13 review / publish；发布后推 mini snapshot 并检查同步。
- [x] 收口：更新 `reports/ops-log/2026-05-03.md`、`INDEX.md` 和 phase-log；不补写伪造的 `2026-05-02` 发布日志。

节奏边界：

- `2026-05-01` 已经是完整发布日，不再为了“前天”重复补同一天。
- `2026-05-02` 是运营缺口日，但现在不能回填过去的 `published_at`；今天如果发卡，只能按 `2026-05-03` 记录，并在日志里说明覆盖的是 05-02/05-03 内容窗口。
- 今日重点：跨境 SKU 选品、产品机会、众筹/预售优先；AI 只挑强热点；SEO/PPC 控量；旧礼物清单、泛生活方式、平台抱怨不发。
- 健康目标不是硬凑数：若新鲜盘足够，今天争取 `8-12` 张强日；若只出 `1-3` 张，必须报成低供给，不包装成正常运营。

执行结果：

- 宽口径 `all-scope 7d` 等待过长且未产出计划文件，已终止，改按定向 SKU profile 执行。
- `crossborder-sku-selection-7d` 新增 `11` 个候选，正式发布 `7` 张：`hot 1 / signal 6 / breakdown 0`，全部为 `电商与卖家`。
- 最新小程序快照：`release-c0a4c90f59bb`，`card_count=572`；snapshot / miniRelease / miniFavorites / cloud_db / 小程序 snapshot data 检查通过。
- final gate 仍显示 `actual_total=5 / publish_ready=true`，但剩余项已人工判为重复、偏题或低优先级；本轮发布完成，严格停机清零未达成。

## 2026-05-03 SKU 7D 二次深挖与发前确认

- [x] 纠正节奏：本轮只做候选发现和语义初筛，不 seed、不 publish。
- [x] 盘点当前 queue：深挖前 `6` 个候选，SKU 相关不足，主要是 AI、SEO 和社区元话题。
- [x] 复跑 `crossborder-sku-selection-7d`：返回 `11` 个候选，但除 `1sw9a4f` 外大多已发布或已打回。
- [x] 拆窄 7D 深挖：
  - 用户需求层：商品替代、品牌 vs 泛品、复购小物
  - 宠物 / 家居层：dog door、宠物上车、异味清洁
  - 户外 / 家居层：露营炉具、清洁 / 收纳
  - 卖家验证层：Etsy 产品图、材料采购、Shopify 变体 / 库存
- [x] 重跑 queue / gate：queue 变成 `15` 个，gate 为 `rewrite`，原因是 `signal_target_window_underfilled`。
- [ ] 等用户确认：先确认候选领域和优先级，再按 V13 seed 生成正式卡片内容。

当前发前判断：

- 真 SKU / 产品机会强候选约 `4` 个：露营炉具、dog door、Etsy makeup bag 产品图、Etsy 材料采购。
- 可选但偏弱候选约 `5` 个：眼镜镜片指数、毛巾异味、Shopify multipack 库存、Shopify 色块滚动、Etsy gift shop 反馈。
- 不建议发：AI 估值重复、SEO de-indexing、社区元讨论、纯清洁技巧、纯宠物行为问题。

## 2026-05-03 SKU 7D/15D 继续深挖

- [x] 继续按用户要求不进入下一步，不 seed、不 publish。
- [x] 7D 拆窄补采：
  - travel / carry：`onebag / ManyBaggers`
  - coffee / kitchen：`espresso / Coffee / Frugal / BuyItForLife`
  - marketplace product page：`EtsySellers / shopify / AmazonSeller`
- [x] 15D 等效扩窗：脚本无原生 `15d`，用 `month` 检索后只保留 `2026-04-18` 之后候选。
- [x] 15D 三层扩窗：
  - 用户需求：耐用品、旅行背包、咖啡设备、小工具
  - 卖家验证：Etsy / Amazon / Shopify 产品页、材料、转化
  - 众筹验证：Kickstarter 实物产品可信度
- [x] 重跑 queue / gate：queue 为 `20` 个，gate 为 `publish`，但包含 AI / SEO / 社区元讨论等非 SKU 项，本轮仍不发布。

新增判断：

- SKU 原料池从 `4` 个强候选扩到约 `10-12` 个可写候选。
- 真正变厚的是旅行背包 / 咖啡设备 / Etsy 实物产品页 / 宠物家居 / 户外炉具。
- Amazon / Shopify 的 15D 验证层净新增不理想：多数是旧题、已发布题或平台操作题。

## 2026-05-03 SKU 7D 吃干净追加轮

- [x] 按用户要求只继续 7D，不开 15D，不 seed、不 publish。
- [x] 补齐 7D 边角类目：家居清洁、众筹实体产品、小工具/耐用品、厨房小家电、育儿、护肤美妆、桌面办公、车载、DIY 家装、maker/3D 打印。
- [x] 对有效桶提高 cap 复采：espresso、carry/outdoor、BIFL/home/pet、maker/parenting。
- [x] 重跑 validate queue：`57` 个候选，其中电商 SKU 候选明显变厚，但仍混有平台抱怨、泛生活、买卖帖和 AI/SEO 非 SKU 项。
- [x] 重跑 no-collect gate：`rewrite / publish_ready=false / actual_total=8 / hot 7 / signal 1`，原因 `signal_target_window_underfilled`。
- [x] 用户确认后，按 V13 semantic seed / review / publish 18 张 SKU 卡，作为 2026-05-02 内容窗口补发。
- [x] 发布后推小程序快照并验收同步：`release-9f44a7745215`，`card_count=590`。
- [x] 更新 `reports/ops-log/2026-05-03.md`；实际 `published_at` 按 2026-05-03 记录，不伪造 05-02 时间。

当前强候选方向：

- espresso / coffee：入门机、磨豆机、无塑料机器、可访问咖啡机。
- carry / outdoor：旅行背包容量、SUV tent、睡垫、露营炉具、雨衣替代。
- BIFL / home / pet：桌面小升级、小工具包、ThumbScraper 替代、dog door、diaper bag。
- marketplace / maker：Etsy 产品图/材料采购、3D 打印商店反推、功能打印产品替代。

发布结果：

- 追加发布 `18` 张：`hot 10 / signal 8 / breakdown 0`，全部为 `电商与卖家`。
- 当日合计 `25` 张：`hot 11 / signal 14 / breakdown 0`。
- `1t00xjt` 两次卡 semantic JSON，未切旧模型；`1sz469k` 已发布重复，用 `1syfama / 1t0j38s` 补位。
- final no-collect gate 仍为 `rewrite / publish_ready=false / actual_total=8`，发卡目标完成，系统收口未完成。

## 2026-05-03 V13 semantic 出卡前增强

- [x] semantic schema：加入 lane-specific readout、结构化 evidence_basis、uncertainty。
- [x] writer/reasoning 注入：让写卡和 breakdown 都看到新的结构化 brief。
- [x] 治理 artifact：V13 shadow JSON / MD / review CSV 都能看到 semantic brief 摘要。
- [x] 验证：先补红灯测试，再实现，再跑目标回归。

验收标准：

- semantic brief 不再只有通用字段；hot / signal / breakdown 都有对应判断位。
- evidence_basis 不再是字符串数组，而是 claim/community/quote/permalink 的结构化对象。
- 真实补卡前可以在 review artifact 里抽样审 Gemini 是否读偏。

## 2026-05-03 V13 LLM 配置生效与 semantic prompt 审计

- [x] 调用链审计：确认 `generate_card_content()` 如何解析 V13 profile、semantic model、writer model、fast/reasoning model。
- [x] 配置生效审计：核对 `backend/config/hotpost_quality.yaml`、`backend/.env`、运行时 loader、测试断言是否一致。
- [x] Prompt 质量审计：判断 semantic brief 是否给 writer/reasoning 足够精准的信息。
- [x] 最小优化：如果问题明确，只增强 semantic prompt 和 schema，不改发卡主链、不重发卡。
- [x] 验证收口：运行目标测试、运行时解析命令、记录 phase-log。

验收标准：

- 运行时解析显示 `fast_model=deepseek/deepseek-v4-flash`，`reasoning_model=deepseek/deepseek-v4-pro`。
- V13 profile 显示 `semantic_model=google/gemini-3-flash-preview`，`writer_model=deepseek/deepseek-v4-pro`。
- semantic prompt 明确产出主体、场景、证据、边界和写作可用判断。

## 2026-05-01 选品真相源纠偏计划

- [x] 配置层：新增 `crossborder-sku-selection-7d`，按“用户需求社区 -> 卖家可行性 -> 众筹预售验证”三层找 SKU 线索。
- [x] 配置层：把 `selection-30d-small-goods-broad` 从默认礼品混合面改回宠物 / 户外 / 家居 / 耐用品小物，不再默认跑 `GiftIdeas`。
- [x] 文档层：更新补卡合同和日常 SOP，明确“选品不是送礼”，卖家社区只做验证层，礼品线必须显式点名才用。
- [x] 记录层：给 2026-05-01 运营日志、CURRENT_STATUS、OPEN_ITEMS 和新 phase 写入口径纠偏，避免后续接手人沿用旧判断。
- [x] 验证层：增加并运行 profile loader 测试，确认新 profile 可加载，且默认 SKU 选品入口不含 `GiftIdeas`。

验收标准：

- 明天定向补薄优先跑 `crossborder-sku-selection-7d`。
- `GiftIdeas` 不再被当成日常跨境 SKU 选品真相源；只在明确“礼品线”任务时使用。
- Seller 社区只用于利润、退货、变体、主图、价格、转化、拥挤度验证，不再作为品类发现第一入口。

## 执行验收口径

- [x] Day1 已补全：`22` 张，按日目标验收为 `AI 6 / 增长 7 / 电商 9`，快照曾同步到 `release-8123fc9ead6f`。
- [x] Day2 已补全：`18` 张，按日目标验收为 `AI 9 / 增长 4 / 电商 5`；增长缺口已用 `r/PPC` 两张 PMax 线索卡补齐。
- [x] Day3 已补全：`23` 张，按日目标验收为 `AI 5 / 增长 5 / 电商 13`；比原计划多 `1` 张 AI，是因为 LLM 记忆卡为强卡，不按死数字丢掉。
- [x] Day4 已补全：`18` 张，按日目标验收为 `AI 4 / 增长 10 / 电商 4`；增长转化先补满，再补 AI / 电商。
- [x] Day5 已补全：`18` 张，按日目标验收为 `AI 6 / 增长 7 / 电商 5`；第三方 SociaVault key 已启用，宽口径 collect 仍受 Reddit 429 / 评论超时影响，最终用已持久化候选池补齐，并补发 1 张 Figma Make 工具效率信号。
- [x] 当前正式发布总数已到 `99` 张：`hot 46 / signal 50 / breakdown 3`，覆盖 `商业增长与运营 33 / AI 与自动化 30 / 电商与卖家 36`。
- [x] 当前最新小程序快照：`release-32d82b05dbcc`，`card_count=536`，snapshot / cloud_db / miniRelease / miniFavorites / 小程序 snapshot data 检查通过。
- [x] 首页排序已补齐三 lane 代表位：front30 为 `hot 15 / signal 14 / breakdown 1`，第 `5` 位出现 breakdown。
- [x] 已严格走 V13 生产口径：`deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro`；上游异常或采集卡住时不切旧模型绕过。
- [x] Day2 不能写成完成的问题已解决：宽口径采集卡住后，改用窄 query + 单社区验证，补齐两张增长卡后再同步发布。
- [x] Day3 no-collect 停机确认通过：`actual_total=0 / yield_exhausted=true / publish_ready=false`，`items=[]`。
- [x] Day5 final no-collect 已清零：`actual_total=0 / yield_exhausted=true / publish_ready=false / items=[]`；`1szbrd1 / 1sy07tv / 1sve3fn` 已按弱证据或低密度打回，`1sxy3fd` 修正串题污染后发布。
- [ ] `trend audit` 尚未回到 `stable`：最新为 `rebound`，`remaining_new_releases=5`，反弹点是 `r/ProductManagement / tools-efficiency`。

原 `95±10`、领域分布和结构分布只作为窗口运营目标，不再作为硬完成条件；硬边界以 V13 质量、freshness、同步链和不回旧模型为准。

## 约束

- `runs_per_day = 3`，每天三轮，双重停机条件
- 默认 `all-scope`，不设 --scope 单 slice
- hot 卡每张必须有 `controversy_chart`
- 补卡只改配置（profile），不改 gate 和主链
- 串行 reject，不并发写 `review_rejections.json`
- V13 生产 profile：`deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro`

## 分天计划（执行节奏）

下面的日目标用于安排补薄顺序，不再作为硬发布数量承诺；实际完成以 V13 质量闸门、freshness、同步链和最终验收字段为准。

### Day 1 — 04-25 均衡起手（目标 20 张：AI 6 / 增长 7 / 电商 7）

**步骤：**
1. `daily_collect.py` — all-scope 采集
2. `run_offline_publish_plan.py` — 生成计划
3. `run_intake_freshness_gate.py --no-named-topics` — 门禁
4. review → publish → snapshot 同步

**验证点：**
- gate_decision = publish
- actual_total ≥ 5（确认有新货）
- 三个 scope 都有卡进入 publish_list
- 无 single_thread_weak_evidence 大面积挡卡

---

### Day 2 — 04-26 AI 补强（目标 18 张：AI 9 / 增长 4 / 电商 5）

**步骤：**
1. `daily_collect.py` — all-scope 基础采集
2. `collect_named_topics.py --watch-profile ai-7d-llm-agent --time-filter week` — AI 定向
3. `run_offline_publish_plan.py`
4. `run_intake_freshness_gate.py` — 含 named-topic
5. review → publish → snapshot 同步

**验证点：**
- AI 面至少 6 张（含 tools-efficiency, ai-product-and-adoption）
- ai-product-and-adoption pack 不为 0
- Hermes 不强发（无真高密度信号则跳过）

---

### Day 3 — 04-27 电商选品（目标 22 张：AI 4 / 增长 5 / 电商 13）

**步骤：**
1. `daily_collect.py` — all-scope
2. `collect_named_topics.py --watch-profile selection-30d-core --time-filter week`
3. `collect_named_topics.py --topic-cluster small-goods --time-filter week`
4. `run_offline_publish_plan.py` + gate
5. review → publish → snapshot 同步

**验证点：**
- selection-signals ≥ 5 张 signal 级选品卡
- small-goods 至少 2 张（非 0）
- EDC cap 守住（demand EDC ≤ 2, tail EDC ≤ 2）

---

### Day 4 — 04-28 增长转化（目标 18 张：AI 4 / 增长 10 / 电商 4）

**步骤：**
1. `daily_collect.py` — all-scope
2. `collect_named_topics.py --topic-cluster funnel-conversion --time-filter week`
3. `collect_named_topics.py --topic-cluster organic-discovery --time-filter week`
4. `run_offline_publish_plan.py` + gate
5. review → publish → snapshot 同步

**验证点：**
- funnel-conversion ≥ 3 张（不再是 1 张薄面）
- organic-discovery ≥ 2 张
- paid-economics 不反弹（≤ 4 张）

---

### Day 5 — 04-29 收口+薄领域（目标 17 张：AI 5 / 增长 7 / 电商 5）

**步骤：**
1. `daily_collect.py` — all-scope
2. `collect_named_topics.py --topic-cluster category-winds --time-filter week`
3. `collect_named_topics.py --topic-cluster platform-policy-shifts --time-filter week`
4. `collect_named_topics.py --topic-cluster key-people-and-route --time-filter week`
5. 末轮 `run_intake_freshness_gate.py --no-collect` — 停机确认
6. `audit_recent_mini_releases.py` — 趋势审计

**验证点：**
- 原计划希望达成：`yield_exhausted=true / actual_total=0 / publish_ready=false`
- 原计划希望达成：`trend audit = stable`
- 实际完成：`18` 张已发布，`AI 6 / 增长 7 / 电商 5`；final no-collect 已到 `actual_total=0 / yield_exhausted=true / publish_ready=false / items=[]`。趋势审计仍为 `rebound`，不能写成 stable，也不能为了 stable 硬发弱卡。

## 每轮发布后固定动作

```bash
python backend/scripts/hotpost/push_mini_snapshot.py
python backend/scripts/hotpost/check_mini_release_sync.py
```

## V13 质量闸门（不通过不发）

| 检查项 | 标准 |
|--------|------|
| title 主体+业务场景 | 必须交代谁+什么事 |
| title 独立可读 | 不依赖 summary_line |
| 报告腔/标题党 | 禁止 |
| 英文缩写粘连 | 禁止 |
| 行动建议混入 why_now | 禁止 |
| 低密度连接词 | 禁止 |
| 机械字数 | 已移除（phase1037），不做硬限制 |

## 2026-04-30 当前执行结果

- Day1 已补全：`22` 张，`AI 6 / 增长 7 / 电商 9`。
- Day2 已补全：`18` 张，`AI 9 / 增长 4 / 电商 5`。
- Day3 已补全：`23` 张，`AI 5 / 增长 5 / 电商 13`；电商选品目标吃满，额外保留 1 张强 AI。
- Day4 已补全：`18` 张，`AI 4 / 增长 10 / 电商 4`；先发增长转化 10 张，再补 AI 4 张、电商 4 张。
- Day5 已补全：`18` 张，`AI 6 / 增长 7 / 电商 5`；未发布 `1szbrd1` Mythos 弱证据草稿，补发 `1sxy3fd` Figma Make 工具效率信号。
- 今日合计已正式发布 `99` 张：`hot 46 / signal 50 / breakdown 3`。
- 今日领域分布：`商业增长与运营 33 / AI 与自动化 30 / 电商与卖家 36`。
- 最新同步：`release-32d82b05dbcc`，`card_count=536`，snapshot / cloud_db / miniRelease / miniFavorites / 小程序 snapshot data 检查通过。
- 首页排序：front30 为 `hot 15 / signal 14 / breakdown 1`，第 `5` 位是 breakdown，已避免 breakdown 被同日较晚 hot/signal 全部挤到首屏外。
- 已发布卡全部走 V13 生产链路生成或复核；命令执行前显式加载 `backend/.env`。
- 已拒绝重复题、证据污染、旧日期低增量、宽泛生活方式和低密度草稿；没有为了补量切旧模型或硬发弱卡。
- 已处理阻断：增长宽口径补采集无输出，根因是多 query / 多 subreddit 串行且结束后才打印；本轮改用窄 query + 单 subreddit 先验货，再持久化 / seed / review。
- Day5 已显式启用 `.env.local` 里的 SociaVault 后备；它能进入链路，但宽口径 collect 在 Reddit 429 和 SociaVault 评论超时时仍不适合继续盲跑。
- 当前 gate：Day5 final no-collect 已清零，`actual_total=0 / yield_exhausted=true / publish_ready=false / items=[]`；validate queue 当前 `0`。
- 趋势验收：`trend audit` 仍未 stable，当前为 `rebound`，`remaining_new_releases=5`。
