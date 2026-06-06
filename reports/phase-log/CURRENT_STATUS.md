# 当前项目状态

最后更新：2026-06-06

## 当前协作口径

- 当前默认协作主链已固定成：`gstack` 负责想，`superpowers` 负责做。
- 决策层默认顺序：
  `gstack-office-hours -> gstack-plan-ceo-review -> gstack-plan-eng-review`
- 执行层默认顺序：
  `using-superpowers -> executing-plans -> 验证/验收`
- 除非用户明确点名，否则不把 `brainstorming`、`writing-plans`、`planning-with-files` 作为默认主入口。
- 当前如果问题落在小程序，默认只围绕 `hotpost-mini/hotpost-mini-app` 处理，不再顺手把问题扩散回大工作区。
- 仓库 `AGENTS.md` 已同步到新的 `key-os` 治理协议：
  - 启动入口改成 `AI_QUICKSTART -> SCOPES -> PROJECT_DASHBOARD`
  - `daily` 默认改用 `判断 / 变化 / 下一步`
  - `ANTI_BLOAT_POLICY` 已收进仓库级约束

## 当前主判断

Reddit Community Intelligence 当前口径已纠偏：主线目标不是继续证明 Phase 0 / 1 / 2 治理正确，也不是回到空白检索框；当前目标是“系统根据已有数据和语义库生成可服务标签 / 赛道，用户点击后获得有证据、有理由、长尾优先的 Reddit 社区推荐”。

## 2026-06-06 Hotpost 补发状态

- 本轮按多日空窗后的最低完整线完成 Hotpost 补发：正式发布 `30` 张，最新小程序快照 `release-fc002edc345d`，总卡数 `1295`。
- 结构为 `signal 21 / hot 5 / breakdown 4`；类别为 `电商与卖家 20 / 商业增长与运营 8 / AI 与自动化 2`。
- 同步链已通过：snapshot、miniRelease、miniFavorites、cloud_db 均为 `feed_contract=30/30`；copy guard、hot controversy guard、trend audit guard 均通过。
- 本轮验证 Reddit 主 OAuth 采集可用；实际阻塞不在 Reddit 连接，而在 DeepSeek `deepseek-v4-pro` 多次阶段超时和 hot 发布 schema 泄漏 `llm_trace`。
- 已修复 hot 发布时 `controversy_meta.llm_trace` 泄漏导致 schema validation 失败的问题，并补回归测试。
- 当前边界：为完成运营补发，本轮使用 `HOTPOST_CARD_CONTENT_PROFILE_ID=off` 走既有快速内容路由；DeepSeek 长响应和模型路由稳定性仍需后续治理，`trend audit` 仍为 `watching / remaining_new_releases=5`，不能写 stable。

## 2026-06-01 Hotpost V13 模型链路稳定性

- 本轮出卡低于目标的工程侧主因已经定位：key 层不是主因；主要问题是 OpenAI-compatible SDK 分支没有显式接收 timeout、`_generate_json()` 缺阶段级硬超时、空 JSON / 坏 JSON 分类太粗、generation trace 看不到子阶段。
- 已修复：SDK 请求显式带 `timeout`；`semantic_brief / writer / draft_precheck / json_retry / json_repair` 进入阶段级 `asyncio.wait_for`；空响应分类为 `empty_response` 且不再同模型修复；前后夹文字但中间有 JSON object 的响应会先抽取 JSON。
- `draft_precheck` 阶段超时现在会降级为 `REWRITE + precheck_error + stage_timeout`，不再把整条 seed 链直接打死；失败 trace 会带 `sub_stages / error_type / duration / provider`。
- 当前验证：相关回归 `104 passed`，`mypy --strict` 覆盖 3 个修改源文件通过，`py_compile` 和 `git diff --check` 通过。
- 当前边界：没有做自动换渠道或静默 fallback；DeepSeek / Gemini 的真实渠道健康仍要在下一轮运营出卡时观察。

## 2026-05-29 Hotpost V13 流程优化状态

- V13 出卡链路已升级为：`semantic_brief -> writer -> draft_precheck -> 人工 review`。
- `semantic_brief` 已新增结构化质量合同：`confidence_level / publish_risk / claim_type / evidence_strength / writer_constraints`，让节点 1 到节点 2 的传递可机读、可测试。
- `draft_precheck` 是人工 review 前的 report-only 节点，输出 `PASS / REWRITE / BLOCK`；不自动改稿、不自动发布，结果保存到 `reports/hotpost-draft-precheck/<draft_id>.json`。
- `review_cards.py show-draft` 会展示 precheck；breakdown/write 最终稿不会丢预检；预检异常会落成 `REWRITE + precheck_error`，不打断草稿生成。
- 当前验证：相关回归 `20 passed`，`py_compile` 通过。

## 2026-05-26 Hotpost 当前状态

- 2026-05-26 日运营已完成 `25` 张；最新小程序快照 `release-30b20d1df3a4`，总卡数 `1185`。
- 结构 `hot 9 / signal 13 / breakdown 3`；类别 `AI 与自动化 11 / 电商与卖家 9 / 商业增长与运营 5`。
- 同步链通过：`miniRelease / miniFavorites / cloud_db` 一致；首页 feed contract `30/30`，copy guard 和 hot 争议图 guard 通过。
- 社区探索回流：`audit_rows=24 / promote_candidate=4 / keep_testing=8 / reject=0`，`r/ebaysellers / r/reselling` 进入 R12 预审候选，不自动写正式池。
- 品牌 sidecar：扫描 `1185` 张，识别 `213` 个品牌/平台，`verified=15 / candidate=181 / rejected=17 / db_writes=false`。
- 当前边界：`trend audit=rebound`，不能写 stable；下一轮继续按 `7d` fresh supply 和品牌/社区回流推进。

## 2026-05-12 Brand Intelligence R15 当前状态

- 品牌收录口径已固定：主系统负责品牌识别、证据和后续注册表；Hotpost / 小程序只作为信号来源和消费端，不维护品牌主数据。
- R15.0 dry-run 已落地：`backend/app/services/brand_intelligence/` 从 `load_published_cards()` 只读已发布卡，生成报告，不写 DB。
- R15.0.5 已把分散品牌资源归一成只读 `brand source catalog`：`unified_lexicon=8 / brands_base=31 / archive=1693 / noise=184`，合并后 `total_entries=1845`，生命周期为 `approved=8 / seed=27 / candidate=1627 / rejected=183`。
- R15.1 质量审查已落地：新增配置化 `brand_quality_rules.json`，输出 `candidate / verified / rejected` 三种审核状态、用户兴趣标签回映射和噪音审计，不写 DB。
- R15.1.5 已按用户校正口径补上 archive 品牌池预审：`archive/brands_*.yml` 是用户历史手工核实过的品牌资源，不再默认当弱候选；本轮只做去重、领域归类和噪音重叠标记。
- 当前产物：`reports/brand-intelligence/brand-source-catalog-2026-05-12.md`、`.json`、`brand-digest-2026-05-12.md`、`.json`、`brand-quality-review-2026-05-12.md`、`.json`。
- 当前跑数：quality review 扫描 `852` 张卡、识别 `169` 个品牌/候选，结果为 `verified=13 / candidate=140 / rejected=16 / noise_items=16 / db_writes=false`。
- Archive 品牌池预审结果：`raw_rows=1693 / brand_count=1644 / duplicate_rows=49 / ready_for_review=1641 / needs_review=3 / db_writes=false`，输出在 `archive-brand-pool-preaudit-2026-05-12.md/json/csv`。
- Agent 初审已完成：`approve=1625 / approve_with_ambiguous_name_guard=16 / review_noise_config_keep_likely=3 / multi_domain_count=44`；初审不建议删除品牌，只建议 19 个重点细审，输出在 `archive-brand-pool-agent-initial-review-2026-05-12.md/csv/json`。
- 严格审计已完成：`P0_clean_accept=1461 / P1_text_match_risk=58 / P2_canonical_form_review=81 / P3_metadata_review=44 / strict_focus_total=183`；严格审计仍不建议删除品牌，重点是给后续自动文本匹配和入库 canonical 加护栏。
- R15.2 Dev DB 注册表已落地：新增 `brand_registry / brand_mentions`，显式执行写入 `reddit_signal_scanner_dev`，结果为 `brand_registry=1655 / brand_mentions=1254`。
- R15.2 写入后复跑已验证幂等：第二次 dry-run 为 `would_insert_registry_rows=0 / would_insert_mentions=0`；rollback SQL 已生成。
- 当前状态分布：`accepted=1457 / verified=13 / candidate=2 / match_guarded=58 / canonical_review=81 / metadata_review=44`。
- R15.2 执行中顺手修掉 Dev 迁移阻塞的历史债：旧 `tasks` 终态约束和一条 failed 任务脏数据会卡住 Alembic，现在 Dev 可升级到 `20260512_000001`。
- R15.3 日常运营 sidecar 已落地：`make brand-ops-sidecar` 会在发布、小程序快照和社区回流后生成品牌 digest、质量审查、sidecar 报告和语义审核队列。
- 2026-05-13 sidecar 跑数：扫描 `881` 张已发布卡，识别 `171` 个品牌，证据 `1571` 条，`verified=13 / candidate=142 / rejected=16`，语义审核队列 `13`，相对 Dev 注册表新品牌候选 `0`。
- 当前边界：R15.3 不参与发布门禁，`blocks_publish=false / db_writes=false / auto_write_semantic_lexicon=false`；Gold DB、小程序快照、cloud DB 和 Hotpost 发布链未写。
- R15.4 只读品牌注册表服务已落地：新增共享读取服务、`/brand-intelligence/registry` API 入口和 `make brand-registry-view` 预览命令，主系统 / 后续前端 / 小程序支线都读同一个 `brand_registry`。
- 2026-05-13 consumer-safe 预览结果：`returned_brands=13 / mention_count=710 / consumer_profile=consumer_safe / field_contract_version=brand-consumer-v1 / db_writes=false / miniapp_snapshot_fields=false`，产物为 `reports/brand-intelligence/brand-registry-view-2026-05-13.md/json`。
- R15 全面审计暴露的两个 P1 已修：API / CLI 默认只出 `verified` 品牌；消费字段改为 `display_name / business_domains / interest_tags / evidence_status / display_status / mention_count`，内部治理字段只在 CLI `--profile internal_registry` 下输出。
- 当前边界：R15.4 仍只读，不写 Gold DB、不写小程序 snapshot、不自动写语义库；小程序展示字段还没接入，前端也没做。
- R16 系统证据包已落地并补上文本护栏：`make brand-system-evidence` 会从 `brand_registry + brand_mentions` 生成后端只读证据包，按业务标签和社区输出品牌证据；`system_evidence` 当前允许 `verified + accepted`，但 `accepted` mention 必须先过 `brand_match_guard`。
- 2026-05-13 当前结果：`brand_count=117 / mention_count=976 / interest_tag_count=9 / community_count=60`；已确认普通短语误伤样本 `Can Do` 不再进入系统证据包。
- R16 sidecar 接入已完成：`brand-ops-sidecar-2026-05-13` 带 `system_evidence_summary`，当前 `system_evidence_brands=117`。
- R16 社区推荐解释接入已完成：`reports/community-recommendation/preview.md/json` 已重跑，结果为 `tags=9 / recommendations=69 / ready_count=29 / acceptance_passed=true`；其中 `46` 条推荐带品牌证据，用户理由只展示品牌名和业务含义，内部来源只留在 Debug Evidence。
- 关键边界：品牌证据只增强解释，不参与排序、状态或 ready 判断；当前 `community_brand_evidence.mention_count` 是品牌全局计数，不是社区内计数，不能拿来当算法权重。
- R16 边界：`db_writes=false / frontend_display=false / miniapp_snapshot_fields=false`；品牌池先服务推荐解释、Hotpost sidecar 和语义审核，不做前端品牌页或小程序品牌 tab。
- 下一步：审推荐质量，再补 Hotpost 后续上下文的消费方式；语义库写入仍需人工审核，不自动写。

## 2026-05-24 Hotpost 当前状态

- 2026-05-23 / 2026-05-24 两天补发已推进第一段，但未完整收口；仓内没有 2026-05-23 运营日志，本轮按 5/24 实际发布时间记录。
- 已正式追加 `15` 张，最新小程序快照 `release-d1e9b9f26a29`，总卡数 `1149`。
- 结构 `hot 9 / signal 6`；类别 `AI 与自动化 11 / 商业增长与运营 4`。本轮先发 AI 硬信号和 GEO/AEO，SKU / eBay / 品牌选品未补齐。
- 首页排序通过：前两张均为 `hot`；同步链通过：snapshot、cloud_db、miniRelease、miniFavorites 一致；copy guard 和 hot controversy guard 通过。
- 已修复 `/workflows` 被标题清洗成 `/流程 s` 的问题；新增 `slash command` 回归测试，当前快照无 `/流程` 残留。
- 社区探索回流：pre `10` 个实验候选；post `already_in_pool=12 / keep_testing=8 / promote_candidate=4 / reject=0`，不自动写正式池。
- 品牌 sidecar 已跑：`brands_observed=213 / verified=15 / new_brand_candidates=0 / semantic_review_queue=15 / db_writes=false`。
- 当前阻塞：V13 writer 官方 DeepSeek `deepseek-v4-pro` 返回 `402 Insufficient Balance`；剩余 SKU / eBay / 品牌选品 `12` 个候选不能继续 seed，不能静默换模型。
- 当前边界：`trend audit=watching / remaining_new_releases=5`，不能写 stable；`1tknjcx` 因 hot 争议图 Gemini 503 被硬门槛挡住。

