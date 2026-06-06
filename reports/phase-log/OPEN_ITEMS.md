# 未完成事项

最后更新：2026-06-06

## 当前未完成的项目事项

### P0

0. Hotpost 2026-06-06 补发已完成，下一步治理模型路由稳定性
   已完成：正式发布 `30` 张，最新快照 `release-fc002edc345d`，总卡数 `1295`；同步链、首页 feed contract、copy guard、hot controversy guard 均通过。运营日志已更新到 `reports/ops-log/2026-06-06.md`。
   当前边界：Reddit 主 OAuth 采集可用，实际阻塞来自 DeepSeek `deepseek-v4-pro` 多次阶段超时；本轮为达成运营补发使用 `HOTPOST_CARD_CONTENT_PROFILE_ID=off` 走既有快速内容路由。`trend audit=watching / remaining_new_releases=5`，不能写 stable。
   下一步：不要继续盲目补量；先复盘 DeepSeek 长响应、阶段 trace、precheck 分布和质量 guard，再决定是否做渠道级替换或分阶段模型路由。

0. Hotpost V13 已接入 AI 预检节点，下一轮真实出卡需要观察误判率
   已完成：`semantic_brief` 新增 `confidence_level / publish_risk / claim_type / evidence_strength / writer_constraints`；`draft_precheck` 已接入 `generate_card_content()`，输出 `PASS / REWRITE / BLOCK`，并通过 `reports/hotpost-draft-precheck/<draft_id>.json` 和 `review_cards.py show-draft` 进入人工 review 面。
   当前边界：precheck 只做 report-only，不自动改稿、不自动发布、不改变 queue 排序；预检异常会记为 `REWRITE + precheck_error`，不能当成通过。
   下一步：下一轮 V13 seed / review 抽样看 `PASS / REWRITE / BLOCK` 分布，重点看它是否能提前拦住证据放大、泛建议和弱主张。

0. 2026-05-26 Hotpost 日运营已完成，下一步进入 2026-05-27 日运营
   已完成：正式发布 `25` 张，最新快照 `release-30b20d1df3a4`，总卡数 `1185`；同步链、首页 feed contract、copy guard 和 hot 争议图 guard 均通过。运营日志已更新到 `reports/ops-log/2026-05-26.md`。
   当前边界：`trend audit` 仍为 `rebound`，不能写成 stable。社区探索有 `4` 个 promote candidate，其中 `r/ebaysellers / r/reselling` 只进入 R12 预审候选，不自动写正式池。
   下一步：2026-05-27 继续 all-scope 日运营，先看 `7d` fresh supply，再按薄领域、品牌舆情、社区探索回流补卡。

0. 2026-05-23/24 Hotpost 两天补发未完整收口，等待 DeepSeek 官方余额恢复
   已完成：本轮先发出 `15` 张 AI 硬信号和 GEO/AEO 卡，最新快照 `release-d1e9b9f26a29`，总卡数 `1149`；同步链、首页前两张 hot、copy guard 和 hot controversy guard 通过。`/workflows` 被洗成 `/流程 s` 的标题污染已修，并补回归测试。
   当前阻塞：V13 writer 官方 DeepSeek `deepseek-v4-pro` 返回 `402 Insufficient Balance`，剩余 SKU / eBay / 品牌选品 `12` 个候选无法继续 seed；不能静默换模型。另有 `1tknjcx` 因 hot 争议图 Gemini 503 未发布。
   下一步：恢复 DeepSeek 官方余额后，继续补 SKU / eBay / 品牌选品候选；不硬发弱 SEO 或泛平台抱怨。

0. Brand Intelligence R16 系统证据包已接入社区推荐解释，下一步审质量并接 Hotpost 上下文
   已完成：主系统品牌收录第一层已经接入已发布 Hotpost 卡、语义库、初始品牌表、历史 archive 品牌包和噪音词表；R15.2 已新增 Dev DB `brand_registry / brand_mentions` 并显式写入；R15.3 已把品牌 digest、质量审查、sidecar 报告和语义审核队列接进日常运营后置动作；R15.4 已补只读服务、API 和预览命令。
   当前结果：Dev DB `brand_registry=1655 / brand_mentions=1254`；状态分布为 `accepted=1457 / verified=13 / candidate=2 / match_guarded=58 / canonical_review=81 / metadata_review=44`。2026-05-13 sidecar 扫描 `881` 张已发布卡，识别 `171` 个品牌、`1571` 条证据，结果为 `verified=13 / candidate=142 / rejected=16 / semantic_review_queue=13 / new_brand_candidates=0`。
   写入产物：`reports/brand-intelligence/brand-registry-r15-2-dev-write-2026-05-12.md`、`.json`、`brand-registry-r15-2-dev-write-rollback-2026-05-12.sql`；幂等复跑产物为 `brand-registry-r15-2-dev-write-rerun-2026-05-12.md/json`。
   Sidecar 产物：`reports/brand-intelligence/brand-ops-sidecar-2026-05-13.md/json`、`brand-semantic-review-queue-2026-05-13.json`，运营日志已补 `Brand Intelligence Sidecar` 段。
   只读消费产物：`reports/brand-intelligence/brand-registry-view-2026-05-13.md/json`；consumer-safe 预览为 `returned_brands=13 / mention_count=710 / consumer_profile=consumer_safe / field_contract_version=brand-consumer-v1 / db_writes=false / miniapp_snapshot_fields=false`。
   审计产物：`reports/brand-intelligence/brand-intelligence-r15-audit-2026-05-13.md`。审计暴露的两个 P1 已修：API / CLI 默认只出 `verified` 品牌；消费字段改为 `display_name / business_domains / interest_tags / evidence_status / display_status / mention_count`，内部治理字段只在 CLI `--profile internal_registry` 下输出。
   R16 产物：`reports/brand-intelligence/brand-system-evidence-2026-05-13.md/json`；当前结果为 `brand_count=117 / mention_count=976 / interest_tag_count=9 / community_count=60`，用于主系统推荐解释、Hotpost sidecar 和语义审核上下文。
   当前边界：R15.4 / R16 都只读；Gold DB、小程序快照、cloud DB、Hotpost 发布链和语义库都未写；`frontend_display=false / miniapp_snapshot_fields=false`，不做前端品牌页或小程序品牌 tab。
   关键修正：`system_evidence` 当前允许 `verified + accepted`，但 `accepted` mention 必须先过配置化 `brand_match_guard`；已确认 `Can Do` 这类普通短语不会进入系统证据包。
   Sidecar 补充：`reports/brand-intelligence/brand-ops-sidecar-2026-05-13.md/json` 已带 `system_evidence_summary`，当前 `system_evidence_brands=117`。
   社区推荐接入：`reports/community-recommendation/preview.md/json` 已重跑为 `tags=9 / recommendations=69 / ready_count=29 / acceptance_passed=true`；`46` 条推荐带品牌证据。品牌证据只增强解释，不参与排序、状态或 ready 判断，因为当前 `mention_count` 不是社区内计数。
   下一步：先审社区推荐质量，再接 Hotpost 后续上下文；后续再补高证据候选晋级队列和 API 高频读取索引。

0. 2026-05-14 Hotpost 日常出卡已完成，待线上 Upsert 导入
   已完成：今日正式发布 `25` 张，最新快照 `release-eca996e28609`，总卡数 `906`；同步检查通过，miniRelease / miniFavorites 派生产物已在小程序子仓提交合并。
   出卡结果：结构 `hot 6 / signal 19`，类别 `电商与卖家 20 / AI 与自动化 4 / 商业增长与运营 1`；本轮按品牌池和 SKU 方向补 eBay、钢笔、露营、onebag、咖啡设备、清洁电器等卡。
   配置变化：新增 `crossborder-sku-brand-ebay-7d` 和 `crossborder-sku-brand-discovery-7d`，并把 eBay 转售 / 翻新 / 退货风险社区纳入显式 experimental probe；默认日常采集仍不包含 experimental。
   当前边界：`trend audit` 为 `watching`，`remaining_new_releases=5`，还不能写成 stable。社区回流为 `already_in_pool=10 / keep_testing=12 / promote_candidate=2 / reject=0`，本轮没有 R12 写入对象。
   下一步：线上导入 `mini_release_meta.wechat-import.json` 和 `mini_release_cards.wechat-import.json` 时继续用 Upsert；后续人工复核 `eBaySellerAdvice` 等 promote candidate 是否进入 R12 预审。

0. 2026-05-13 Hotpost 日常出卡已完成，待线上 Upsert 导入
   已完成：今日正式发布 `25` 张，最新快照 `release-f798171983ef`，总卡数 `881`；同步检查通过，首页 feed contract `30/30`。运营日志已更新到 `reports/ops-log/2026-05-13.md`。
   出卡结果：特朗普访华 x AI 深度信号 `3` 张；AI 侧补 Claude Code、Agent harness、本地记忆、eval、LocalLLaMA / NVIDIA / Optane 等；SKU 和电商侧补除湿、冷藏包、不锈钢平替、Amazon/FBA 经营、AI SaaS 分发失败。
   当前边界：`trend audit` 仍为 `rebound`，`remaining_new_releases=5`，还不能写成 stable。社区回流 R11.5 为 `already_in_pool=8 / keep_testing=8 / promote_candidate=0`，本轮没有 R12 写入对象。
   下一步：线上导入 `mini_release_meta.wechat-import.json` 和 `mini_release_cards.wechat-import.json` 时继续用 Upsert；下一轮继续补 GEO/AEO、AI x 电商和 SKU。

0. 2026-05-11 Hotpost 日常出卡已完成，待线上 Upsert 导入和继续观察 trend
   已完成：今日正式发布 `25` 张，最新快照 `release-8617f1d6f8a6`，总卡数 `822`；`push_mini_snapshot.py` 和 `check_mini_release_sync.py` 已通过，首页 feed contract `30/30`。`signal / hot` prompt 已加入隐性信号规则，要求把用户讨论背后的购买理由、信任变化、成本转移、规则压力或运营风险说出来。
   当前边界：`trend audit` 仍是 `rebound`，`remaining_new_releases=5`；个别候选因 LLM JSON、弱证据、重复发布或语义护栏未发，不能为 stable 硬发低质量卡。
   下一步：线上导入 `backend/data/hotpost/mini_snapshots/cloud_db/mini_release_meta.wechat-import.json` 和 `mini_release_cards.wechat-import.json` 时用 Upsert；下一轮继续从 `7d fresh` 和探索社区隔离报告推进。

0. Reddit Community Intelligence 社区推荐合同修正版已落地，等待用户验收
   当前产品合同：`docs/reference/community-intelligence-clean-contract-2026-05-07.md`。当前系统设计：`docs/superpowers/specs/2026-05-08-community-discovery-recommendation-system-design.md`。当前后端架构：`docs/reference/community-recommendation-backend-architecture-2026-05-08.md`。主线目标是系统根据已有数据和语义库生成可服务标签 / 赛道，用户点击后获得有证据、有理由、长尾优先的 Reddit 社区推荐；不是继续做开放检索框，也不是把 Phase 0 / 1 / 2 治理结果当成产品完成。
   旧社区发现 / 社区池治理链已归档为历史实现：`docs/reference/community-discovery-legacy-archive-2026-05-08.md`。归档含义是“不再作为当前推荐产品主链”，不是否定 DB 8 大领域，也不是删除历史数据。
   已完成事实：治理审计、Phase 1 dry-run、Phase 2 Dev 写入都已经落地；Dev `community_pool` active count 从 `300` 到 `356`，实际新增 `56` 个社区，rollback SQL 在 `reports/community-governance/phase2-dev-write-rollback.sql`。这些是数据准备和库存校准，不是推荐结果页。
   新增完成：后端应用服务入口 `backend/app/services/community/community_recommendation_service.py` 已统一生成 preview、audit 和验收摘要；CLI `backend/scripts/community/community_recommendation_preview.py` 已改为调用同一 service，后续 API / 前端只能做薄适配，不能重写推荐链。当前输出在 `reports/community-recommendation/preview.md` 和 `reports/community-recommendation/preview.json`，生成 `9` 个具像化兴趣标签、`69` 条推荐样例。CI-R2-R5 已补齐：`15D` 活跃探测合同、语义证据摘要、长尾优先 / 泛社区限额、后端验收摘要。R7-R9 已补齐：推荐理由证据化、标签-社区审核表、`content_labels / content_entities` 语义证据密度。
   合同修复：`CAPABILITY_SEEDS` 已从 production code 移除；标签目录、泛社区名单、分数权重、用户推荐文案、审核文案和证据摘要模板改由 `backend/config/community_interest_tags.json` 承载；旧业务分类目录、别名和 Phase 2 分类推断规则改由 `backend/config/community_business_categories.json` 承载。用户可见 preview 区不再暴露 `Hotpost / community_pool / semantic_observation / semantic ledger / 语义账本 / ai_workflow / tools_edc` 等内部词。当前推荐预览 CLI 为 `acceptance_passed=true / ready_count=29 / tags=9 / recommendations=69`，`电商平台政策与风向` 已从空状态修到 `ready / available_community_count=5`，新增审核表在 `reports/community-recommendation/audit.md` 和 `audit.json`。
   新增护栏：旧 `community_pool.categories` 不能单独构成推荐证据，必须同时有标签相关关键词或语义证据命中；已验证 `r/managers` 不再进入“家居生活选品”预览。
   当前边界：`community_pool` 是社区总池，不是推荐面；Hotpost / 小程序是新社区探测器，不能用“没出卡”否定旧 DB 社区。当前 `ready` 主要来自 Hotpost 近期探测 `hotpost_recent_probe`，不是 Dev `posts_hot` 自己恢复了完整 15D 新鲜数据；深层 `semantic_observation / semantic_terms` 仍需后续继续补密度，但推荐层已开始读取 `content_labels / content_entities` 的标签和实体词。当前不做 UserTrack、Web/API、前端入口、开放搜索框、实时重抓或生产写库。
   新增桥接计划：`docs/superpowers/plans/2026-05-08-hotpost-community-pool-feedback-loop-plan.md`。当前 Hotpost 探索社区池已实现配置隔离和只读审计；R10/R11 已落地：日常采集默认不含探索社区，显式 `probe_community_discovery.py --scope ...` 才开启探索试采；回流 dry-run 只读、不写 DB、不自动入池。R11.5 已补社区价值评分算法，规则在 `backend/config/community_value_scoring.json`，报告输出 `observe / testing / validated / pool_candidate / reject` 和分数。2026-05-10 已跑出 3 个真实 `pool_candidate`：`r/aeo`、`r/ai_ugc_marketing`、`r/growthhacking`；`r/etsy` 和 `r/digital_marketing` 已在 pool，只补证据。R12 已写入 Dev `community_pool`，结果为 `active_count_before=356 / active_count_after=359 / inserted=3 / skipped_existing=0 / blocked=0`；Gold DB 和小程序派生产物未写。产物在 `reports/community-governance/community-pool-feedback-dry-run-2026-05-10.md`、`reports/community-governance/community-pool-r12-prewrite-2026-05-10.md` 和 `reports/community-governance/community-pool-r12-dev-write-2026-05-10.md`。
   SOP 已固化：`docs/sop/2026-05-10-Hotpost社区探索回流SOP.md`。后续运营 agent 不能只汇报“探索已触发”，必须按模板汇报 probe、audit、R11.5、R12 预审和 DB writes 状态。
   下一步：
   - 人工复核 R12 写入后的推荐质量，重点看 `r/aeo`、`r/ai_ugc_marketing`、`r/growthhacking` 的标签归属和推荐理由
   - 后续 R12 execute 仍必须逐次人工确认，不能因为本轮通过就改成自动写入
   - 后续人工只重点看 `validated / pool_candidate`，不再逐个社区靠发布验证
   - `r/CursorAI` 继续停在 `validated`，还不是本轮写入对象
   - 用户验收 `reports/community-recommendation/preview.md`、`preview.json`、`audit.md` 和 `audit.json`
   - 先验收后端推荐质量；前端和 API 继续暂缓
   - 若后端推荐质量过关，再决定是否进入 API / 前端；未验收前不做产品界面
   - 后续补强真实 Reddit 活跃探测，让 `recent_posts_15d` 不只依赖 Hotpost 近期探测
   - 后续继续用用户验收结果收紧 `backend/config/community_interest_tags.json`，避免具像化标签重新变宽
   - 后续补强深层 `semantic_observation / semantic_terms`，把审核表里“复核匹配 / 补证据”的社区继续补成可解释推荐
   - 保持用户不输入标签，标签继续由系统根据已有数据生成
   - 治理复查只作为库存校准；不得把 `strong / medium / weak`、泛社区 cap、Hotpost card count 当成产品门禁
   - `ready` 的含义只保留给“近期活跃 + 历史证据或 Hotpost 证据都成立”的推荐，不为了看起来完成而放宽