## 2026-05-18 Hotpost 当前状态

- 今日按 `3D 优先，不够再扩 7D` 完成日常发卡 `27` 张；最新小程序快照 `release-d55b3b8369dd`，总卡数 `1028`。
- 结构 `hot 14 / signal 13`；类别 `商业增长与运营 11 / 电商与卖家 10 / AI 与自动化 6`。本轮重点纠偏：商业增长 / GEO / AEO 从最近薄项补回主发布面。
- 首页排序通过：前两张为 `hot`；同步链通过：snapshot、cloud_db、miniRelease、miniFavorites 一致；copy guard 和 hot controversy guard 通过。
- 社区探索回流：pre `11` 个实验候选；post `already_in_pool=10 / keep_testing=12 / promote_candidate=2 / reject=0`，两个 promote 仍是 `r/eBaySellerAdvice`，不自动写正式池。
- R12 预审已收口：`r/eBaySellerAdvice` 两条 promote 证据已合并成一条，并已写入 Dev community pool；复跑 dry-run 显示 `skipped_existing=1 / would_insert=0`，确认不会重复写。
- 品牌 sidecar 已复核：`brands_observed=196 / verified=15 / new_brand_candidates=0 / semantic_review_queue=15 / db_writes=false`；`Mirror` 是小写动词误识别，已进入噪音项。
- 当前边界：final no-collect gate 仍 `publish_ready=true / actual_total=8`；`trend audit=rebound`，不能写 stable。今天发卡目标完成，但系统收口未完成。

## 2026-05-19 Hotpost 当前状态

- 今日按 `3D 优先，7D 补薄` 完成日常发卡 `30` 张；最新小程序快照 `release-d5fdfced5175`，总卡数 `1058`。
- 结构 `hot 17 / signal 13`；类别 `电商与卖家 17 / AI 与自动化 11 / 商业增长与运营 2`。本轮主线是 SKU / eBay / 品牌舆情，AI 只补硬信号。
- 首页排序通过：前两张均为 `hot`；同步链通过：snapshot、cloud_db、miniRelease、miniFavorites 一致；copy guard 和 hot controversy guard 通过。
- 社区探索回流：pre `13` 个实验候选；post `already_in_pool=12 / keep_testing=10 / promote_candidate=2 / reject=0`，不自动写正式池。
- 品牌 sidecar 已跑：`brands_observed=202 / verified=15 / new_brand_candidates=0 / semantic_review_queue=15 / db_writes=false`。
- 当前边界：final no-collect gate 仍 `publish_ready=true / actual_total=13`；`trend audit=rebound`，不能写 stable。今天发卡密度完成，但系统仍有剩余可发布候选。

## 2026-05-20 Hotpost 当前状态

- 今日按 `SKU / 品牌舆情优先，AI 保留硬信号` 完成日常发卡 `25` 张；最新小程序快照 `release-9bc24a160791`，总卡数 `1083`。
- 结构 `hot 12 / signal 13`；类别 `电商与卖家 15 / 商业增长与运营 6 / AI 与自动化 4`。本轮补入 eBay 转售风控、咖啡机 / 磨豆机、旅行包、钢笔、耐用品价格判断、AEO/GEO 和 Meta Ads。
- 首页排序通过：前两张均为 `hot`；同步链通过：snapshot、cloud_db、miniRelease、miniFavorites 一致；copy guard 和 hot controversy guard 通过。
- 社区探索回流：pre `13` 个实验候选；post `already_in_pool=12 / keep_testing=8 / promote_candidate=4 / reject=0`，不自动写正式池。
- 品牌 sidecar 已跑：`brands_observed=206 / verified=15 / new_brand_candidates=0 / semantic_review_queue=15 / db_writes=false`。
- 当前边界：final no-collect gate 仍 `publish_ready=true / actual_total=12`；`trend audit=rebound`，不能写 stable。V13 Gemini 语义层有超时和 JSON repair，但未阻断今日发布。

## 2026-05-21 Hotpost 当前状态

- 今日按 `品牌舆情 + SKU 选品策略优先` 完成日常发卡 `26` 张；最新小程序快照 `release-7b03ab193ce4`，总卡数 `1109`。
- 结构 `hot 13 / signal 13`；类别 `电商与卖家 21 / 商业增长与运营 3 / AI 与自动化 2`。本轮主线是高端基本款溢价、钢笔/咖啡/手电/冰箱耐用反馈、eBay 转售、Kickstarter 履约、Crocs 授权风险、DTC 退货成本和 Amazon 补货策略。
- 首页排序通过：前两张均为 `hot`；同步链通过：snapshot、cloud_db、miniRelease、miniFavorites 一致；copy guard 和 hot controversy guard 通过。
- 社区探索回流：pre `16` 个实验候选；post `already_in_pool=12 / keep_testing=8 / promote_candidate=4 / reject=0`，不自动写正式池。
- 品牌 sidecar 已跑：`brands_observed=209 / verified=15 / new_brand_candidates=0 / semantic_review_queue=15 / db_writes=false`。
- 当前边界：final no-collect gate 仍 `publish_ready=true / actual_total=9`；`trend audit=rebound`，不能写 stable。今天发卡目标完成，但系统收口未完成。

## 2026-05-22 Hotpost 当前状态

- 今日按 `品牌舆情 + SKU 选品策略` 完成日常发卡 `25` 张；最新小程序快照 `release-e24eb0af5574`，总卡数 `1134`。
- 结构 `hot 11 / signal 14`；类别 `电商与卖家 17 / 商业增长与运营 5 / AI 与自动化 3`。本轮主线是 Darn Tough / Puma、Brooklinen、LAMY / Kaweco / Leonardo、宜家沙发与垃圾桶、Aer / Goruck、车钥匙金属壳、扫地机器人、ITOP 杠杆机、eBay / reselling 和 Shopify 操作摩擦。
- 首页排序通过：前两张均为 `hot`；同步链通过：snapshot、cloud_db、miniRelease、miniFavorites 一致；copy guard 和 hot controversy guard 通过。
- 社区探索回流：pre `16` 个实验候选；post `already_in_pool=12 / keep_testing=8 / promote_candidate=4 / reject=0`，不自动写正式池。
- 品牌 sidecar 已跑：`brands_observed=213 / verified=15 / new_brand_candidates=0 / semantic_review_queue=15 / db_writes=false`。
- 当前边界：final no-collect gate 仍 `publish_ready=true / actual_total=8`；`trend audit=rebound`，不能写 stable。`GPT Image 2.0` hot 卡因争议图 Gemini 503 被发布硬门槛挡住。

## 2026-05-17 Hotpost 当前状态

- 5/16 未发卡，本轮一次性补发 5/16 + 5/17，正式追加 `51` 张；最新小程序快照 `release-ced31a676824`，总卡数 `1001`。
- 结构 `hot 16 / signal 35`；类别 `AI 与自动化 21 / 电商与卖家 30`。本轮没有强发商业增长/GEO，原因是强候选少，`ChatGPT Ads beta` 在 V13 JSON repair 阶段失败。
- 首页排序通过：前两张为 `hot`；同步链通过：snapshot、cloud_db、miniRelease、miniFavorites 一致；copy guard 修复后通过。
- 社区探索回流：pre `13` 个实验候选；post `already_in_pool=10 / keep_testing=12 / promote_candidate=2 / reject=0`，不自动写正式池。
- 品牌 sidecar 已跑：`brands_observed=194 / verified=15 / semantic_review_queue=15 / db_writes=false`。
- 当前边界：运营日志按实际发布时间归档，所以 `51` 张记入 2026-05-17；final no-collect gate 仍 `publish_ready=true / actual_total=9`，但剩余多为弱项/重复；`trend audit=watching`，不能写 stable。

## 2026-05-15 Hotpost 当前状态

- 今日先按 `3D 优先，3D 不足再扩 7D` 完成日常发卡 `25` 张，随后按突发热点追加中美会谈专题 `12` 张；当天合计 `37` 张。
- 最新小程序快照为 `release-90e8299bfe62`，总卡数 `950`；结构为 `hot 19 / signal 18`。
- 类别为 `电商与卖家 17 / AI 与自动化 10 / 商业增长与运营 10`；日常主线是 SKU / 品牌舆情 / eBay 转售与平台风险，专题补入台湾红线、AI 芯片、能源、波音和中美谈判筹码。
- 同步链已验收：snapshot、cloud_db、`miniRelease / miniFavorites` 一致，首页 feed contract `30/30`，首页前两张为 `hot`。
- 社区探索回流：pre probe `2` 个方向、`8` 个实验候选；post 为 `already_in_pool=10 / keep_testing=12 / promote_candidate=2 / reject=0`，不自动写正式池。
- 当前边界：`trend audit` 仍为 `rebound`，`remaining_new_releases=5`，不能写成 stable。

## 2026-05-11 Hotpost 当前状态

- 今日已按日常运营节奏发布 `25` 张，最新小程序快照 `release-8617f1d6f8a6`，总卡数 `822`。
- `signal / hot` 生成链已加入隐性信号要求：标题、摘要、why_now 和正文必须从证据里提炼“为什么这事有商业含义”，不能只复述表层热度。
- 同步链已验收：snapshot、cloud_db、`miniRelease / miniFavorites` 一致，首页 feed contract `30/30`。
- 探索社区仍保持隔离：本轮 probe 只写 `experimental_candidates` 和探索审计报告，不写正式候选池，不自动入正式社区池。
- 当前边界：`trend audit` 仍为 `rebound`，`remaining_new_releases=5`，不能写成 stable。

## 2026-05-14 Hotpost 当前状态

- 今日已发布 `25` 张，最新小程序快照 `release-eca996e28609`，总卡数 `906`。
- 结构为 `hot 6 / signal 19`；类别为 `电商与卖家 20 / AI 与自动化 4 / 商业增长与运营 1`。
- 本轮按“品牌池先命中，再探索新品牌”补 SKU，新增 `crossborder-sku-brand-ebay-7d` 和 `crossborder-sku-brand-discovery-7d` 两个小配额 profile。
- 同步链已验收：snapshot、cloud_db、`miniRelease / miniFavorites` 一致；小程序子仓已把 `release-eca996e28609` 派生产物提交合并。
- 社区探索回流：post 为 `already_in_pool=10 / keep_testing=12 / promote_candidate=2 / reject=0`；`eBaySellerAdvice` 等只进入待确认，不自动写正式池。
- 当前边界：`trend audit` 为 `watching`，`remaining_new_releases=5`，还不能写成 stable；下一步是线上 Upsert 导入 cloud_db 两份文件。

## 2026-05-13 Hotpost 当前状态

- 今日已发布 `25` 张，最新小程序快照 `release-f798171983ef`，总卡数 `881`。
- 结构为 `hot 12 / signal 12 / breakdown 1`；类别为 `AI 与自动化 14 / 电商与卖家 6 / 商业增长与运营 5`。
- 临时插入特朗普访华 x AI 深度信号 `3` 张：随行名单市场押注、黄仁勋与芯片管制、Anthropic 拒绝中国接触新模型。
- 今日补厚主线：Claude Code / Agent harness / 本地记忆 / eval / LocalLLaMA 模型与硬件、SKU 选品、Amazon/FBA 经营和 AI SaaS 分发失败。
- 同步链已验收：snapshot、cloud_db、`miniRelease / miniFavorites` 一致，首页 feed contract `30/30`；front30 前两张为 `hot`。
- 社区探索回流：pre probe 产出 `11` 个 experimental candidates；post 为 `already_in_pool=8 / keep_testing=8 / promote_candidate=0`，本轮不做 R12 写入。
- 品牌池 sidecar 已按 R15.3 跑完：`brands_observed=171 / verified=13 / noise_items=16 / semantic_review_queue=13 / db_writes=false`。
- 当前边界：`trend audit` 仍为 `rebound`，`remaining_new_releases=5`，还不能写成 stable。

## 2026-05-12 Hotpost 当前状态

- 今日已发布 `34` 张，最新小程序快照 `release-d3534e9b4b86`，总卡数 `856`。
- 结构为 `hot 13 / signal 20 / breakdown 1`；类别为 `AI 与自动化 21 / 电商与卖家 8 / 商业增长与运营 5`。
- 本轮补卡新增 `5` 张：Claude Mythos `2`、GitHub / Copilot `2`、DeepSeek `1`；Musk 相关 3D 内没有足够硬的新信号，未强发。
- 突发插入新增 `4` 张特朗普访华 x AI 深度解读卡：中美 AI 沟通、美国模型预审、xAI 政府模型评估、高端 AI 芯片谈判底牌；4 张均进首页前 `13`，前两张仍保持 `hot`。
- `AI_UGC_Marketing / GrowthHacking / Etsy` 的新社区验证结果已进入正式卡和探索审计。
- 同步链已验收：snapshot、cloud_db、`miniRelease / miniFavorites` 一致，首页 feed contract `30/30`。
- 社区回流 R11.5：`input_rows=16 / already_in_pool=8 / keep_testing=8 / promote_candidate=0`，本轮不做 R12 写入。
- 探索社区编排入口已落地：pre 固定跑小配额 probe，post 固定生成社区审计和 R11.5 dry-run；正式出卡主链、V13 人审和发布快照链不变。
- 当前边界：`trend audit` 为 `watching`，`remaining_new_releases=5`，还不能写成 stable。