0. 2026-05-03 线上小程序数据资产保护 P0 和首页首屏性能优化已完成，待部署 `miniRelease`
   已完成：已审核当前线上小程序数据链路，确认主数据从 `mini_release_meta / mini_release_cards` 经 `miniRelease` 云函数输出；当前快照 `release-c0a4c90f59bb` 共 `572` 张卡，后续运营快照已到 `release-9f44a7745215 / card_count=590`。审计结论是：旧版 `miniRelease.getCardDetail` 直接按 `cardId` 返回完整详情，未在云函数内校验 `OPENID`、积分、限速；详情页前端当前是先拿详情再调用 `miniPoints.consumeDetail` 扣积分，因此正常 UI 有积分门槛，但直接云函数调用可以绕过。数据保护规划已写入 `docs/superpowers/specs/2026-05-03-mini-data-protection-plan.md`。本轮已完成 P0 代码修复：`miniRelease.getCardDetail` 返回详情前会服务端校验用户、扣积分或识别免扣 / 已看过状态；旧版前端随后再调用 `miniPoints.consumeDetail` 时不会双扣；`miniRelease.listCards / getCardDetail` 已加服务端访问日志和按小时基础限速。针对用户真机反馈“重新进入首页约 5s 才加载出来”，已把 `miniRelease.listCards` 从全量读取当前 release 再切第一页，改成按 `display_order` 只查首屏 `size + 1` 条；首页 sibling tab 预取改为主列表返回后再启动，避免冷启动时四路列表请求并发放大全量读取。测试结果：`node --test cloudfunctions/tests/*.test.mjs` 为 `91 passed`，`npm run build:weapp:prod` 通过，`git diff --check` 通过。
   当前边界：本轮还没部署线上；限速和访问日志依赖云数据库集合 `mini_access_rate_limits / mini_access_events`，列表分页直查依赖 `mini_release_cards` 的 `release_id + display_order` 索引，部署 `miniRelease` 前需要确认集合和索引存在。列表摘要继续开放，详情完整内容已改成服务端出口保护；P0 可以先只部署 `miniRelease` 云函数，不必先发新版小程序包。
   下一步：
   - 在云数据库确认 / 创建 `mini_access_rate_limits` 和 `mini_access_events`
   - 确认 / 创建 `mini_release_cards` 索引：`release_id` 升序 + `display_order` 升序
   - 部署新版 `miniRelease` 云函数
   - 真机冷启动 / 重新进入首页，确认首屏不再卡约 `5s`
   - 用已登录有积分账号真机打开详情，确认详情正常展示且只扣一次积分
   - 用低积分账号打开新详情，确认返回积分不足且不展示详情
   - 观察 24 小时访问日志后再决定是否收紧列表摘要字段

0. 小程序手机号绑定已真机验通，邀请新用户绑定奖励已按拉新口径收紧
   已完成：`我的` 页已恢复“绑定手机号”入口；`phone-bind` 授权页已改成“微信授权登录 -> 绑定手机号 -> 补头像昵称”的连续流程。入口复用既有 `miniAuth.bindPhone` 和微信 `phonenumber.getPhoneNumber`，不影响白名单详情免扣；积分口径为新用户完成微信登录并绑定手机号后初始 `200`、签到 `30`、邀请新用户绑定奖励 `30`。Tavily 核实微信官方文档后，手机号按钮已改成 `getPhoneNumber|agreePrivacyAuthorization`，让隐私同意和手机号授权走同一个按钮。2026-05-02 用户真机复验已成功绑定手机号；奖励代码已改成：只有新用户通过邀请链接首次授权并绑定手机号后，邀请人才获得 `30` 积分；老用户互相分享、已注册/已绑定用户、同一手机号重复绑定都不计入奖励。前端按钮、小字、积分页和详情页文案已改成“邀请新用户绑定奖励”口径。审计补齐手机号空值硬校验，微信未返回手机号时抛 `PHONE_NUMBER_NOT_FOUND`，不会写空手机号。测试结果：`node --test cloudfunctions/tests/*.test.mjs` 为 `86 passed`，`git diff --check` 通过，`npm run build:weapp:prod` 通过。
   当前边界：代码与构建已就绪；线上还需要部署新版 `miniAuth / miniPoints` 云函数和新版小程序包，才能让真机邀请链路走到新规则。
   剩余风险：同一手机号重复奖励目前靠绑定前查询拦截，正常体验版足够；如果后续公开大规模拉新，需要再补手机号奖励锁或事务式 claim，防极端并发。
   下一步：
   - 部署 `miniAuth / miniPoints` 云函数，并用新版 `dist-prod` 上传体验版
   - 用账号 A 邀请、全新账号 B 打开后完成微信授权和手机号绑定
   - 查库确认 A 增加 `30` 积分、流水为 `invite_reward`，`mini_user_referrals.status=completed`，B 写入 `phone_masked / phone_bound_at / invited_by_openid`
   - 再用两个已授权/已绑定的老账号互相分享，确认不增加积分

0. 2026-05-03 已完成 SKU 纠偏、05-02 内容窗口补发和 AI/SKU x2 追加发布，freshness gate 保持 publish
   已完成：出卡前审计确认 V13 和同步链可用，但旧 publish surface freshness gate 不通过；本轮没有硬发旧草稿，先跑新 `7d` fresh。宽口径 `all-scope 7d` 长时间无输出且未产出计划文件后，收窄到 `crossborder-sku-selection-7d`，第一轮发布 `7` 张。随后按用户确认，把 7D 深挖出的 SKU 强候选作为 2026-05-02 内容窗口补发，追加发布 `18` 张。用户再要求 `AI 信息 x2 / SKU 信息 x2`，已追加发布 `28` 张：`AI 10 / SKU 18`，SEO/PPC 为 `0`。当前当日合计 `53` 张：`hot 26 / signal 27 / breakdown 0`，类别为 `电商与卖家 43 / AI 与自动化 10 / 商业增长与运营 0`。最新小程序快照 `release-33033bf53e07`，`card_count=618`；`check_mini_release_sync.py` 和 `npm run check:mini-snapshot-data` 通过。运营日志已更新到 `reports/ops-log/2026-05-03.md`。
   当前边界：实际 `published_at` 按 2026-05-03 记录，不能伪造 05-02 发布时间。`signal_target_window_underfilled` 根因已修：发布面会优先用 72h 内 signal 替换老 signal，不放宽 gate；AI/SKU x2 后 no-collect gate 为 `decision=publish / publish_ready=true / actual_total=6`，说明还有可审候选，不是停机清零。`trend audit` 仍为 `rebound`，`remaining_new_releases=5`，不能写成 stable。
   下一步：
   - 下一轮继续先跑新 `7d` fresh，再决定是否进入 review / publish
   - SKU 选品优先 `crossborder-sku-selection-7d`，不把 `GiftIdeas` 或平台规则抱怨当默认选品真相源
   - 当前可以基于 publish-ready 面进入人工候选确认，但仍不能跳过 V13 seed / review
   - 每次发布后继续跑 `push_mini_snapshot.py`、`check_mini_release_sync.py` 和 `npm run check:mini-snapshot-data`

0. 2026-05-03 小程序首页体验和 V13 标题治理已修复，待线上重导数据和上传新版小程序
   已完成：V13 title repair / prompt 已补上首页扫读规则，禁止标题默认带 `r/xxxx`，压缩 18-32 字，并拦截“这帖火了 / 评论区在吵 / 有用户开始 / 开始先 / 不再先”等模板句。当前 `release-33033bf53e07` 的 mini snapshot、cloud_db 导入文件、miniRelease / miniFavorites 内置数据已批量打磨标题，`card_count=618`。小程序首页、详情、收藏页标题字体已去 serif 并缩小；首页和详情收藏改为点击即变亮，收藏页取消收藏立即移除卡片。验证结果：后端 V13 title/prompt `20 passed`，生成链路 `85 passed`，小程序 node 测试 `14 passed`，`npm run check:mini-snapshot-data` 通过，`npm run build:weapp` 通过。
   当前边界：线上云数据库仍需要重新导入优化后的 cards；前端体验变化需要上传新版小程序包。`release_id` 保持 `release-33033bf53e07`，这是为了避免再次换 release 导致线上导入和首页指向混乱。
   下一步：
   - 删除或清空线上 `mini_release_cards` 后，重新导入 `backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.wechat-import.json`
   - 如果只重导 cards，`mini_release_meta` 可以保持当前 release；如果做全量重建，再同步导入 meta
   - 用微信开发者工具打开 `hotpost-mini/hotpost-mini-app/dist-dev` 预览；确认标题、tab、收藏即时反馈正常后上传新版小程序

0. 2026-05-01 补卡已完成 29 张，但 SKU 选品口径已纠偏，trend 仍未 stable
   已完成：按用户要求把昨天/今天补卡重心从 AI/SEO/PPC 转向众筹、预售、产品选品、礼物消费场景；本轮正式发布 `29` 张，结构为 `hot 11 / signal 18 / breakdown 0`，全部为 `电商与卖家`。最新小程序快照 `release-e2fb5db69afa`，`card_count=565`；front30 为 `hot 11 / signal 18 / breakdown 1`；`check_mini_release_sync.py`、`npm run check:mini-snapshot-data` 均通过，运营日志已更新到 `reports/ops-log/2026-05-01.md`。
   当前边界：本轮没有继续补 AI / SEO / PPC，也没有为了接近 30 张强发宽泛草稿；`1su9hhp` 仍因泛好物清单感保留未发，`1sxaiai / 1t0d021` 仍在候选队列待下一轮判断。`trend audit` 是 `watching`，`remaining_new_releases=5`，不能写成 stable。事后已纠偏：`GiftIdeas` / 送礼讨论只能算消费需求观察，不能再算严格跨境 SKU 选品。
   2026-05-03 出卡补充：已按 SKU 纠偏口径新增发布 `7` 张，最新小程序快照为 `release-c0a4c90f59bb`，但 final gate 未严格清零，trend 仍未 stable。
   下一步：
   - 下一轮跨境 SKU 选品先跑 `crossborder-sku-selection-7d`，按“用户需求 -> 卖家验证 -> 众筹验证”判断
   - 先跑新 `7d` fresh 采集，再重跑 freshness gate；不从旧 publish surface 里硬挑
   - 下一轮继续先看新 `7d` fresh，再决定是否 seed `1sxaiai / 1t0d021 / 1su9hhp`
   - 不为 trend stable 硬发低密度、旧日期、重复题或泛生活方式卡
   - 每次发布后继续跑 `push_mini_snapshot.py`、`check_mini_release_sync.py` 和 `npm run check:mini-snapshot-data`

0. 2026-04-30 V13 五天回补已按逐日目标发完，final gate 已清零，但 trend 未 stable
   已完成：Day1 `22` 张，Day2 `18` 张，Day3 `23` 张，Day4 `18` 张，Day5 `18` 张，今日正式发布总数 `99` 张，结构为 `hot 46 / signal 50 / breakdown 3`，类别为 `商业增长与运营 33 / AI 与自动化 30 / 电商与卖家 36`。最新小程序快照 `release-32d82b05dbcc`，`card_count=536`，snapshot / cloud_db / miniRelease / miniFavorites / 小程序 snapshot data 检查通过，运营日志已更新；首页 front30 已补成 `hot 15 / signal 14 / breakdown 1`。
   当前边界：Day5 final no-collect gate 已到 `actual_total=0 / yield_exhausted=true / publish_ready=false / items=[]`，validate queue 当时为 `0`；后续 2026-05-01 快照已把 trend 推到 `watching`，`remaining_new_releases=5`，仍不能写成 stable。SociaVault 第三方 key 已启用，但宽口径 collect 仍会被 Reddit 429 和评论超时拖住，不能把后备链路当成无成本补量开关。
   下一步：
   - 不继续盲跑宽口径 collect；只有新 `7d` fresh 或明确薄领域有净新增时再进 review / publish
   - 不为 trend stable 硬发旧日期、重复题、证据污染、已发布同题或质量不稳草稿
   - 每次发布后继续跑 `push_mini_snapshot.py`、`check_mini_release_sync.py` 和 `npm run check:mini-snapshot-data`

0. 2026-04-24 日常出卡已恢复发布，但 trend 仍在 rebound
   已完成：已审计今日 phase-log、ops-log 和出卡池；SociaVault 后备 API 已确认可用，并修掉评论补采批超时过早取消后备请求的问题；同时修掉 `hot` 争议图生成绕开后备客户端的问题。今天已正式发布 `18` 张，最新小程序快照 `release-6f282273ec9b` 同步检查通过。后续又跑了一轮 `all-scope 7d`，SociaVault discover assist 命中 `2` 次；进入发布面的 `6` 个候选经人工审计全是重复、拼接不稳或弱证据，已串行打回。
   当前边界：最新复跑 no-collect gate 后 `actual_total=0 / yield_exhausted=true / publish_ready=false`。这代表当前发布面可以停，不代表全天已稳定收口，因为 trend audit 仍是 `rebound`，还需要 `5` 个新 release 才能回到稳定观察窗。
   下一步：
   - 不继续为补量发布重复 draft
   - 不再继续盲跑 all-scope；下一轮只在新 `7d` fresh 或明确薄领域补薄有净新增时进 review / publish
   - 优先看 `organic-discovery / category-winds / selection-signals` 的新社区和新题材
   - 每次发布后继续跑 `push_mini_snapshot.py` 与 `check_mini_release_sync.py`
   - 继续观察后备 API 在真实 Reddit timeout 下的 fallback 指标