- 当前产品合同：`docs/reference/community-intelligence-clean-contract-2026-05-07.md`。
- 当前补充硬合同：`docs/superpowers/specs/2026-05-08-community-recommendation-interest-tag-contract-design.md`，用于锁定具像化兴趣标签、无业务硬编码、用户文案与内部证据分离。
- 旧社区发现 / 社区池治理链已归档：`docs/reference/community-discovery-legacy-archive-2026-05-08.md`。它只保留为历史审计、数据准备、Dev 写入追溯和 rollback 参考，不再作为当前推荐产品主链。
- 当前系统设计：`docs/superpowers/specs/2026-05-08-community-discovery-recommendation-system-design.md`。
- 当前后端架构：`docs/reference/community-recommendation-backend-architecture-2026-05-08.md`，固定 CLI / 后续 API / 前端适配层都调用同一个应用服务入口。
- 产品北极星仍是：`docs/reference/reddit-product-direction-2026-05-06.md`。
- `community_pool` 是干净社区总池，不是推荐结果页；进入 pool 只代表进入资产底座和学习范围。
- Hotpost / 小程序是用户端和新社区探测器；它能回流价值社区，但不能用“没有出卡”否定旧 DB 社区。
- 推荐层必须再看标签相关性、`15D` 活跃度、旧 DB 深度证据、Hotpost 证据、发现链证据；不活跃默认不推荐，但不删除。
- Phase 0 / 1 / 2 治理产物降级为数据准备和历史证据；不能再作为产品完成口径。
- 当前不做 UserTrack、Web/API、前端入口、开放搜索框、实时重抓或生产写库。
- 社区推荐合同修正版已落地：9 个用户可选业务标签和后台映射只放在 `backend/config/community_interest_tags.json`，代码只负责读取、校验、匹配和计算。
- 旧业务分类目录和 Phase 2 分类推断也已改成配置真相源：`backend/config/community_business_categories.json`，不再把分类 key / 别名 / 推断规则塞进 Python 常量。
- 离线标签式社区推荐预览已按补充硬合同重跑：用户可见区只展示具像化兴趣标签、社区、活动状态、推荐理由；内部证据只放在 Debug Evidence 区。
- 当前跑数已通过后端验收：`acceptance_passed=true / ready_count=29 / tags=9 / recommendations=69`；`电商平台政策与风向` 已从空状态修到 `ready / available_community_count=5`，品牌证据已进入推荐解释。
- 当前已补回归护栏：旧 `community_pool.categories` 不能单独构成推荐证据，必须有标签相关关键词或语义证据命中；`r/managers` 这类旧误分社区不会再出现在“家居生活选品”预览里。
- CI-R 验收链暴露出的历史类型债已清掉；本轮合同修正版目标 mypy 覆盖 `18` 个相关源文件通过。
- R7-R9 已落地：用户可见推荐理由已改成具体证据解释；新增 `reports/community-recommendation/audit.md` 和 `audit.json` 做标签-社区审核表；加载层已把 `content_labels / content_entities` 的标签和实体词并入语义证据密度。
- 后端应用服务边界已落地：`backend/app/services/community/community_recommendation_service.py` 统一生成 preview、audit 和验收摘要；CLI 已改为只调用 service，不再复制推荐计算；服务层只读，不持有 `SessionFactory`、不调用治理写库脚本、不 `commit`。
- 当前 `ready` 主要来自 Hotpost 近期探测 `hotpost_recent_probe`，不是 Dev `posts_hot` 自己恢复了完整 15D 新鲜数据；深层 `semantic_observation / semantic_terms` 仍需后续继续补密度，但已经不再只看 `community_pool_semantic_profile`。
- 预览产物：`reports/community-recommendation/preview.md`、`preview.json`、`audit.md` 和 `audit.json`。
- Hotpost 探索社区池结构已核实：`experimental_communities` 默认隔离，显式 `include_experimental=True` 才进入小配额 specs；审计合同仍是 `auto_promote=false / writes_db=false`。`ai-automation` 首轮显式 probe 已跑出真实候选证据：`r/CursorAI` 2 条、`r/windsurf` 1 条；其中 `cand-ai-automation-1t5ef8s` 已按 V13 validate 流程发布为 `card-cand-ai-automation-1t5ef8s-validate`，并同步到小程序快照 `release-0d88d54dd172`。`r/aider` 和 `r/openrouter` 仍是 `no_signal_yet`。
- 新增系统化桥接计划：`docs/superpowers/plans/2026-05-08-hotpost-community-pool-feedback-loop-plan.md`。
- R10/R11 已落地：显式 probe 命令为 `backend/scripts/hotpost/probe_community_discovery.py --scope ...`；日常采集默认仍不包含探索社区；回流 dry-run 只读、不写 DB、不自动入池。
- 2026-05-10 R11.5 回流 dry-run 已出现真实 `pool_candidate`：`input_rows=16 / already_in_pool=5 / keep_testing=8 / promote_candidate=3 / reject=0`。`r/aeo`、`r/ai_ugc_marketing`、`r/growthhacking` 进入候选；`r/etsy` 和 `r/digital_marketing` 已在 pool，只补证据。
- R12 预写入审计已生成：`reports/community-governance/community-pool-r12-prewrite-2026-05-10.md` 和 `.json`；结果为 `candidate_rows=3 / would_insert=3 / skipped_existing=0 / blocked=0`。
- 用户确认后，R12 已真实写入 Dev `community_pool`：`target_database=reddit_signal_scanner_dev / active_count_before=356 / active_count_after=359 / inserted=3`。新增社区为 `r/aeo`、`r/ai_ugc_marketing`、`r/growthhacking`；rollback 在 `reports/community-governance/community-pool-r12-dev-write-rollback-2026-05-10.sql`。Gold DB、小程序快照和 cloud DB 未写。
- `topic_cluster:funnel` 的用户标签映射已从只挂“卖家店铺运营”校准为配置驱动的多标签：广告投放、卖家店铺运营、内容营销创作；代码没有写社区名判断。
- Hotpost 社区探索回流 SOP 已固化：`docs/sop/2026-05-10-Hotpost社区探索回流SOP.md`。日常产卡 SOP 和评审发布 SOP 已补入口；以后必须同时汇报 probe、audit、R11.5、R12 预审和 DB 写入状态。

## 已落地事实：社区池治理与 Dev 写入

Reddit Community Intelligence 社区池治理已从 Phase 1 dry-run 推进到 Phase 2 Dev 写入：

- Phase 0 / 1 没有改 DB、API、前端、认证、用户轨迹、小程序或 Hotpost 日运营链；Phase 2 只写 Dev DB，Gold DB 未写。
- Phase 0 口径固定为社区池治理：`入池` 等于进入系统学习、采集、分析和证据积累范围，不等于高频采集、高权重或自动发布。
- 泛社区不排除，但后续必须设 cap；长尾社区是重点资产，按活跃度、帖子质量、垂直密度和可学习性判断。
- 新增治理规则文档：`docs/reference/community-governance-rules-2026-05-07.md`。
- 新增只读治理审计脚本：`backend/scripts/community/community_governance_audit.py`。
- live audit 当前输出：`promote_candidate=69 / keep_active=39 / needs_evidence=31 / stale_review=115 / observation_queue=10`。
- 审计报告在 `reports/community-governance/phase0-audit.md`。
- Phase 0.5 的 `promote_candidate` strong / medium / weak 人工表已降为历史证据；这些标签只表示证据密度，不再决定社区能不能进入治理主体。
- Phase 0 完整预审包已按社区池治理口径修正：入池等于进入系统学习范围，不等于高频采集或自动发布；泛社区可入池但要限额，长尾社区按活跃度、帖子质量、垂直密度和可学习性判断；完整预审在 `reports/community-governance/phase0-full-preaudit.md`。
- Phase 0 最终只读入池方案已生成：`reports/community-governance/phase0-community-pool-entry-plan.md`，确认社区资产总数 `264`，其中 `108` 个已有证据社区进入治理主体：`69` 个建议补入 pool、`39` 个保持在 pool。
- `108` 个已有证据社区已按角色收口：长尾垂直 `36`、泛社区 / 热点入口 `27`、AI 工具链 / 工作流 `27`、平台 / 卖家 / 增长操作 `17`、配置冲突待确认 `1`。
- `needs_evidence=31`、`stale_review=115` 和 `observation_queue=10` 不降级、不删除；下一步只补当前活跃度、帖子质量、业务归属和旧 DB 证据。
- Phase 1 口径已由用户确认：只做 dry-run 入池差异表、泛社区 cap、长尾活跃度 / 帖质字段，以及写库前验收；未人工确认前仍不写 DB。
- Phase 1 执行计划已写入：`docs/superpowers/plans/2026-05-07-community-pool-phase1-dry-run-plan.md`。
- Phase 1 dry-run 产物已生成：`reports/community-governance/phase1-dry-run.json` 和 `reports/community-governance/phase1-dry-run.md`。
- Phase 1 计数已验证：`existing_evidence_communities=108 / proposed_pool_additions=69 / keep_pool_unchanged=39 / needs_evidence=31 / stale_review=115 / observation_queue=10`。
- Phase 1 已补上泛社区 hot-floor 规则：泛社区默认只占 `25%` 常规学习预算，`30%` 以上需人工确认；但 must-have 热点信号必须覆盖，不受常规 cap 误伤，绕过原因固定为 `must_have_hot_signal`。
- Phase 1 dry-run 已由用户批准进入 Dev 写入；本轮仍没有改 Gold DB、API、前端、认证、用户轨迹、小程序或 Hotpost 日运营链。
- Phase 2 真实写库只打到 `reddit_signal_scanner_dev`，写入前后都经过 Dev/Test guard；Gold DB 未写。
- Phase 1 原始拟新增为 `69` 个；按 `community_pool` 真实约束 canonical 成小写后，发现 `13` 个已在 Dev pool，实际新增 `56` 个。
- Dev `community_pool` active count 从 `300` 到 `356`；新增行全部为 `tier=seed / priority=medium`，全部带 `description_keywords.source=community_pool_phase2_dev_write` 和 `display_name`，全部有 `community_category_map`。
- Phase 2 产物：`reports/community-governance/phase2-dev-write-result.json`、`reports/community-governance/phase2-dev-write.md`、`reports/community-governance/phase2-dev-write-rollback.sql`。
- 下一关不是继续盲目扩池；治理复查只作为库存校准，产品下一步以用户验收和进一步补强真实 Reddit 活跃探测 / 深层语义观察为主。
- 社区推荐后端已收口为“配置真相源 -> 只读加载 -> 领域计算 -> 应用服务 -> preview/audit 输出”的链路：
  - `backend/config/community_interest_tags.json`
  - `backend/config/community_business_categories.json`
  - `backend/app/services/community/community_recommendation_service.py`
  - `backend/app/services/community/community_recommendation_*` 小模块
  - `backend/scripts/community/community_recommendation_preview.py`
  - `backend/tests/services/community/test_community_recommendation_service.py`
- 当前跑数结果：生成 `9` 个具像化兴趣标签和 `69` 条推荐样例；验收摘要为 `acceptance_passed=true / ready_count=29 / db_writes=false / user_input_required=false`。

当前 Hotpost V13 LLM 路由已按最新要求改完：

- 正式生产 profile 仍是 `hotpost_v13_title_standalone`。
- V13 出卡链路现在是 `google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro`。
- `google/gemini-3-flash-preview` 负责语义理解层；`deepseek/deepseek-v4-pro` 负责中文写卡、title-only repair、breakdown 和 breakdown refresh。
- `fast_model` 现在是 `deepseek/deepseek-v4-flash`；`reasoning_model` 仍是 `deepseek/deepseek-v4-pro`。
- V13 semantic brief 已增强为主体、场景、证据 basis、张力、why_now、边界、写作焦点和禁写结论；同一份 brief 现在会继续传给 breakdown prompt。
- V13 semantic brief 现在进一步拆出 hot / signal / breakdown 的 lane-specific 判断位，`evidence_basis` 已结构化，`uncertainty` 已显式传给 writer/reasoning；shadow / review artifact 会保留 brief 供补卡前抽样审。
- hot 争议图仍走独立 `hot_controversy` 配置，不并入正文 V13 路由。

当前小程序上线准备新增状态：

- 授权登录流程已继续改成连续三步：微信授权登录 -> 绑定手机号 -> 补头像昵称 -> 进入目标页面。
- 主体变更后，手机号绑定入口已恢复到“我的”页：已登录未绑定用户显示“绑定手机号”，已绑定用户显示脱敏手机号。
- 前端入口复用既有 `bindPhone -> miniAuth.bindPhone -> phonenumber.getPhoneNumber` 链路，没有新增积分限制，也没有影响白名单详情免扣。
- 积分口径已按最新要求改为：新用户完成微信登录并绑定手机号后初始 `200`、每日签到 `30`、邀请新用户绑定奖励 `30`。
- 真机首次验证显示“手机号授权没成功”，后续诊断返回 `api scope is not declared in the privacy agreement`。已按微信官方文档把手机号按钮改成 `getPhoneNumber|agreePrivacyAuthorization`，让隐私同意和手机号授权走同一个按钮。
- 2026-05-02 用户真机复验已成功绑定手机号；手机号授权 / 隐私协议 / 前端按钮 / `miniAuth.bindPhone` 链路已打通。
- 邀请奖励已正式改名为“邀请新用户绑定奖励”：分享可以发生，但只有新用户通过邀请链接首次授权并绑定手机号后，邀请人才获得 `30` 积分。
- 后端奖励门槛已收紧：老用户互相分享不发奖；已注册或已绑定手机号用户不计入奖励；同一手机号如果已被其他用户绑定，也不会再次贡献邀请奖励。
- 前端文案已同步成同一口径：按钮为“邀请新用户获得30积分”，按钮下方说明“仅限新用户首次绑定手机号后获得积分奖励”，积分页提供“查看奖励规则 >”和 5 条奖励规则。
- 审计补齐了手机号空值硬校验：微信接口如果没有返回手机号，`miniAuth` 会抛 `PHONE_NUMBER_NOT_FOUND`，不会写入空手机号或误触发邀请奖励。
- 当前验证已过：小程序云函数 node 测试 `56 passed`，`git diff --check` 通过，`npm run build:weapp:prod` 通过。剩余上线前事项是部署 `miniAuth / miniPoints` 云函数、上传新版小程序，并做双账号真机邀请链路验证。
- 2026-05-03 线上数据资产保护 P0 已完成代码修复：`miniRelease.getCardDetail` 已改成服务端详情闸门，返回详情前会按 `OPENID` 查询用户、扣详情积分或识别免扣 / 已看过状态，并写详情访问日志；`miniRelease.listCards / getCardDetail` 已加按小时基础限速。后续又针对用户真机反馈的首页重进加载约 `5s` 做了首屏性能优化：`miniRelease.listCards` 已从“全量读取当前 release 再切第一页”改成按 `display_order` 只查首屏 `size + 1` 条，首页 sibling tab 预取改成主列表返回后再启动，避免冷启动并发放大。测试结果：`node --test cloudfunctions/tests/*.test.mjs` 为 `91 passed`，`npm run build:weapp:prod` 通过，`git diff --check` 通过。剩余上线动作是部署 `miniRelease` 云函数，并确保云数据库有 `mini_access_rate_limits / mini_access_events` 集合，以及 `mini_release_cards` 的 `release_id + display_order` 索引。

当前 `2026-05-01` Hotpost 补卡已按“众筹 / 选品 / 产品 / 礼物优先，少 AI，少 SEO/PPC”完成一轮：

- 本轮正式发布 `29` 张，全部为 `电商与卖家`，结构为 `hot 11 / signal 18 / breakdown 0`。
- 方向分布：`众筹 / 预售 / 产品启动 12`，`商品选品 / 家居 / 礼物 / 耐用品 17`，`AI 0`，`SEO / PPC 0`。
- 事后口径已纠偏：`GiftIdeas` / 送礼讨论只能算消费需求观察，不能再算严格跨境 SKU 选品；明天 SKU 选品默认先跑 `crossborder-sku-selection-7d`。
- 新 SKU 选品真相源顺序固定为：用户/爱好者社区发现需求 -> 卖家/平台社区验证利润、退货、变体、主图、价格和转化 -> 众筹/预售社区验证早期产品信任。
- 最新小程序快照已同步到 `release-e2fb5db69afa`，`card_count=565`。
- `snapshot / miniRelease / miniFavorites / cloud_db / 小程序 snapshot data` 检查通过；`hot controversy guard` 通过。
- 首页 front30 为 `hot 11 / signal 18 / breakdown 1`，本轮修掉了同日 hot/signal 新卡把 breakdown 挤出首屏的问题。
- 运营日志已更新到 `reports/ops-log/2026-05-01.md`。
- 当前 validate queue 只剩 `cand-ecommerce-sellers-1sxaiai / 1t0d021` 两个候选和 `1su9hhp` 一个宽泛草稿；本轮没有为了补量硬发。
- `trend audit` 最新为 `watching`，`remaining_new_releases=5`，不能表述成 stable。

当前 `2026-05-03` Hotpost 运营发卡结果：

- V13 运行时配置已生效：`fast_model=deepseek/deepseek-v4-flash`，`reasoning_model=deepseek/deepseek-v4-pro`，正式 profile 为 `hotpost_v13_title_standalone`，语义层走 `google/gemini-3-flash-preview`，writer / repair / breakdown 走 `deepseek/deepseek-v4-pro`。
- `generate_card_content()` 已确认在 production profile 下先生成 semantic brief，再把同一份 brief 传给正文 writer 和 breakdown prompt。
- 出卡前审计曾给出 no-collect freshness gate `fail`，所以本轮没有从旧 publish surface 硬挑，先跑新 `7d` fresh。
- 宽口径 `all-scope 7d` 长时间无输出且未生成计划文件，已终止；随后按 SKU 纠偏口径跑 `crossborder-sku-selection-7d`。
- `crossborder-sku-selection-7d` 新增 `11` 个候选，第一轮正式发布 `7` 张：`hot 1 / signal 6 / breakdown 0`，全部为 `电商与卖家`。
- 用户确认后，继续把 7D 深挖出的强 SKU 候选作为 2026-05-02 内容窗口补发，追加发布 `18` 张：`hot 10 / signal 8 / breakdown 0`，全部为 `电商与卖家`。
- 用户随后要求在当前口径上把 `AI 信息 x2 / SKU 信息 x2`，已追加发布 `28` 张：`AI 10 / SKU 18`，结构为 `hot 15 / signal 13 / breakdown 0`，SEO/PPC 仍为 `0`。
- 当日合计为 `53` 张：`hot 26 / signal 27 / breakdown 0`，类别为 `电商与卖家 43 / AI 与自动化 10 / 商业增长与运营 0`。
- 本轮发布重点是 SKU / 商品判断 / AI 核心价值信息，不再把 `GiftIdeas` 当默认 SKU 真相源；SEO/PPC 没有为了补量硬发。
- 最新发布真相源同步到小程序快照 `release-33033bf53e07`，`card_count=618`。
- `snapshot / miniRelease / miniFavorites / cloud_db / hot controversy guard / copy guard / 小程序 snapshot data` 检查通过。
- `signal_target_window_underfilled` 根因已修：`offline_publish_plan` 会用 72h 内 signal 替换最老 signal，不放宽 `signal=72h` 门槛；最新 no-collect gate 为 `decision=publish / publish_ready=true / actual_total=8`。
- AI/SKU x2 追加轮后 no-collect gate 为 `decision=publish / publish_ready=true / actual_total=6`，说明还有可审候选，不是停机清零。
- `trend audit` 仍为 `rebound`，`remaining_new_releases=5`，不能表述成 stable。

当前小程序首页体验与 V13 标题治理已完成一轮产品化修复：

- V13 标题规则已从“能生成标题”收紧到“首页能扫读”：默认不写 `r/xxxx`，控制 18-32 字，拦截“这帖火了 / 评论区在吵 / 有用户开始 / 开始先 / 不再先”等模板句式。
- 当前 `release-33033bf53e07` 的 mini snapshot、cloud_db 导入文件、miniRelease 和 miniFavorites 内置数据已批量打磨标题，`card_count=618`。
- 小程序首页 / 详情 / 收藏页标题样式已去掉特殊 serif，改成更小的 sans 字体；首页和详情收藏已乐观更新，收藏页取消收藏会立即移除卡片。
- 当前验证已过：后端 V13 title/prompt 测试 `20 passed`，生成链路测试 `85 passed`，小程序 node 测试 `14 passed`，`npm run check:mini-snapshot-data` 通过，`npm run build:weapp` 通过。
- 线上可见前还需要重新导入 `mini_release_cards.wechat-import.json`，并上传新版小程序包。

当前 `2026-04-30` Hotpost V13 回补节奏已改成逐日验收，不再把五天混算：

- Day1 已补全：`22` 张，按日目标验收为 `AI 6 / 增长 7 / 电商 9`。
- Day2 已补全：`18` 张，按日目标验收为 `AI 9 / 增长 4 / 电商 5`。
- Day3 已补全：`23` 张，按日目标验收为 `AI 5 / 增长 5 / 电商 13`；比原计划多 `1` 张 AI，是因为 LLM 记忆卡为强卡。
- Day4 已补全：`18` 张，按日目标验收为 `AI 4 / 增长 10 / 电商 4`；增长转化先补满，再补 AI / 电商。
- Day5 已补全：`18` 张，按日目标验收为 `AI 6 / 增长 7 / 电商 5`；其中第三方 SociaVault key 已启用，但宽口径 collect 仍被 Reddit 429 / 评论超时拖住，最终用已持久化候选池补齐，并补发 1 张 Figma Make 工具效率信号。
- 今日正式发布总数已到 `99` 张：`hot 46 / signal 50 / breakdown 3`，覆盖 `商业增长与运营 33 / AI 与自动化 30 / 电商与卖家 36`。
- 本轮只发 V13 可发布卡；截断 quote、证据污染、重复题、旧日期低增量草稿均未强发，上游异常也未切旧模型绕过。
- 最新小程序快照已同步到 `release-32d82b05dbcc`，`card_count=536`。
- `snapshot / cloud_db / miniRelease / miniFavorites / 小程序 snapshot data` 检查通过，运营日志已更新到 `reports/ops-log/2026-04-30.md`。
- 日常产卡 SOP 和评审发布 SOP 已补上多日回补三层验收、SociaVault 使用边界和“发够数量不等于 stable”的口径。
- 首页排序已继续收口：front30 现在是 `hot 15 / signal 14 / breakdown 1`，第 `5` 位出现 breakdown，三条 lane 都能在首页首屏露出。
- Day3 final no-collect gate 为 `actual_total=0 / yield_exhausted=true / publish_ready=false / items=[]`。
- Day5 final no-collect gate 已清零：`actual_total=0 / yield_exhausted=true / publish_ready=false / items=[]`；validate queue 当前 `0`。
- 已处理的阻断：增长宽口径补采集看似卡住，实际是多 query / 多 subreddit 串行且结束后才打印；本轮用窄 query + 单社区先验货，再持久化 / seed / review，补齐两张 `r/PPC` 增长卡。
- 当时 `trend audit` 为 `rebound`，后续 2026-05-01 快照已进入 `watching`，但仍不能表述成 stable。
- 下一步不继续盲跑宽口径 collect；发布面已经收口，只等新的 7d fresh 盘面或明确薄领域净新增。

当前 `2026-04-24` 日常出卡主线已经接回：

- Reddit timeout 时的 SociaVault 后备 API 已确认可用；这轮不是“没有后备”，而是两个链路没有正确等到 / 用到后备。
- 已修掉评论补采外层批超时：有 SociaVault 时，评论批处理不再用固定 `12s` 过早取消后备请求。
- 已修掉 `hot` 争议图生成绕开后备客户端的问题：发布前补争议图现在走 `CollectRedditClient`，Reddit timeout 后可进入 SociaVault assist / rescue。
- 今天已真实发布 `18` 张：`hot 3 / signal 10 / breakdown 5`，覆盖 `商业增长与运营 8 / AI 与自动化 7 / 电商与卖家 3`。
- 最新小程序快照已同步到 `release-6f282273ec9b`，`card_count=437`，snapshot / bundle / cloud_db 同步检查通过。
- 已清掉最后一个重复 Frugal 隐性成本 breakdown；复跑 no-collect gate 后 `actual_total=0 / yield_exhausted=true / publish_ready=false`。
- 继续推进后又跑了一轮 `all-scope 7d`：采集触发 `daily_collect + collect_named_topics`，SociaVault discover assist 命中 `2` 次；进入发布面的 `6` 个候选全部是重复、拼接不稳或弱证据，已串行打回。
- 最新复跑 gate 仍为 `actual_total=0 / yield_exhausted=true / publish_ready=false`，今天发卡数保持 `18`。
- 当时这轮发布侧可以停，但全天还不能说稳定收口：trend audit 仍是 `rebound`，`remaining_new_releases=5`。
- 下一步不应继续盲发；只在新 `7d` fresh 或明确薄领域补薄有净新增时再进 review / publish。

- 小程序授权后反复要求补头像昵称的问题已定位为流程 bug，并已完成源码修复：
  - 已补资料完整性判断，真实昵称 + 稳定头像地址才跳过补录
  - 已接入头像云上传，避免继续保存微信临时头像路径
  - 当前还缺微信开发者工具 / 真机二轮验收
- 小程序构建链已补防卡死入口：
  - `build:weapp / build:weapp:prod` 现在会识别已知 Taro `system-configuration` panic 并快速失败
  - `tsc --noEmit --skipLibCheck` 已通过
  - 后续已定位到 Taro build 默认执行 `@tarojs/plugin-doctor` 的 config check，doctor native binding 在当前 macOS sandbox 触发 `system-configuration` panic
  - 项目标准入口已改为 `taro build --type weapp --no-check`
  - `npm run build:weapp` 和 `npm run build:weapp:prod` 均已通过
  - PR #3 已合并：`https://github.com/namcodog/hotpost-mini-app/pull/3`
  - 小程序独立仓库当前 `main` 已同步到 `a14c85b`
- 小程序授权登录后点击卡片详情出现 `加载失败 re is not function` 的问题已完成源码修复：
  - 根因是详情页把“扣查看积分”的云函数底层异常当成详情加载失败
  - 后续已把三个白名单 id 免积分单独拆出，不再和积分异常兜底混在一起
  - 现在白名单通过 `free_detail_access` 明确跳过扣积分；非白名单如果积分系统异常，不再被默认放行
  - 最新截图里的 `Re(a.card_id) is undefined` 已继续定位为详情页加载期 helper 初始化顺序问题，并已把 `prepareSharePaths / prepareInviteShare` 提前成函数声明
  - READ 03 的「查看原帖链接」已改成先尝试复制并始终展开原帖链接；如果微信剪贴板拦截，页面仍会显示原帖链接让用户手动复制
  - 当前已确认旧实现自身有问题：复制失败时不展示链接，且 toast 失败也会被误报成复制失败
  - 因 Taro 沙箱构建仍有已知 panic，当前已用非沙箱构建重新同步 `dist-dev / dist-prod`
  - 当前还缺微信开发者工具 / 真机完整链路复验