0. `AI / LLM / Agent / Harness` 的 `7d` 补卡入口已经落地，但还要继续看续航
   已完成：只改配置入口 `ai-7d-llm-agent`，已经真实发布 `10` 张 AI 卡；其中原本因为 freshness 进不了主面的 `6` 张，现已通过 `15天补充` 面进入小程序。
   当前边界：这轮已经证明“AI 补卡 + 补充展示面”都能只靠配置层和独立表面落地；但 `Hermes` 在 `7d` 下依然没有足够硬的直连信号，不能为了补量硬塞。
   下一步：
   - 如果继续补 AI 线，先明确是等新的 `7d` fresh，还是切更长时间窗
   - 优先盯：LLM 路线切换、模型退化、Agent 可观测性 / 评测
   - `Hermes` 只在有真实高密度信号时再发，不改 gate，不改主链

0. `small-goods` 的补卡 profile 已收紧并补发 3 张，但还要继续看续航
   已完成：`selection-30d-small-goods-demand / tail` 已按补卡合同收紧，只改 YAML，不改规则；去掉 `homeowners / ApartmentHacks / onebag` 这类高噪音社区，`tail` 的 `candidate_cap` 也从 `4` 降到 `3`。按新配置重跑后，`demand=20`、`tail=12`，并已真实补发 `1se4i3o / 1scp4vn / 1rzx6t5` 三张 small-goods 卡；当前 `hotpost release latest = release-f772e56df334`，小程序快照同步到 `release-be57ce64ac15`。
   当前边界：这轮已经证明“只改配置也能真补 small-goods 卡”，但 `EDC / flashlight / ManyBaggers` 仍然天然更容易打出量；当前已经把 `demand` 里的 `EDC cap` 从 `4` 压到 `2`、`tail` 里的 `EDC cap` 从 `3` 压到 `2`，并新增：
   - `selection-30d-small-goods-broad`
   - `selection-30d-brand-opinion`
   现在 `pet / outdoor / home / gifts / brand / crowdfunding` 都已有独立 30 天补卡入口，不再只能跟着 EDC 跑。
   下一步：
   - 继续沿 `selection-30d-small-goods-broad` 补宠物 / 户外 / 家居小物 / 礼品
   - 用 `selection-30d-brand-opinion` 专门补品牌溢价、平替、众筹和预售舆论
   - `EDC` 保留为配角，不再默认当主补卡面
   - 后续如果还要继续收窄，只继续调 YAML，不回头改 gate 和主链

0. `30d` 去 EDC 化补卡已经跑出第一轮真实结果，但线上可见面还不够厚
   已完成：新加的 `selection-30d-small-goods-broad / selection-30d-brand-opinion` 已分别试跑出 `16 / 8` 个候选，并真实发布 `4` 张新 profile 卡；为保证当前前台立刻有新增可见卡，又补发了 `1so22u3` 这张宠物毛发清理卡。当前小程序快照已更新到 `release-b06569bffde5`，`card_count = 74`。
   当前边界：这轮里真正进小程序可见面的只有 `2` 张：
   - 主面：`1so22u3`
   - `15天补充`：`1sm5wkz`
   另外 `1sc32lq / 1rzb3rq / 1s4qkly` 已进正式 release，但没进当前前台，不是同步失败，而是原帖时间已经超出 `15天补充` 窗口。
   下一步：
   - 继续优先补“内容够硬且还在 15 天里”的 `brand / pet / home` 卡
   - `gift / crowdfunding / outdoor` 先继续收 query 和社区，再补第二轮
   - 不放宽主 freshness，也不拿补卡去冲主规则

0. `30d` 去 EDC 化补卡已经补到第二轮，但薄方向还没彻底打穿
   已完成：在 phase915 的 `5` 张基础上，又真实补发 `1sixo6a / 1soc5l5 / 1slqcxb` 三张；当前相关补卡累计 `8` 张。小程序快照已更新到 `release-2f225c36ef5f`，其中已确认进入可见面的有 `5` 张：
   - 主面：`1so22u3 / 1soc5l5`
   - `15天补充`：`1sm5wkz / 1sixo6a / 1slqcxb`
   当前边界：这说明 `brand / pet / outdoor / 消耗品判断` 这几条已经能持续补出卡，但 `gift / crowdfunding / home odor` 仍然容易混进生活方式噪音或卖家视角贴。
   下一步：
   - 继续优先补 `brand / pet / home`
   - `gift / crowdfunding` 只在出现高密度产品判断时再发
   - `home odor` 继续收 query，避免再被 towels/windows 这类泛技巧贴带偏

0. `gift` 线已经起量，但还没拆到更细的跨境礼品子方向
   已完成：已新增 `selection-30d-gift-crossborder / selection-30d-gift-emotional-value`，并真实补发 `1se1gc0 / 1spqj1u / 1smulbv / 1s36awc / 1sejtkv / 1s4dp64 / 1s37jfw` 七张 gift 卡。当前小程序可见面的 gift 结果已到 `4` 张：
   - 主面：`1spqj1u / 1smulbv`
   - `15天补充`：`1se1gc0 / 1sejtkv`
   当前边界：现在能稳定跑出来的是：
   - 地域独有性
   - 日常实用性
   - 应急小物
   - 升级型礼物
   - 情绪价值但仍像商品的礼物
   - comfort 商品
   但 `品牌礼盒 / 厨房小物 / 节日伴手礼` 还没形成稳定出卡面；`1s36awc / 1s4dp64 / 1s37jfw` 虽然进了正式 release，但没进当前前台；`1sliyon` 被判成 `hot` 后缺争议图，也不能为了补量硬发。
   下一步：
   - 继续沿 `selection-30d-gift-crossborder / selection-30d-gift-emotional-value` 补 gift
   - 如果下一轮继续有量，再拆更窄的 gift 子 profile
   - 继续挡掉纯情绪礼物、手作礼物、泛人生建议这类噪音
   - 优先找仍在 `15天补充` 里的 gift 卡，避免“正式资产增加了，但前台完全不涨”

0. 审计里暴露出的默认策略硬编码已落地修掉，后面不再回头口头争论
   已完成：
   - `named-topic` 的 registry / preset / 默认 preset 已从 Python 常量抽到 `backend/config/hotpost_named_topic_watchlists.yaml`
   - `collect_named_topics.py` 与 `run_intake_freshness_gate.py` 的默认 named-topic preset 已改成读配置
   - `topic_metadata` 已改成认“全部 configured named topics”，不再只认 `daily-watchlist`
   - `freshness gate` 的 lane target 现在按 rolling mix 配置缩放，`recommended_actions` 也不再写死 `--limit 15`
   - `runs_per_day` 已和正式口径对齐到 `3`
   当前边界：这轮收掉的是“默认策略藏在代码里”的问题，不是已经把所有运营动作都自动化；当前运营纪律仍主要在 SOP。
   下一步：
   - 后续新的补卡 / 运营策略，优先落 YAML，不再往 Python 常量里塞
   - 继续按配置驱动去补 `small-goods`
   - 如果后面还要进一步结构化，再考虑把更多 SOP 纪律下沉成 operation contract