- 小程序独立 GitHub 仓库当前主线已更新到：
  - `main@a65da7f`
  - PR #1：授权、详情、READ 03、构建防卡死等代码修复已合并
  - PR #2：快照数据一致性检查已合并
  - `miniRelease / miniFavorites` 的 manifest 现在只指向实际存在的 `release-6f282273ec9b`
  - 后续快照提交前需要先跑 `npm run check:mini-snapshot-data`
- 小程序功能验收已经收口：
  - 用户已确认当前功能都正常
  - 授权登录、头像保存、首页点卡片、详情查看、READ 03 原帖链接不再作为 P0 待验收项保留

当前主线已经重新收口回 `hotpost` 出卡，不再把“小程序验收”当成当前主任务。

- 当前进度提醒：
  - 当前接手主线是 `hotpost` 日常出卡与发布链稳定性
  - 小程序详情页 / READ 03 已由用户确认功能正常，不再是当前阻断
  - 不把当前进度表述成“大工作区所有方向一起推进”

- 小程序补充面口径已经纠偏回正确状态：
  - `supplement surface` 继续只作为后台分桶存在
  - 前端不再新增 `15天补充` tab
  - 本地 `422` 的根因已坐实：前端错误请求了 `card_type=supplement`
  - 现在本地和云函数都改成：补充卡继续由 `surface_bucket` 承接，但在原来的列表里按 `lane / card_type` 展示
  - 当前验证结果：
    - `tests/api/test_hotpost_clues.py`：`11 passed`
    - `cloudfunctions/tests/mini-release.test.mjs`：`4 passed`
    - `npm run build:weapp`：通过
    - `npm run build:weapp:prod`：通过
  - 当前根项目配置已恢复到：
    - `project.config.json -> dist-dev/`
    - `project.private.config.json -> dist-dev/`

- 补充面已经收回后台分桶，没有改主 freshness 硬规则：
  - `supplement surface` 仍存在，但只作为后台 `surface_bucket`
  - 前端不再新增 `15天补充` 标签页
  - 超出主 freshness 窗口但仍有价值的卡，继续通过补充面进入发布快照，再并回原来的列表
  - `trend audit` 现在也只看主面，不再因为补充库存增厚就误报 `rebound`

- “审计结论”这轮已经从报告落成实现，不再只是口头判断：
  - `named-topic` 的 topic registry / preset / 默认 preset 已从 Python 常量抽到 YAML：
    - [hotpost_named_topic_watchlists.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_named_topic_watchlists.yaml)
  - 现在默认 named-topic 策略不再写死在代码里：
    - `collect_named_topics.py` 默认 preset 改成读配置
    - `run_intake_freshness_gate.py` 主链里的 named-topic collect 默认 preset 也改成读配置
    - `topic_metadata` 不再只认 `daily-watchlist`，而是认配置里的全部 named topics
  - `freshness gate` 里旧的窗口硬编码也继续收掉了：
    - lane target 不再写死 `15 -> 9/4/2`
    - 现在改成按 rolling mix 配置缩放
    - `recommended_actions` 里的 `run_offline_publish_plan --limit 15` 也改成跟运行时 target total 走
  - 当前 `runs_per_day` 配置已经和正式口径重新对齐：
    - `global_rules.operation_defaults.runs_per_day = 3`
  - 这轮的结果不是“完全没有硬编码”，而是关键的默认策略硬编码已经被拔掉；当前剩下的运营纪律主要在 SOP，而不是埋在执行代码里

- “补上线卡”的硬规则与配置边界已经重新审计并结构化：
  - 新增补卡合同：
    - [hotpost-card-supplement-contract.md](/Users/hujia/Desktop/RedditSignalScanner/docs/reference/hotpost-card-supplement-contract.md)
  - 当前正式口径已经锁定为：
    - 硬规则不动
    - 补卡只改 collect 输入层
    - 长尾新社区属于结果层价值，不是 gate 豁免
  - 当前补卡 profile 已扩成四档：
    - `selection-30d-core`
    - `selection-30d-home-decisions`
    - `selection-30d-small-goods-demand`
    - `selection-30d-small-goods-tail`
  - 最新又补成了“压 EDC、补非 EDC”的六档：
    - `selection-30d-small-goods-broad`
    - `selection-30d-brand-opinion`
  - 当前明确的新口径是：
    - `EDC` 仍保留，但不再默认吃满小商品补卡面
    - `pet / outdoor / home / gifts / brand / crowdfunding` 现在都有独立 `30d` profile 可切
    - 品牌舆论与众筹预售属于“补卡入口扩展”，不是改 gate
  - 当前 profile loader 已增加前置校验：
    - `scope_id`
    - `topic_pack_id`
    - `topic_cluster_ids`
    - `time_filter`
  - 这次审计坐实的主风险不是“代码偷偷改了硬规则”，而是：
    - phase-log 口径一度还停在旧的两档 profile
    - 补卡合同之前没有单独写清，容易让人把“扩检索”误解成“改规则”

- `AI / LLM / Agent / Harness` 的 `7d` 补卡入口也已经按同一条边界落下来了：
  - 当前只新增了一个配置入口：
    - `ai-7d-llm-agent`
  - 这轮没有动 gate、没有动发布合同、也没有回头改主链，只改了补卡 profile
  - 按 `week` 跑完后已真实发布 `4` 张 AI 卡：
    - `1sk7e2k`：Claude Code 100 小时 vs Codex
    - `1so9uta`：Opus 3.7 退化
    - `1sjqxat`：Anthropic 封禁 OpenClaw 作者
    - `1sm2bft`：Agent 可观测性 / Harness
  - 当前正式 release 已到：
    - `hotpost release latest = release-b3e8c4f83030`（`294` 张）
    - `mini snapshot latest = release-d514a1867cd1`（`62` 张）
  - `Hermes` 这轮 `7d` 没跑出足够硬的直连信号；当前已经给了配置入口，但没有为了补量硬发

- 小程序双轨当前已重新确认，不会再混回旧世界：
  - 本地开发工具当前应看 `dist-dev/`
  - 手机预览 / 真机当前应看 `dist-prod/ + cloud db`
  - 这轮已重新执行：
    - `npm run build:weapp`
    - `npm run build:weapp:prod`
  - 当前根项目 `miniprogramRoot` 已恢复到 `dist-dev/`，开发态继续直连本地 `127.0.0.1:8006`
  - 当前云端内容已更新到 `release-2aa8efc6b16c`，`check_mini_release_sync.py` 通过
  - 这轮也确认了一条新边界：
    - 内容同步靠 `push_mini_snapshot.py`
    - 本地调试看 `dist-dev`
    - 手机预览这轮只需要重新部署 `miniRelease` 云函数，并用 `dist-prod` 重新预览

- `ai-7d-llm-agent` 这轮已经继续补到底，不再停在前一轮 4 张：
  - 当前继续新增发布 `6` 张 AI 卡：
    - `1sjlesb`：Claude Pro 额度打断长会话，工作流转向“拆任务 + 回灌上下文”
    - `1sljk0t`：Claude Code 桌面版 UI，用户在“官方原生端”和“继续待在 VS Code”之间摇摆
    - `1skreyb`：Qwen3.5 配工具后不再过度思考
    - `1sn8bnq`：Agent 记忆从 Markdown 转向数据库
    - `1smd9sz`：顺着模型“语义引力”去设计最终答案
    - `1snaa5w`：Qwen 3.6 在 3090 上跑 262k 上下文
  - 当前已明确打回一批不该硬发的弱货：
    - `1skwi3m`：退款吐槽
    - `1sm374u`：draft 被带偏到 PDF 处理
    - `1spfz31`：假 Hermes 命中
    - `1sjtyq5 / 1slvy0o`：低信息密度
  - 当前这条线在小程序里的可见结果已经更新为：
    - 主面 `4` 张
    - `15天补充` 里 `6` 张
    - 最新 snapshot `release-2aa8efc6b16c`
  - 这轮也坐实了边界：
    - `Hermes` 现在仍然没有真高密度直连信号
    - 之前超出主 freshness 的 `6` 张，现在不是硬塞回主面，而是通过独立补充面给用户看
  - 所以这轮 `7d` AI 配置当前可以视为已榨干；如果还要继续补，只能等新的 `7d` fresh，或者明确切更长时间窗/更窄主题

- `small-goods` 的 `30d supplement profile` 已按“只改配置、不改规则”真正跑完一轮：
  - `selection-30d-small-goods-demand / tail` 已重新收紧：
    - 去掉会放大 listing 噪音的 `homeowners / ApartmentHacks / onebag`
    - `tail` 的 `candidate_cap` 从 `4` 收到 `3`
    - `tail` 明确退回“长尾探索配角”，不再和主补卡面抢位子
  - 最新又继续把 `EDC` 权重再压一档：
    - `small-goods-demand` 里的 `EDC candidate_cap` 已从 `4` 降到 `2`
    - `small-goods-tail` 里的 `EDC candidate_cap` 已从 `3` 降到 `2`
    - 同时新增两档 `30d` 补卡入口：
      - `selection-30d-small-goods-broad`
      - `selection-30d-brand-opinion`
  - 新配置重跑后：
    - `demand candidate_count = 20`
    - `tail candidate_count = 12`
  - 已真实补发 `3` 张 `small-goods` 卡：
    - `card-cand-ecommerce-sellers-1se4i3o-validate`：玻璃保鲜盒平替
    - `card-cand-ecommerce-sellers-1scp4vn-validate`：多功能清洁粉末和旧工具
    - `card-cand-ecommerce-sellers-1rzx6t5-validate`：差旅非包类小物 / 一根 USB-C 走天下
  - 当前最新发布真相源：
    - `hotpost release latest = release-f772e56df334`
    - `mini snapshot latest = release-be57ce64ac15`
  - 这轮说明：`small-goods` 现在不是只能“出候选”，已经能在不改硬规则的前提下，真实补到线上

- `30d` 选品补卡已经继续去 `EDC` 化，而且不是只停在配置层：
  - `small-goods-demand` 的 `EDC cap` 已从 `4` 降到 `2`
  - `small-goods-tail` 的 `EDC cap` 已从 `3` 降到 `2`
  - 新增两档独立 profile：
    - `selection-30d-small-goods-broad`
    - `selection-30d-brand-opinion`
  - `no-persist` 试跑结果：
    - `broad = 16`
    - `brand = 8`
  - 当前已真实发布 `5` 张相关新卡：
    - `1sc32lq`：平替不是终身耐用，买的是保修与极端场景稳定性
    - `1sm5wkz`：弹力牛仔裤的舒适，正在变成耐用性陷阱
    - `1rzb3rq`：清洁用品从专品堆，转向几种便宜基础货轮换
    - `1s4qkly`：宠物家庭在“单机戴森”与“吸拖全家桶”之间摇摆
    - `1so22u3`：清宠物毛先看粘和搓，不再先问吸力参数
  - 当前小程序快照已更新到：
    - `release-b06569bffde5`
    - `card_count = 74`
    - `main_card_count = 62`
    - `supplement_card_count = 12`
  - 当前已确认进入小程序可见面的有：
    - 主面：`1so22u3`
    - `15天补充`：`1sm5wkz`
  - 另外 3 张没有进当前小程序前台，不是同步坏了，而是原帖时间超出 `15天补充` 窗口

- `30d` 去 EDC 化补卡这轮又继续往前推了一段，不再只停在第一波：
  - 新增真实发布 `3` 张：
    - `1sixo6a`：宠物主买吸尘器，先问电池能不能自己换
    - `1soc5l5`：Durston X-Dome 是真需求，还是网红带货带偏
    - `1slqcxb`：内裤这种消耗品，到底值不值追“终身耐用”
  - 当前这轮相关补卡累计已到 `8` 张
  - 当前正式发布真相源：
    - `release-076ec8e94fd8`
    - `published_count = 308`
  - 当前小程序快照已更新到：
    - `release-2f225c36ef5f`
    - `card_count = 75`
    - `main_card_count = 63`
    - `supplement_card_count = 12`
  - 当前已确认进入小程序可见面的累计变成 `5` 张：
    - 主面：`1so22u3`、`1soc5l5`
    - `15天补充`：`1sm5wkz`、`1sixo6a`、`1slqcxb`
  - 当前还没被证实能继续出货的薄方向，仍然是：
    - `gift`
    - `crowdfunding`
    - 偏噪的 `home odor`

- `gift` 线已经从“弱项”变成“当前前台能看到的一条小面”，而且没有改底层规则：
  - 新增独立 profile：
    - `selection-30d-gift-crossborder`
    - `selection-30d-gift-emotional-value`
  - 当前 gift 线真实补发 `7` 张：
    - `1se1gc0`：送礼先看地域独有性，不再先纠结价格或通用性
    - `1spqj1u`：送礼先看日常实用性，不再先追求贵重或新奇
    - `1smulbv`：送礼先挑能救急的小实用物，不再先想好看摆设
    - `1s36awc`：给咖啡爱好者送礼，现在先看配件升级，不再先想新机器
    - `1sejtkv`：送礼开始先升级对方天天在用的东西，不再先买陌生新玩具
    - `1s4dp64`：情绪价值礼物开始具体化成靴子、咖啡机、香水和护理工具
    - `1s37jfw`：情绪价值礼物开始具体化成 `weighted blanket` 这类 comfort 商品
  - 当前这轮去 EDC 化相关补卡累计已到 `15` 张
  - 当前正式发布真相源：
    - `release-205b5e196ddc`
    - `published_count = 315`
  - 当前小程序快照已更新到：
    - `release-335f526281dd`
    - `card_count = 76`
    - `main_card_count = 64`
    - `supplement_card_count = 12`
  - gift 当前在小程序可见面的结果是：
    - 主面：`1spqj1u`、`1smulbv`
    - `15天补充`：`1se1gc0`、`1sejtkv`
  - 当前更清楚的边界是：
    - `GiftIdeas` 现在已经能补出“地域独有 / 日常实用 / 应急小物 / 升级型礼物 / comfort 商品”这几类
    - “情绪价值商品”这条线已经能出正式卡，但更容易被关系建议和手作情绪贴污染
    - `1sejtkv` 已经进入 `15天补充`
    - `1s4dp64 / 1s37jfw` 虽然是更具体的商品卡，但还没进当前前台 gift 面
    - `1s36awc` 这种“升级型礼物”能进正式资产，但因超出 `15天补充`，不进当前前台
    - `1sliyon` 被判成 `hot` 后缺争议图，当前不能为了补量手改 lane
    - 还没稳定打穿“品牌礼盒 / 厨房小物 / 节日伴手礼”这些更窄子方向

- 按新的 `30d supplement profile` 又补出一轮真正上线的选品卡，不再停在“入口可配”：
  - 本轮按 `selection-30d-core` 新增发布 `3` 张：
    - `card-cand-ecommerce-sellers-1ryygmo-validate`：买空压机先看能不能自己修
    - `card-cand-ecommerce-sellers-1s5oofq-validate`：买冰箱要算维护与耗材总账
    - `card-cand-ecommerce-sellers-1sa9l80-validate`：EDC 手电开始为十年耐用和 UI 逻辑付溢价
  - 当前 `selection-signals` 已到 `61` 张
  - 当前 `hotpost release latest = release-511af28a137d`
  - 小程序同步快照已更新到 `release-d9727a712016`
  - 当前更清楚的边界是：`selection-30d-core` 确实能继续补，但不是每条都值得发；`dogs` 里的宠物吸尘器目前更像品牌投票，还没家电/工具/EDC 这几条硬

- “补上线卡”和“每天运营节奏”已经明确拆开，不再混成一条主链：
  - 当前已经新增独立的补卡配置入口
  - `collect_named_topics.py` 现在支持：
    - `--watch-profile`
    - `--watch-profile-config`
    - `--topic-cluster`
  - 当前补卡配置文件是：
    - [hotpost_card_supplement_profiles.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_card_supplement_profiles.yaml:1)
  - 当前内置四个 profile：
    - `selection-30d-core`
    - `selection-30d-home-decisions`
    - `selection-30d-small-goods-demand`
    - `selection-30d-small-goods-tail`
  - 这意味着后面再补 `30d` 选品/采购决策卡，默认先改 YAML 或切 profile，不再频繁改 Python 主链

- Reddit 选品挖掘窗口已经从近 `7d` 真正扩到 `30d`，不是停留在口头建议：
  - `named-topic/custom watch` 主链现在已支持 `month`
  - `collect_named_topics.py` 已能直接收 `--time-filter month`
  - 本轮 `30d` 挖掘后新增发布 `2` 张选品/采购决策卡：
    - `card-cand-ecommerce-sellers-1s2vqb9-validate`：旅行枕先看内部支撑结构，不再先看品牌或填充物
    - `card-cand-ecommerce-sellers-1skepok-validate`：新房升级先别在开发商那儿加钱，先找外部承包商
  - 当前 `hotpost release latest = release-b92d867b96f8`
  - 小程序同步快照已更新到 `release-fabc8cf142e4`
  - 当前新边界也更清楚了：`30d` 的确能把池子拉厚，但 `homeowners` 这类宽泛社区会显著放大误命中；这轮真正干净的增量主要还是来自 `BuyItForLife / flashlight`

- 近 `7d` 的 fresh 选品挖掘已经跑出第二轮结果，不再只靠历史补卡：
  - 新增发布 `2` 张 fresh 选品卡：
    - `sig-1sji2uz`：社区 4000+ 咖啡配置数据拆解，指向“机器 vs 磨豆机”的预算判断
    - `sig-1so2bpp`：狗车载出行从航空箱转向安全带胸背
  - 当前 `hotpost release latest = release-d674f902fd79`
  - 小程序同步快照已更新到 `release-c8ab947acd95`
  - 已串行打回噪音候选 `cand-ecommerce-sellers-1soqzy5`
  - 当前代码侧又确认了一条新边界：queue 默认会吞掉有用的 fresh selection 候选，必要时需要 `review_cards.py seed --live` 直接从候选池拉进 review

- “选品 / 好物推荐”这条线刚补了一轮，不再是几乎看不见：
  - 新增发布 `3` 张偏选品卡：
    - `sig-1sl84dz`：详细清单型选品
    - `sig-1so1ohw`：平替与单价型选品
    - `sig-1snq6nb`：批次缩水风险
  - 当前 `hotpost release latest = release-2cbdbf6ae58a`
  - 小程序同步快照已更新到 `release-08c588667271`
  - 这轮补的是“选品判断信号”，不是单纯多发生活方式晒图；其中 `1snq6nb` 属于版本/批次风险，不算纯好物推荐

- `2026-04-14 ~ 2026-04-18` 的历史补卡首轮已经收口，不再停留在“要不要补”的判断阶段：
  - 已从历史 `review_queue snapshot` 补发 `5` 张真漏卡：
    - `sig-1snhyck`
    - `sig-1so5ozi`
    - `sig-1slqavn`
    - `sig-1sljggu`
    - `sig-1slqxss`
  - 当前 `hotpost release latest = release-b84077c4458f`
  - 小程序同步快照已更新到 `release-b132b3a180a4`
  - 这 `5` 张属于历史漏卡补发，不等于今天 fresh `all-scope` 结果恢复成健康强日
  - 当前剩余历史候选大多是噪音、撞题或信息密度不够；其中 `cand-ai-automation-1sm30ry` 已按 `duplicate_story_after_publish` 打回，不再重复发

- 今天这轮日常运营已经正式跑到停机，不再是“还在进行中”：
  - `scope = all-scope`
  - `collect_stopped_by = yield_exhaustion`
  - `dry_cycles = 3`
  - `gate_decision = publish`
  - `actual_total = 0`
  - `publish_ready = false`
- 今天 fresh `all-scope` 日运营累计真实发布 `7` 张；再加上历史补卡 `5` 张后，当前 `hotpost release latest = release-b84077c4458f`，小程序同步快照为 `release-b132b3a180a4`，`mini snapshot / cloud_db / miniRelease / miniFavorites` 继续全绿，`trend` 仍是 `stable`。
- 结果层定性不能和停机条件混说：
  - 流程层：今天已经满足正式停机条件
  - 结果层：今天仍是 `低供给日`，不是健康强日；最终补货主要还是 AI，`small-goods / funnel-conversion / category-winds` 没有稳定站住
- 这轮还坐实了一个运营层细节：
  - 并行 `reject` 会互相覆盖 `backend/data/hotpost/review_rejections.json`
  - 当前人工串行流程不受影响，但后续如果要自动化 reject，必须先补锁或避免并发写

- 今天的日常运营已经正式启动，不再停留在 preflight。当前已真实发布 `4` 张，并把发布后的 `mini snapshot / cloud_db / miniRelease / miniFavorites` 同步到 `release-8ebc53547c77`。
- 这轮运营里又修掉了两个真实阻断：
  - `review_cards seed` 遇到坏 JSON 会直接失败；现在已增加 JSON 修复通道
  - `signal validate` 生成后 `min_test_action` 为空，导致发布必挡；现在已重新接回生成链
- 当前最新盘面再次确认：还不能停机。发布后重算仍是：
  - `gate_decision = publish`
  - `actual_total = 7`
  - `publish_ready = true`
  - 当前还没有 `collect_stopped_by = yield_exhaustion` 的停机证据
- 当前结果定性也要拆开看：
  - 流程层：今天已经真实进入运营轮，并且第一轮发卡成功
  - 结果层：盘面还没跑到健康强日；`small-goods` 暂时又回空白，`funnel-conversion` 只补出 `1` 张，仍然需要继续补薄

- `hotpost` 出卡的系统性主阻断已经打穿；当前不再有 priority cluster 空白，不再是全局结构性卡死。
- 当前已经完成两段主修复：
  - recall：同 pack 内 priority cluster 已改成交错分配，且同帖撞多个 cluster 时会保留合并后的 cluster 元数据
  - evidence：candidate 层已前移 `group-*` 强证据候选，且 `backfill` 后新增了一次 shortlist enrich，不再让后捞上来的候选永远停在 `0 quote`
- 当前最新真实验证：
  - `ecommerce-sellers` 已出现 `2` 条 `small-goods` raw candidate + `1` 条 `group-*` 候选
  - 三条 `small-goods` 候选当前 quote 分别为 `5 / 5 / 4`
  - `build_offline_publish_plan(scope='ecommerce-sellers')` 当前：
    - `candidate_count = 15`
    - `candidate_publish_surface_count = 4`
    - `blank_priority_clusters = ['key-people-and-route', 'ai-product-and-adoption', 'platform-policy-shifts']`
  - `build_offline_publish_plan(scope=null)` 当前：
    - `candidate_count = 27`
    - `candidate_publish_surface_count = 10`
    - `blank_priority_clusters = []`
    - 全局 `publish_list` 已出现 `1` 条 `small-goods`
- 当前重点 cluster 现状：
  - `key-people-and-route = 1`
  - `ai-product-and-adoption = 3`
  - `platform-policy-shifts = 1`
  - `small-goods` 已脱离 `0`
- 现在剩下没解的，不再是主链，而是：
  - `funnel-conversion` 仍薄
  - 以及历史 rejection 对个别旧 `candidate_id` 的持续隐藏

当前主问题已经不是规则不清、也不是脏 draft 继续占名额。

- 小程序范围内刚重新核过：`miniRelease store` 测试通过、`build:weapp:prod` 通过、本地 `miniRelease / miniFavorites` 都已指向 `release-3fdc73c6a229`，且 `hot validate` 卡本地无缺争议图。
- 所以当前小程序这条线的主风险更像“产品态偏离基线 / 真机展示仍待验收”，不是同步链或构建链已经坏掉。
- 首页卡片收藏入口已经重新接回，避免“首页没有收藏动作，但收藏页仍让用户回首页点收藏”的路径断裂。

- `draft-cand-business-growth-ops-1sokcov-validate` 仍存在，但已经被识别为 `detail_fields_incomplete`，且不再算 ready draft / queue blocker
- 当前真正的主问题重新收口成：`供给薄`
- 现在薄，不是因为 API 不够，也不是因为题材树不清楚，而是：
  - 当前候选池本身只剩 `11` 条
  - 四个重点 cluster 现在都是 `0`
  - publish surface 主阻断原因集中在：
    - `single_thread_weak_evidence`
    - `single_community_weak_evidence`
    - `exploration_requires_two_quotes`
    - `low_information_density`
- 当前已经代码级确认：这不只是“门槛偏高”，而是 `recall 偏窄 + evidence formation 偏弱` 同时收缩：
  - 当前更准确的 recall 问题不是“所有重点 pack 的 query 都太少”，而是 spec 展开后仍会被 pack 共享 quota 与 subreddit cap 压偏：
    - `upstream-winds = 108 specs / quota 3`
    - `tools-efficiency = 96 specs / quota 4`
    - `category-winds = 48 specs / quota 3`
    - `funnel-conversion = 12 specs / quota 4`
  - raw candidate 在生成阶段就固定 `thread_count = 1`、`community_count = 1`，且 `evidence_quotes` 只保留前 `2` 条
  - 这意味着 strong tier raw candidate 默认会被单线程 / 单社区挡掉；如果后面 grouped draft 形成不出来，强证据档供给会天然变薄
- 当前四个重点 cluster 里还要分开看：
  - `key-people-and-route / platform-policy-shifts / ai-product-and-adoption` 更像“有 spec，但在 pack 内竞争里被吞掉”
  - `small-goods` 当前更像“spec 很多但真实命中弱/噪声高”，不能继续和其他 cluster 混为同一种问题
- 所以下一轮要聊透、也要继续验证的，不是再改规则，而是：
  - 检索入口是不是太窄
  - 薄 pack / 新节点是不是经常命中后又被证据强度挡掉
  - LLM 为什么没有真正把 recall 拉起来

## 当前进度

当前已经把 `publish-surface-gate-tiering-v1` 的 winner `contract_tiered_surface_v3` 回灌进项目侧默认 publish surface gate：

- 保留硬垃圾过滤层，不放松：
  - 玩笑帖
  - 无有效 quote
  - 纯客服 / 弱客服
  - why_now 不清楚
  - 信息密度不足
  - 明显 stale