0. 补卡合同已经单独审计，但还要继续按它执行，避免后面再漂移
   已完成：已新增补卡合同 [hotpost-card-supplement-contract.md](/Users/hujia/Desktop/RedditSignalScanner/docs/reference/hotpost-card-supplement-contract.md)，明确：
   - 硬规则不动
   - 补卡只改 collect 输入层
   - 长尾新社区属于结果层价值，不是 gate 豁免
   同时 `named_topic_watch_profiles.py` 已增加 `scope / pack / cluster / time_filter` 前置校验。
   当前边界：主风险不是规则被代码偷改，而是口径容易再次漂移；尤其 phase-log 之前还停在“两档 profile”的旧描述。
   下一步：
   - 后续每次补卡都先按合同判断“这是改规则，还是只改配置”
   - phase-log 与 key-os 跟着 profile 真实状态同步
   - 继续把长尾社区发现当成结果层价值来用，但不拿它冲硬门槛

0. `selection-30d-core` 已跑出第二轮真实补卡，但还要继续挑干净增量
   已完成：本轮按 `selection-30d-core` 新增发布 `3` 张选品卡：`1ryygmo / 1s5oofq / 1sa9l80`；当前 `selection-signals` 已到 `61` 张，`hotpost release latest = release-511af28a137d`，小程序同步快照为 `release-d9727a712016`。
   当前边界：这条 profile 现在能稳定补出工具/家电/EDC 的高质量判断卡，但 `dogs` 里的宠物吸尘器讨论仍偏品牌投票，不适合为了数量硬发。
   下一步：
   - 继续沿 `selection-30d-core` 补
   - 优先挑可维修性、总持有成本、结构耐用性这三类
   - 暂时不把重心扩回更噪的场景帖

0. “补上线卡”已经有了独立配置入口，但 profile 还要继续收敛
   已完成：`collect_named_topics.py` 已支持 `--watch-profile / --watch-profile-config / --topic-cluster`；新增配置文件 `backend/config/hotpost_card_supplement_profiles.yaml`，当前内置：
   - `selection-30d-core`
   - `selection-30d-home-decisions`
   - `selection-30d-small-goods-demand`
   - `selection-30d-small-goods-tail`
   - `selection-30d-small-goods-broad`
   - `selection-30d-brand-opinion`
   当前边界：这套入口已经够后续补卡直接用，但 profile 内容仍要继续看真实出卡结果来收敛；当前最明确的新要求是“压 EDC、补非 EDC 与品牌舆论”，所以后续默认不要再拿 `flashlight / ManyBaggers` 当小商品主补卡面。
   下一步：
   - 后续补卡默认先跑 `selection-30d-core`
   - `small-goods` 需求补卡优先跑 `selection-30d-small-goods-demand`
   - 要补 `pet / outdoor / home / gifts` 时，直接切 `selection-30d-small-goods-broad`
   - 要补品牌溢价 / 平替 / 众筹 / 预售时，直接切 `selection-30d-brand-opinion`
   - 要补长尾社区发现时，再切 `selection-30d-small-goods-tail`
   - 只有你明确要家居/购房决策时，再加 `selection-30d-home-decisions`
   - 后面继续按真实出卡结果修 profile，不再改 Python 主链

0. `30d` 选品窗口已经打通，但“变厚”还没有自动等于“变干净”
   已完成：`named-topic/custom watch` 主链已支持 `month`，`collect_named_topics.py` 已能直接收 `--time-filter month`；本轮 `30d` 挖掘后新增发布 `2` 张卡：`1s2vqb9 / 1skepok`；当前 `hotpost release latest = release-b92d867b96f8`，小程序同步快照为 `release-fabc8cf142e4`。
   当前边界：`30d` 的确把候选池拉厚了，但也放大了宽泛社区噪音；`homeowners` 这类社区误命中明显偏多，当前真正干净的新增主要还是来自 `BuyItForLife / flashlight`。
   下一步：
   - 继续用 `30d` 只打配置组合、平替单价、场景配件三类
   - 社区面优先 `BuyItForLife / flashlight / dogs`
   - 少碰宽泛 `homeowners`，避免把“信息变多”做成“噪音变多”

0. 近 `7d` fresh 选品信号已经开始能直接从 Reddit 挖出来，但当前还不算厚
   已完成：新增发布 `2` 张 fresh 选品卡：`1sji2uz / 1so2bpp`；分别覆盖社区配置数据拆解和宠物出行配件替代；当前 `hotpost release latest = release-d674f902fd79`，小程序同步快照为 `release-c8ab947acd95`。同时已打回噪音候选 `cand-ecommerce-sellers-1soqzy5`。
   当前边界：大范围 query 不是直接跑空，就是混进大量 EDC 晒图/身份梗/宠物场景求助；当前 queue 默认还会吞掉有用的 fresh selection 候选，需要 `--live seed` 才能拉进 review。
   下一步：
   - 继续用窄 query 挖 `selection-signals`
   - 优先抓：配置统计、平替对撞、具体场景配件
   - 继续串行清掉会污染选品面的生活方式噪音

0. “选品 / 好物推荐”已补出首轮，但还不算厚
   已完成：新增发布 `3` 张偏选品卡：`1sl84dz / 1so1ohw / 1snq6nb`；分别覆盖详细清单、平替单价、批次缩水风险；当前 `hotpost release latest = release-2cbdbf6ae58a`，小程序同步快照为 `release-08c588667271`。
   当前边界：这轮说明“选品信号能补出来”，但目前仍只是从“偏少”补到“开始可见”；其中 `1snq6nb` 更像批次/版本风险，不是纯粹的好物推荐。
   下一步：
   - 继续把 `selection-signals / small-goods / category-winds` 当成专门薄项盯
   - 继续区分“真选品信号”和“生活方式噪音”
   - 后续补卡优先找：详细清单、平替推荐、批次缩水、价格/功能对撞这四类

0. `2026-04-14 ~ 2026-04-18` 历史漏卡补发已完成首轮收口
   已完成：从历史 `review_queue snapshot` 补发 `5` 张真漏卡：`1snhyck / 1so5ozi / 1slqavn / 1sljggu / 1slqxss`；当前 `hotpost release latest = release-b84077c4458f`，小程序同步快照已更新到 `release-b132b3a180a4`。
   当前边界：这 `5` 张属于历史漏卡补发，不等于今天 fresh `all-scope` 盘面已经恢复健康；当前剩余历史候选大多是噪音、撞题或信息密度不够，其中 `cand-ai-automation-1sm30ry` 已按 `duplicate_story_after_publish` 打回。
   下一步：
   - 主线回到正式 `all-scope` 日运营
   - 只有再发现明确漏发证据时，才继续走 `snapshot -> seed -> review -> publish` 的历史补卡链
   - 不再把“历史可补”包装成“今天 fresh 供给厚了”

0. 今天的日常运营已经正式停机，但结果层仍是 `低供给日`
   已完成：今天累计真实发布 `7` 张；第三轮标准 `all-scope` 已给出正式停机字段：
   - `collect_stopped_by = yield_exhaustion`
   - `dry_cycles = 3`
   - `gate_decision = publish`
   - `actual_total = 0`
   - `publish_ready = false`
   最新同步稳定在 `release-df5466b436d4`，`trend` 继续 `stable`。
   当前边界：能停，不代表结果健康。今天覆盖虽有 `business-growth-ops / ecommerce-sellers / ai-automation`，但厚度仍明显不够；`small-goods / funnel-conversion / category-winds` 没有稳定站住，离“尽量盖全领域树、强日接近 30+”还有距离。
   下一步：
   - 下一轮继续按 `all-scope collect -> sync -> plan -> gate -> review/publish` 跑
   - 优先补 `small-goods / funnel-conversion / category-winds`
   - 每次回报继续拆开写 `collect_stopped_by / gate_decision / actual_total / publish_ready`

0. 当前运营里暴露出的两个真实阻断已经修掉，但还要继续看 live 运行
   已完成：
   - `review_cards seed` 的 LLM 坏 JSON 已增加修复通道
   - `signal validate` 的 `min_test_action` 已重新接回生成链，不再生成出“必挡 draft”
   当前边界：这两条刚在 live 运营中被验证过一次，说明能解当前阻断，但还需要继续看后续 seed / publish 是否持续稳定。
   下一步：
   - 继续在第二轮和后续真实 seed / publish 里观察
   - 如果再出现同类失败，直接按生成链 bug 处理，不再当作运营偶发噪音

0. `review_rejections.json` 当前不适合并发写
   已完成：这轮已坐实并行 `reject` 会覆盖同文件的前一笔结果；重新改成串行后，reject 才稳定进入 `offline_publish_plan` 的过滤链。
   当前边界：这不是当前人工运营的主阻断，但如果后面把 reject 自动化并行化，会再次把 `actual_total` 虚高。
   下一步：
   - 现阶段继续保持串行 reject
   - 如果后面要自动化 review，再补文件锁或原子 merge

0. `hotpost` priority cluster 空白已清零，当前转入运营观察和薄 pack 专项
   已完成：`small-goods` 已从“进池但不上桌”打通到真正进入 publish surface；当前 `ecommerce-sellers` 已有 `2` 条 raw candidate + `1` 条 `group-*` 候选，quote 到 `5 / 5 / 4`；`build_offline_publish_plan(scope=null)` 当前 `blank_priority_clusters = []`，全局 publish list 已出现 `1` 条 `small-goods`。
   当前边界：priority cluster 空白问题已收口，但还不能直接承诺后续每轮都稳定厚出；另有个别旧 upstream 候选会被历史 rejection 隐藏。
   下一步：
   - 继续观察 `small-goods` 在后续真实 collect / publish 里是否持续非零
   - 单独审 `funnel-conversion` 为什么仍是 priority pack 薄项
   - 评估是否要单独调整历史 rejection 对重复老帖的持续隐藏策略

0. 当前小程序问题要继续按“小程序产品态”收，不再回推到大工作区
   已完成：已把执行范围锁回 `hotpost-mini/hotpost-mini-app`；`miniRelease store` 测试通过、`build:weapp:prod` 通过、本地 release 指向一致；首页收藏入口已恢复。
   当前边界：当前小程序依然 `matches_baseline: no`，所以风险更像“产品态偏离基线 + 真机展示待验收”，不是同步链或构建链已坏。
   下一步：继续按最新 release 做微信侧真机检查；如果还有问题，优先收首页 / 详情的正式交互，不再把问题回推到上游供给链。

0. 当前主问题已从“脏 draft 浪费”收口到“供给薄根因”，要先把这个问题聊透并验证
   已完成：字段完整性已前移，脏 draft 不再占 gate / queue 名额；当前工作区里那张脏 draft 仍存在，但只会被标记为 `detail_fields_incomplete`，不再算 ready draft。
   当前边界：当前候选池只剩 `11` 条；四个重点 cluster 现在都是 `0`；当前 publish surface 主阻断原因集中在：
   - `single_thread_weak_evidence`
   - `single_community_weak_evidence`
   - `exploration_requires_two_quotes`
   - `low_information_density`
   这说明现在的主问题已经不是脏 draft，而是 recall 和证据强度一起导致供给仍薄。当前又已代码级确认：
   - recall 问题要继续拆成两段看：
     - spec 展开前的入口限制：`search_subreddit_limit`、`listing_subreddit_limit`、`subreddit_candidate_cap`
     - spec 展开后的 quota 压偏：重点 pack 当前已是 `108 / 96 / 48 / 12` 个 spec，但仍只有 `3 / 4 / 3 / 4` 个 quota
   - raw candidate 在生成时固定 `thread_count = 1`、`community_count = 1`，且 `evidence_quotes` 只保留前 `2` 条；strong tier raw candidate 默认过不了 publish surface，只有 grouped draft 能补出强证据
   下一步：继续按 `all-scope` 保持正式合同不动，专门拆 3 件事：
   - 重点 cluster 是不是主要死在 pack 共享 quota / subreddit cap，而不是单纯 query 太少
   - grouped draft / quote / 多线程多社区证据形成是不是太弱，导致 strong tier 候选天生出不来
   - `small-goods` 为什么在 `selection-signals = 189 specs / quota 7` 下仍然是 `0` 命中，究竟是 query 质量差还是噪声过滤过强

1. `publish-surface gate tiering` 已回灌，但还要用后续 `5` 个新 release 做 live 验证
   已完成：`contract_tiered_surface_v3` 已落进默认 publish surface gate；强证据档与探索档已分开，探索档只对薄 pack / 新节点开放，且仍保留硬垃圾过滤层。当前默认盘面验证已确认：`scope = null`、`latest_status = stable`、watch 项未反弹。
   当前边界：这次已经证明“分层 gate 已吃进默认发布链”，但还没证明它能在后续多轮里持续把每天真正能发的卡做厚。
   下一步：固定跟后续 `5` 个新 release，记录：
   - 实际发布数
   - gate 放行数
   - `gate 放行 -> 最终发布` 转化率
   - 四个薄 pack 是否继续进发布面
   - 四个新节点 / 近空白节点是否继续出现
   - `stable` 是否守住，watch 社区 / pack 是否反弹

2. 今天这轮已完整跑完 3 轮，但结果属于 `异常低供给日`
   已完成：基础轮、定向补薄轮、停机确认轮都已经按正式 SOP 跑完；最终确认 `scope = null`、`yield_exhausted = true`、`actual_total = 0`、`publish_ready = false`，最新 release 到 `release-3fdc73c6a229`，`card_count = 63`，trend 仍是 `stable`。
   当前边界：今天 gate 真实放行 `2 + 3 + 0`，但最终只发出 `1` 张；这不能包装成正常厚度日。
   下一步：继续按 3 轮日节奏跑后续运营日，重点减少两类浪费：
   - 定向补薄后因 freshness 不够被 gate 挡掉
   - 定向补薄后因 freshness 不够被 gate 挡掉
   - 薄 pack / 新节点命中后，仍因证据强度不够进不了最终可发布面

3. collect 长时间等待已经定位到评论 enrichment 批等待链，但还要继续观察真实运行
   已完成：评论 enrichment 已改成有界等待；超时任务会被取消并按空评论收口，不再把整轮 collect 无限拖住。
   当前边界：今天这轮 collect 最终都正常跑完，说明不是死锁；但 Reddit API / 网络波动下仍会出现长时间正常等待。
   下一步：继续在真实日运营里看 comment batch timeout 是否继续稳定避免“卡住错觉”。

4. 刚打通的两个 cluster 还要继续验证“不是只出现一次”
   已完成：`key-people-and-route / platform-policy-shifts` 已经真进 latest release，最新 `release-4127f8731851` 里四个重点 cluster 都不再是 0。
   当前边界：这只能证明“开始打通”，还不能证明“后续会持续稳定出卡”。
   下一步：继续按 `all-scope` 正式链跑后续轮次，重点盯这两个 cluster 是否继续出现，同时守住 `stable`。