- 新增分层 gate：
  - 强证据档继续要求更强的多线程 / 多社区证据
  - 探索档只对薄 pack / 新节点开放，允许单线程 / 单社区，但至少要 `2` 个可用 quote，且 why_now 清楚、信息密度够、不穿透硬垃圾过滤层
- 当前优先薄 pack / 新节点已固化到 gate 分层语义：
  - `upstream-winds`
  - `tools-efficiency`
  - `funnel-conversion`
  - `category-winds`
  - `key-people-and-route`
  - `ai-product-and-adoption`
  - `platform-policy-shifts`
  - `small-goods`
- 当前默认盘面验证已跑过：
  - `scope = null`（默认 `all-scope`）
  - `latest_status = stable`
  - watch 项仍在阈值内：
    - `FacebookAds = 5`
    - `PPC = 5`
    - `BuyItForLife = 5`
    - `paid-economics = 14`
- 当前离线计划结果说明：
  - 回灌已吃进默认发布链
  - 但当前这一轮真实盘面 `candidate_publish_surface_count = 0`
  - 说明这次已经把“薄题材如何更早进发布面”的规则落进去了，但后面仍要用后续 `5` 个新 release 验证它能不能持续把真实可发布数做厚，而不是只停留在合同层

当前又把“字段不完整前移”这条明显尾项收掉了，不再让脏 draft 继续占 gate 名额：

- 新增了 `draft_surface_readiness.py`
- `offline_publish_plan` 现在只会把 `surface_ready_drafts` 当成已占坑 draft
- `review_queue_policy` 现在只会把字段完整的 draft 当成已存在 blocker
- `review_card_ops` 现在会用完整 draft 替换同 `draft_id` 的脏 draft，不再让旧脏 draft 长期卡住候选
- 当前工作区里那张脏 draft 已被真实识别成：
  - `draft-cand-business-growth-ops-1sokcov-validate`
  - `detail_fields_incomplete`
  - 并且它已经不再算 `ready_validate_drafts`
- 这次离线验证结果已经确认：
  - `draft_count = 1`
  - `ready_validate_drafts = 0`
  - `ready_write_drafts = 0`
  - 说明字段不完整这层已经从 draft/review 继续前移到了 publish surface 编排阶段

今天这次已经按正式日节奏完整跑完 `3` 轮，不再是“一轮 exhausted 就收工”：

- 第 1 轮基础轮：`all-scope` gate 放行 `2` 张，实际发布 `1` 张：
  - `card-cand-ai-automation-1sogbxg-validate`
  - 另一张 growth signal draft 因 `detail.min_test_action` 缺失被挡
- 第 2 轮定向补薄轮：补出 `3` 张可进发布面的候选，但 final gate 因 `stale_ratio_out_of_control` 全挡，实际发布 `0` 张
- 第 3 轮停机确认轮：再次跑标准链后，最终确认：
  - `scope = null`（默认 `all-scope`）
  - `yield_exhausted = true`
  - `actual_total = 0`
  - `publish_ready = false`
- 最新 release 已更新到：
  - `release-3fdc73c6a229`
  - `card_count = 63`
- 当前稳定态继续守住：
  - `latest_status = stable`
  - `stable_streak = 11`
  - watch 项仍在阈值内：
    - `FacebookAds = 5`
    - `PPC = 5`
    - `BuyItForLife = 5`
    - `paid-economics = 14`
- 这次还补掉了 collect 长时间等待的真实问题：
  - 根因落在评论 enrichment 的批等待链
  - 现在 comment 批次已改成有界等待；超时任务会被取消并按空评论收口，不再把整轮 collect 无限拖住
- 对今天这轮最准确的定性是：
  - 这是 `异常低供给日`
  - 根因不是规则、展示层或稳定性，而是：
    - 一张 gate 放行卡因 draft 字段不完整被挡
    - 定向补薄长出了候选，但 freshness 不够新
    - 所以最终真正能发的卡仍太少

当前已经把两个之前没真正打通的空白 cluster 推进到真实 release：

- 先用最小定向 named-topic collect 补这两个 cluster 的候选：
  - `key-people-and-route`
  - `platform-policy-shifts`
- 再用 grouped validate draft 补足多线程 / 多社区证据，最终新增发布 2 张 AI 卡：
  - `card-group-ai-automation-50e98bcedd`
  - `card-group-ai-automation-e429d17909`
- 最新 release 已更新到：
  - `release-4127f8731851`
  - `card_count = 62`
- 最新 release 的重点 cluster 状态现在是：
  - `key-people-and-route = 1`
  - `platform-policy-shifts = 1`
  - `ai-product-and-adoption = 1`
  - `small-goods = 1`
- 稳定态继续守住：
  - `latest_status = stable`
  - `stable_streak = 10`
  - watch 项仍在阈值内：
    - `FacebookAds = 5`
    - `PPC = 5`
    - `BuyItForLife = 5`
    - `paid-economics = 14`
- 这轮正式停机字段也已经补齐：
  - `scope = null`（默认 `all-scope`）
  - `yield_exhausted = true`
  - `final decision = publish`
  - `actual_total = 0`
  - `publish_ready = false`
- 当前可以更准确地说：
  - `key-people-and-route / platform-policy-shifts` 已开始打通
  - 但还不能说“这两个 cluster 已经稳定补厚”

当前已经把“统一口径”继续压成默认计划输出，不再只靠对话解释：

- `offline_publish_plan` 现在会默认带出 `publish_contract_summary`
- 这份摘要固定回答 4 件事：
  - 最终想达到什么
  - 当前已经达到什么
  - 现在还没达到什么
  - 当前最优先补什么
- 当前最新真实 plan 输出里，这份摘要已经能直接给出：
  - `latest_status = stable`
  - `stable_streak = 6`
  - watched 社区 / pack 当前都压在阈值边上：
    - `FacebookAds = 5`
    - `PPC = 5`
    - `BuyItForLife = 5`
    - `paid-economics = 14`
  - 当前薄 pack 已开始冒头，但还不能说“已稳定补厚”：
    - `upstream-winds = 4`
    - `tools-efficiency = 2`
    - `funnel-conversion = 3`
    - `category-winds = 1`
  - 当前空白 cluster 也还没完全补起来：
    - `ai-product-and-adoption = 1`
    - `small-goods = 1`
    - `key-people-and-route = 0`
    - `platform-policy-shifts = 0`
  - 当前主焦点明确收口成：
    - `thicken_supply_without_breaking_stable`

当前已经把“供给厚度和证据强度前移”真正压进发布面，不再等到 review 才大面积挡弱货：

- 新增了 publish-surface 质量层：
  - `publish_surface_quality.py`
  - 现在 `offline_publish_plan` 和 `review_queue_policy` 共用同一套弱货判定
- 当前会更早挡掉这几类弱货：
  - 玩笑帖 / satire
  - `no_substantive_quotes`
  - `single_thread_weak_evidence`
  - `single_community_weak_evidence`
- 默认补货入口已经补到薄 pack / 空白 cluster：
  - `upstream-winds`
  - `tools-efficiency`
  - `funnel-conversion`
  - `category-winds`
  - `key-people-and-route`
  - `ai-product-and-adoption`
  - `platform-policy-shifts`
  - `small-goods`
- 当前离线发布面真实结果：
  - `candidate_count = 22`
  - `candidate_publish_surface_count = 8`
  - `weak_candidate_count = 9`
  - 说明弱货已经明显前移过滤，不再都拖到 review 才挡
- 当前候选池真实结果：
  - 总候选 `17`
  - `kept`：
    - `paid-economics = 3`
    - `funnel-conversion = 1`
    - `category-winds = 2`
    - `kill-signals = 2`
    - `upstream-winds = 2`
    - `tools-efficiency = 3`
  - `blocked`：
    - `funnel-conversion = 1`
    - `category-winds = 1`
    - `tools-efficiency = 1`
  - 被挡原因都集中在单帖单社区、quote 太薄
- 当前 stable 还守住了：
  - latest trend audit 仍是 `stable`
  - watched 社区 / pack 没有反弹
- 这轮 live collect / supply-repair 证据已经补到发布面：
  - 当前离线发布面已变成：
    - `candidate_count = 52`
    - `candidate_publish_surface_count = 34`
    - `weak_candidate_count = 5`
  - 当前优先薄 pack 已开始真实进入 publish surface：
    - `upstream-winds = 3`
    - `tools-efficiency = 4`
    - `funnel-conversion = 2`
    - `category-winds = 2`
  - 当前不能表述成“薄 pack 已稳定补厚”，只能表述成“开始冒头、开始进发布面”
  - 当前空白 cluster 也不能表述成“已清零”：
    - `ai-product-and-adoption / small-goods` 已开始出现
    - `key-people-and-route / platform-policy-shifts` 还没真正补起来
  - 所以这轮已经不再只是“少浪费”，而是“供给开始变厚”，但厚度验证还没彻底收官

当前已经按“达到结果后继续出卡，直到正式停机条件成立”为止真实跑完一轮：

- 本轮新增发布 `8` 张卡，发布总量从 `254 -> 262`
- 最新 snapshot / cloud_db / miniRelease / miniFavorites 已统一到：
  - `release-5e91837e625e`
- 这轮实际发出的卡包括：
  - `card-cand-ai-automation-1skqvp2-validate`
  - `card-cand-business-growth-ops-1soajtm-validate`
  - `card-cand-ecommerce-sellers-1soc03a-validate`
  - `card-cand-ecommerce-sellers-1smeee9-validate`
  - `card-cand-ai-automation-1so6z2t-validate`
  - `card-cand-ecommerce-sellers-1so8c4l-validate`
  - `card-cand-business-growth-ops-1so5k1a-validate`
  - `card-cand-ecommerce-sellers-1so92f5-validate`
- 这轮最终停机不是“发够了”，而是正式双条件成立：
  - `scope = null`（默认 `all-scope`）
  - `yield_exhausted = true`
  - `final actual_total = 0`
  - `final decision = publish`
  - `publish_ready = false`
- 也就是：
  - 采集侧已经耗尽
  - 发布侧也没有新的 publishable cards
  - 因此这轮可以正式停机

当前已经把“什么时候停”正式压进 SOP，并且按这条规则真实跑完了一轮 `all-scope -> collect -> sync -> plan -> gate -> review/publish -> snapshot -> 再回下一轮`：

- 本轮新增发布 `4` 张：
  - `card-cand-ai-automation-1snynsw-validate`
  - `card-cand-business-growth-ops-1sn7x6z-validate`
  - `card-cand-business-growth-ops-1so0wmk-validate`
  - `card-cand-business-growth-ops-1snufqe-validate`
- 最新 release 已更新到 `release-dfc7383d1f14`
- 当前停机不是因为“发够了”，而是因为双重条件同时成立：
  - `collect side = yield exhausted`
  - `publish side = no new publishable cards`
- 这轮真实停机字段已经跑出来：
  - `scope = all-scope`（`scope = null`）
  - `dry_cycles = 3`
  - `yield_exhausted = true`
  - `freshness gate final decision = publish`
  - `actual_total = 0`
  - 所以当前这轮可以正式停机

当前已经从“题材树四层和 yield exhaustion 已经落地”继续推进到“产品默认范围正式切成 all-scope，而且真实入口不带 `--scope` 时已经按全树工作”：

- `offline_publish_plan` 不再按旧 `pack programming` 做硬编排
- `run_offline_publish_plan` 默认范围已改成 `all-scope`
- `freshness gate` 不再因为固定 `15 / 9/4/2` 没凑满就硬 fail
- 当前默认 workflow 已变成：
  - `collect -> sync -> plan -> freshness gate`
  - 同时带出 `topic_tree_governance` 四层审计结果
- `offline_publish_plan` 不再把未 materialize 的 breakdown suggestion 当成可发项
- `freshness gate` 已新增 `yield_exhausted` 语义，真没货时不会再报假失败
- 当前治理补救也已进默认动作：
  - `rotation` 优先换计划项，不再直接删计划
  - `source_health` 会自动生成补社区 watch
  - `named topic budget` 已变回硬门槛，不再为了补 lane 强行塞同题材
- 当前默认入口都已切到全树：
  - `daily_collect.py`
  - `run_offline_publish_plan.py`
  - `run_intake_freshness_gate.py`
  - `audit_topic_tree_governance.py`
- 单 slice 现在只保留为显式局部修复模式，不再代表产品默认范围
- 热点争议图硬门槛仍然有效，没有被这轮治理改动打回旧世界
- 最新 mini snapshot 的前 30 张已经开始真正体现题材树 visible 治理，不再只是审计和日志层变好
- 题材树治理现在又往前压了一层：`publish_list` 的 plan-time selection 也开始直接吃 `source_health / scope / community / pack` 的过重信号，不再只靠 snapshot front30 末端纠偏
- 最新 `mini snapshot` 已从“250 张历史累积盘”切到“governed rolling inventory”：
  - 最新 release = `release-727805c2aaf3`
  - card_count：`250 -> 64`
  - 这次不只是 front30 更均衡，而是 latest inventory 本身已经开始去老社区 / 强 pack 化

## 最近完成了什么

1. 题材树四层已变成项目侧程序化审计
   新增了分配层、轮换 / 冷却层、供给诊断层、来源健康层的 evaluator，并统一收口到 `topic_tree_governance`。

2. `offline_publish_plan` 已接入题材树治理排序
   旧 `_PACK_PROGRAMMING_TARGETS` 不再主导当前计划面；现在是价值优先，再叠加题材树治理排序。