5. 供给厚度还要继续做成长期结构，而不是只证明“一轮开始变厚”
   已完成：弱货前移过滤已经落进 `offline_publish_plan / review_queue_policy`；默认 named-topic 补货入口也已补到薄 pack 和空白 cluster。当前离线发布面已到 `candidate_count = 52`、`candidate_publish_surface_count = 34`、`weak_candidate_count = 5`，并且优先薄 pack 已开始真实进入 publish surface：`upstream-winds = 3`、`tools-efficiency = 4`、`funnel-conversion = 2`、`category-winds = 2`。
   当前边界：这轮只能证明“供给开始变厚”，不能说“薄 pack 已稳定补厚”；空白 cluster 也不能说“已清零”，当前只是 `ai-product-and-adoption / small-goods` 开始出现，`key-people-and-route / platform-policy-shifts` 还没真正补起来。
   下一步：继续在后续 live collect / 发布轮次里验证这些 pack / cluster 能否持续进入发布面，同时不把 `stable` 打回去。

6. 下一轮 all-scope freshest supply 还要继续补
   已完成：本轮已经按新停机规则真实跑完，并在“供给开始变厚”后继续把能发的卡发到停机：
   - 第 1 轮 gate 放行 `8` 张，实际发布 `4` 张
   - 第 2 轮 gate 放行 `2` 张，但都被质量闸门挡掉
   - 后续在“供给开始变厚”后，又继续新增发布 `8` 张，最新 release 已到 `release-5e91837e625e`
   - 最终 `no-collect gate` 已跑到：
     - `scope = null`
     - `yield_exhausted = true`
     - `actual_total = 0`
     - `publish_ready = false`
   边界：`hotpost-publish-until-exhausted` 目前还是默认入口名 / 运行纪律，不是 shell 级自动整晚循环器。
   下一步：等下一波 fresh `hot / signal` 真长出来后，再按同一条 all-scope 标准链继续跑；重点看 `publish_contract_summary.current_metrics.publish_surface_conversion`、优先 pack 进发布面数量，以及这些 pack / cluster 是否持续出现。

7. governance collect 已改成 next-cycle preview，但还要继续积累真实增益证据
   已完成：治理补采不再重写本轮 `final decision`，`governance-*` 候选也不再混进当前发布面。
   下一步：在下一轮 all-scope collect / gate 里继续观察 preview 带来的真实补货效果。

8. 发布后真机展示要继续按 release 节点验收
   已完成：仓内 `push_mini_snapshot`、`check_mini_release_sync` 已全绿，release / cloud_db / miniRelease / miniFavorites 已统一到 `release-068686464a53`。
   下一步：继续按最新 release 做微信侧真机检查，确认展示层没有偏差。

9. 题材树治理还要继续从“front30 已改善”推进到“后续新发布本身也更均衡”
   已完成：最新 snapshot 前 30 张已经明显缓解 `FacebookAds / PPC / paid-economics` 吃满问题。
   下一步：继续在后续真实发布轮次里观察 `publish_list` 和新 release 是否也同步变得更均衡，而不只是显示层先变好；当前 250 张总库存结构还不能算健康。

10. 发布面全量治理已经前移到 plan-time，但还要继续看真实新发布是否因此变得更健康
   已完成：`offline_publish_plan` 现在已经开始直接吃 `source_health / scope / pack / community` 的过重信号，不再只靠 snapshot front30 末端纠偏。
   下一步：继续看后续新 release 本身是否开始同步缓解老社区 / 强 pack 过重，而不是只有 visible layer 好看。

11. latest inventory 已经切成 governed rolling inventory，但还要继续看它能否在不回偏的前提下重新变厚
   已完成：最新 snapshot / latest release 已从 `250` 张历史累积盘切到 `64` 张治理后库存，老社区和强 pack 头部已经明显回落。
   下一步：继续观察后续新发布进入后，latest inventory 是否能从 `64` 张逐步扩回更厚的健康库存，而不是重新堆回旧偏斜结构。

12. rolling inventory stability 已跑到稳定态，但后续仍要继续守反弹
   已完成：新增 `hotpost-release-trend-audit` 默认入口；`push_mini_snapshot` 会自动跑趋势审计；`check_mini_release_sync` 也会强校验 trend audit 是否和 latest release 对齐。
   当前状态：baseline = `release-727805c2aaf3`，latest stable = `release-de33e9da1942`，`stable_streak = 5`，`remaining_new_releases = 0`。
   下一步：后续继续保留 trend audit，重点只看是否反弹，不再把这条链当成未完成的稳定性实验。

### P1

1. 全树 freshest supply 的长期稳定性还要继续看
   已完成：`quota-aware crawl`、`value-threshold publishing`、`yield exhaustion` 已按正式默认贯通到真实发布。
   下一步：继续观察是不是每轮都能维持足够的新发现感，而不靠旧库存回填。

2. 默认 named-topic watchlist 现在已补齐三大领域
   已完成：AI / Growth / Ecommerce 都已进入 `daily-watchlist`。
   下一步：继续观察它在真实 collect 里是否能带来更稳的跨域补货。

3. 当前 source_health rewrite 还没有被彻底收掉
   已完成：四层治理已经进入默认 planner / gate / visible 层。
   下一步：继续盯 `upstream-winds`、`tools-efficiency`、`funnel-conversion`、`category-winds`、`kill-signals` 这些高风险 pack 的老来源占比，推动后续新发布继续去老社区化。

### P2

1. 继续把“默认范围 = all-scope”沉成长期可追踪产物
   已完成：默认入口、SOP、真实发布结果都已同步。
   下一步：把后续全树 collect / publish / exhaustion 的关键结果继续写进 `reports/evals/` 和 phase-log，避免未来又被旧 slice 口径覆盖。

## 下一步要完成的事情

0. 2026-06-01 本轮已完成 `7` 张补卡并同步 `release-dea5ddcc9848 / card_count=1265`；下一轮不要再把这轮当未执行事项，只继续补 fresh supply。
0. 模型链路已能区分 `provider_503 / stage_timeout / empty_response`，且 title repair 空响应不再报废整张卡；后续重点观察 DeepSeek 空响应是否仍高频。
0. 当前 trend audit 是 `rebound / remaining_new_releases=5`，不能按 stable 对外表述；后续继续守 release_surface。
0. 主线回到 `all-scope` 正常日运营；历史补卡只保留为明确漏发时的专项动作
0. 后续继续专项补 `selection-signals / small-goods / category-winds`，优先补能帮助做选品判断的卡
0. 继续跑近 `7d` 的窄 query fresh 挖掘；必要时继续用 `--live seed` 绕开 queue 对选品苗子的吞噬
0. 继续把小程序问题限定在 `hotpost-mini` 范围内处理，先走 release 节点真机验收
1. 后续默认都按 `all-scope` 跑 `collect -> sync -> plan -> gate -> review/publish`
2. 补跑一轮标准 collect，优先验证“薄 pack / 空白 cluster 是否开始稳定进发布面”
3. 每次只有同时满足“采集侧已耗尽 + 发布侧无新卡”才停，不再用“发够了”做理由
4. 发布后继续同步 snapshot / cloud_db / miniRelease，并按 release 节点做真机验收
5. 继续观察下一轮真实新发布本身是否也开始缓解老社区 / 强 pack 过重，而不只是 front30 排序层变均衡
6. 继续观察 plan-time `publish_list` 收紧后，source health 高风险 pack 是否开始在新发布里同步回落
7. 继续观察 `governed rolling inventory` 之后，`latest release` 的 full scope / community / pack 结构是否继续改善，而不只是这一次快照切薄了
8. 后续继续保留 release trend audit，重点盯 stable 之后是否重新回到 `rebound`