3. `freshness gate` 已拆掉旧固定模板硬 veto
   当前 `15 / 30` 和 `9/4/2` 只保留为窗口诊断，不再因为没凑满固定数量直接打回。

4. 三步治理已经收进项目侧默认实现
   - `rebalance_publish_list_for_governance` 现在只做“优先换，不盲删”
   - `rotation` watch 改成只拉 `day` 新货，且只拉少量 relief
   - `source_health` watch 继续负责补新社区来源
   - lane 选择阶段不再绕过 `named topic budget`

5. 默认范围已正式从临时 slice 切到全树
   当前产品默认范围 = `all-scope`；`business-growth-ops` 现在只表示局部修复模式。
   默认帮助文案、SOP、Makefile、脚本入口都已经同步，不再把单 slice 当产品默认。

6. 真实入口已验证全树默认不是口头合同
   不带 `--scope` 直接运行：
   - `run_offline_publish_plan` 返回 `scope = null`
   - `audit_topic_tree_governance` 返回 `scope = null`
   - `run_intake_freshness_gate --no-collect --no-named-topics` 返回 `scope = null`
   当前全树 plan 已经不只是“能排出 15 张”，而是真实跑通了默认的 `all-scope -> collect -> sync -> plan -> gate` 单轮 workflow。
   这里的 `publish-until-exhausted` 当前是默认运行纪律 / SOP，不是已经做成 shell 级自动整晚循环器。

7. 默认命令和 SOP 已同步
   `make hotpost-topic-tree-audit`、日常产卡 SOP、评审发布 SOP、小程序同步 SOP 都已明确写成“产品默认 = all-scope；单 slice 仅在显式局部修复时使用”。

8. 针对 all-scope 默认又补掉了 3 个真实漏口
   - `daily-watchlist` 之前只覆盖 AI 和电商，已补进 Growth，三大领域现在都在默认 named-topic watchlist 里
   - governance 补采之前只在显式单 scope 下触发；现在全树默认下也会按 rewrite scope 生成 watch
   - `audit_topic_tree_governance.py` 之前只吐整包原始 JSON；现在已补 `scope_summaries`，能直接看到四层结果

9. 保险审计与三步治理补漏已修掉真实漏口
   - 治理审计之前漏算了 ready draft / breakdown suggestion 的真实供给池
   - `named topic collect` 之前还会被旧 hot 目标数偷偷触发
   - lane 选择之前会绕开 `named topic budget` 强塞同题材
   现在这三处都已经按新合同收正，不再把 workflow 带回旧模板。

10. all-scope 默认发卡纪律已经真实跑到 exhaustion
   本轮把治理补采从“污染当前 cycle”改成“只服务下一轮 preview”，同时把 `governance-*` 命名题材候选排除出当前发布面。
   然后按默认全树规则一直发到 `actual_total = 0`、`yield_exhausted = true` 才停；本轮新增发布 `24` 张卡，发布总量从 `226` 增加到 `250`，最新 release / snapshot / cloud_db / miniRelease / miniFavorites 已统一到 `release-0fc67dd68272`，同步检查全绿。

11. 题材树治理已经从 publish planning 继续压到最终可见卡面
   新增 `topic_tree_visible_governance.py`，并把它接进 `mini_snapshot` 的 front30 选择逻辑；同时 `rebalance_publish_list_for_governance` 也开始把 visible 过重社区 / pack / scope 当成换位信号。
   最新 snapshot 已更新到 `release-068686464a53`。前 30 张从：
   - scope：`growth 13 / ecommerce 10 / ai 7`
   - 社区：`r/FacebookAds 5 / r/PPC 4`
   - pack：`paid-economics 11 / selection-signals 6 / agent-builder 5`
   变成：
   - scope：`ecommerce 12 / growth 11 / ai 7`
   - 社区：前 10 名全部降到 `2`
   - pack：`selection-signals 9 / organic-discovery 5 / funnel-conversion 5 / upstream-winds 4 / paid-economics 1`
   说明治理已经开始真正影响最终可见层，不再只是 audit 结果更好看。

12. 发布面与来源健康的收紧已经前移到 plan-time
   新增 `TopicTreePublishSurfacePlanner`，并把它接进 `offline_publish_plan` 的候选排序。当前在 lane 内选卡时，已经会主动吃：
   - `missing_scope_ids`
   - `overweight_scope_ids`
   - `overweight_pack_ids`
   - `overweight_communities`
   - `dominant_old_source_penalty`
   - `selected_community_penalty`
   这意味着治理不再只是“snapshot 前 30 张怎么排”，而是已经开始影响未来每轮真实 `publish_list` 的形成。
   最新真实验证：
   - `run_offline_publish_plan --limit 30`：默认 `scope = null`
   - `run_intake_freshness_gate --no-collect`：`decision = publish`、`actual_total = 0`、`yield_exhausted = true`
   说明实现已经落地，但当前全树库存这轮已经没有新的净新增价值，不是代码没吃上新规则。

13. latest inventory 已开始真正收缩并去历史偏斜
   新增 `topic_tree_rolling_inventory.py`，并把它接进 `build_mini_snapshot`。
   现在 snapshot 不再无条件吃掉全量已发布卡，而是：
   - 先按 lane freshness 去掉过时卡
   - 再按 `source_health / scope / pack / community` 做 governed rolling inventory
   - 最后再跑原来的 front30 visible governance
   真实结果：
   - `release-727805c2aaf3`
   - `card_count = 64`
   - full scope：`growth 30 / ecommerce 22 / ai 12`
   - full top community：`DigitalMarketing 9 / PPC 6 / BuyItForLife 6 / FacebookAds 6 / FulfillmentByAmazon 5`
   - full top pack：`paid-economics 16 / selection-signals 14 / organic-discovery 11 / agent-builder 8 / kill-signals 7`
   相比上一版 `250` 张库存：
   - `FacebookAds 19 -> 6`
   - `BuyItForLife 16 -> 6`
   - `ecommerce 15 -> 2`
   - `OpenAI 13 -> 3`
   - `PPC 13 -> 6`
   - `paid-economics 54 -> 16`
   - `selection-signals 51 -> 14`

14. 连续 `3-5` 个 release 的趋势审计已变成项目侧默认能力
   新增 `mini_release_trend_audit.py` 和 `audit_recent_mini_releases.py`，并补了 `make hotpost-release-trend-audit`。
   现在不再只是口头说“后面继续观察”，而是能直接对最近 `5` 个 release 输出：
   - `scope / pack / top community / front30`
   - `watching / rebound / stable`
   - 是否重新回到 `FacebookAds / PPC / BuyItForLife / paid-economics` 吃满
   最新真实结果：
   - latest release = `release-727805c2aaf3`
   - latest status = `watching`
   - front30 已无 watch alert
   - full inventory 仍有：
     - `community_over: FacebookAds / PPC / BuyItForLife`
     - `pack_over: paid-economics`
   说明“这轮没有反弹”已经可以被程序化证明，但还不能宣称长期结构已压稳。

15. rolling inventory stability 现在已经接进默认发布后动作
   `push_mini_snapshot.py` 在生成新 release 后会自动跑 `release trend audit`，并把：
   - `latest_status`
   - `remediation_focus`
   - `remaining_new_releases`
   一起写进输出。
   `check_mini_release_sync.py` 也新增了 `trend audit guard`，会强校验：
   - 趋势审计文件存在
   - 它的 `latest_release_id` 必须和当前 snapshot / cloud_db / miniRelease 一致
   这意味着后续每出一个新 release，默认都会自动进入同一套 `watching / stable / rebound` 裁判链，不再靠人工记得跑。

16. 首个 post-baseline release 已经真实压到库存阈值内
   本轮没有回头改 front30，而是只收 `topic_tree_rolling_inventory`。
   最新 release 已更新到 `release-ba1e32de9844`：
   - `card_count = 58`
   - `front30_alerts = []`
   - full inventory：
     - `r/FacebookAds = 5`
     - `r/PPC = 5`
     - `r/BuyItForLife = 5`
     - `paid-economics = 14`
   - `trend.rebounds = []`
   - `stable_streak = 1`
   - `remaining_new_releases = 4`
   说明这轮已经不是 `watching + over-cap`，而是第一张真正满足 full inventory 稳定条件的新 release。

## 当前真实阻塞

1. 当前这轮 all-scope 已经按规则发完并停机
   停机不是因为人工停，也不是因为旧模板，而是这轮真实结果已经变成：
   - `collect_stopped_by = yield_exhaustion`
   - `gate_decision = publish`
   - `actual_total = 0`
   - `publish_ready = false`
   这里要固定拆开说：collect 侧和 gate 侧的 `yield_exhausted` 不是同一个东西。
   另外，“这轮流程上可以停”不等于“结果健康”；如果当天只发 `1-2` 张，仍然要报成低供给，不能包装成正常节奏。

2. 下一轮 freshest supply 仍要继续观察
   本轮能跑通 all-scope 默认工作流，不等于后续每轮都会自动长出很多新卡；后续仍要继续看 freshest `hot / signal` 的补货速度和 `candidate -> publish` 穿透。

3. 题材树治理补采现在服务下一轮，不再该污染当前发布面
   当前已经把 governance collect 改成 next-cycle preview；后续如果要看它的真实增益，要在下一轮 collect / gate 里继续积累运行证据，而不是再把 preview 强塞回本轮发布面。

4. 仍需继续盯发布后真机面板效果
   仓内同步链已经全绿，但微信侧是否展示成预期，仍要继续按 release 节点做真机验收。

5. 当前 visible 层已经缓解，但底层库存结构并没有被一次性改写
   这轮改善主要体现在 `publish_list -> snapshot front30` 的最终可见层。
   `250` 张总库存的整体 community / pack 分布仍然保留历史发布累积结果；目前更准确的状态是：
   - `visible layer governance = 已落地`
   - `full inventory / long-run source health = 还没落地完`

6. 当前 plan-time 治理已经更强，但长期来源健康还没被一轮改干净
   当前高风险 pack 仍然集中在：
   - `upstream-winds`
   - `tools-efficiency`
   - `funnel-conversion`
   - `category-winds`
   - `kill-signals`
   也就是说，新的排序逻辑已经能提前压老来源和强社区，但历史库存和长期供给结构还需要靠后续几轮真实发布继续洗。

7. 当前 latest inventory 已经明显改善，但还不是最终稳态
   `64` 张是这轮在 freshness + governance 下还值得留在 latest release 的库存，不代表后续库存会永久稳定在这个数字。
   下一阶段要继续看的是：后续新发布进来后，latest inventory 能不能一边回升，一边继续维持去老社区 / 强 pack 化。

8. rolling inventory 稳定性验证已跑满 `5 / 5`，当前 latest 已从 `watching` 升到 `stable`
   最新 post-baseline release 已连续走到：
   - `release-ba1e32de9844`
   - `release-bd5725c3ee75`
   - `release-a8032ce3de22`
   - `release-81ab015d63be`
   - `release-de33e9da1942`
   当前 latest = `stable`，并且：
   - `front30_alerts = []`
   - `full_alerts = []`
   - `r/FacebookAds = 5`
   - `r/PPC = 5`
   - `r/BuyItForLife = 5`
   - `paid-economics = 14`
   - `trend.rebounds = []`
   这说明当前 rolling inventory stability 链已经从观察态走到了稳定态。

## 当前默认判断

- 当前正式合同已经真正落到项目侧：
  - `all-scope`
  - `value-threshold publishing`
  - `yield exhaustion`
  - `topic tree governance`
- 题材树问题以后不能再混成一句“今天发得不平衡”。
- 当前三步治理已经落成默认工作流，不再只是审计口径。
- 当前真实结论是：
  - 默认生产范围已经是全树
  - 当前全树默认工作流已经真实产出并发布
  - 当前停止条件是 `yield_exhausted = true`，不是旧模板，也不是假剩余卡
  - 当前题材树治理已经开始真正影响最终 front30，而不是只在审计输出里生效
  - 但 `publish-until-exhausted` 目前仍更像运行纪律 / SOP，不是 shell 级自动循环器

## 下一步

1. 后续发卡默认继续按 `all-scope` 跑，只有显式说“局部修复”才收回单 slice
2. 下一轮继续按 `collect -> sync -> plan -> freshness gate -> review/publish` 跑到 exhaustion，不再因为治理 preview 或旧模板中途误停
3. 继续观察 freshest `hot / signal` 的新货速度，以及治理补采在下一轮里的真实增益
4. 继续看下一轮新发布本身，是否也会比这轮更少被老社区和强 pack 吃满，不只是在 snapshot front30 上变均衡
5. 每轮发布后继续强制跑 `push_mini_snapshot -> check_mini_release_sync`，保持小程序同步链稳定
6. 继续观察 plan-time `publish_list` 收紧后，后续新 release 本身是否也开始同步去老社区 / 强 pack 化，而不是只靠 front30 末端治理
7. 继续观察 `governed rolling inventory` 在后续发布轮次里是否能把 latest inventory 从“64 张健康盘”逐步扩回更厚的健康库存，而不是再次堆回历史偏斜盘
8. 后续继续默认保留 release trend audit，但它现在从“验证是否能稳住”切成“守住 stable 后是否反弹”。
9. 当前稳定性观察窗已完成：
   - baseline = `release-727805c2aaf3`
   - latest stable = `release-de33e9da1942`
   - `stable_streak = 5`
10. 后续如果再出现 `FacebookAds / PPC / BuyItForLife / paid-economics` 回涨，只继续打库存层，不回头改 front30。
