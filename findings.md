# Findings

## 2026-05-06 主项目复位审计规划

- 主项目复位审计不能直接变成重构或清仓。当前根仓约 `1474` 条 dirty status，且含 `720 D / 43 M / 711 ??`；先分桶归因比直接清理更安全。
- 当前合理决策是 `SCOPE REDUCTION`：先做只读审计，确认主项目最短可验收链、过度工程化位置、脏仓来源和下一步最小修复面。
- 审计报告应落到 `reports/audits/mainline-reset-audit-2026-05-06.md`；phase-log 只有在审计结论被确认会改变主线状态时才更新。
- Hotpost 日运营和小程序产品态不是本轮修复对象。本轮只检查它们对主项目边界的影响，不能接管日常出卡，也不能改小程序子仓。
- 过度工程化判断必须有证据链：大文件、重复服务族、fallback / legacy / Any / except Exception、测试覆盖与真实入口不匹配。不能凭感觉删。
- phase-log 和 Serena 核实后，需要修正一个判断：项目确实做过系统解耦，尤其是报告链和 crawl 链。`ReportService` 当前只有 `191` 行，已拆出 runtime / factory / context loader / enrichment / assembly / payload builder；后续不应把它当作首要重构对象。
- 当前主项目最大未收口点更像是 `analysis_engine.py`：约 `4995` 行，虽然已有多个 `analysis_*_support.py` 模块，但 `run_analysis` 和周边 helper 仍承载太多职责。
- 主线 smoke 证据偏正面：后端 `70 passed, 1 skipped`，前端 `27 passed`；问题不是“主链完全不能跑”，而是缺一条明确、可复现、可验收的产品级 acceptance chain。
- 小程序对主项目的真正启发不是分析深度，而是产品机制：状态分层、gate、不可变正式资产、派生产物只读、前台不拉重任务。
- 主项目瘦身第一刀不应做新浅扫描页；应先把 `analysis_engine.py` 里已存在 support 模块承接的 readiness / insufficient sample / remediation 逻辑收回单一真相源。
- 当前已有 `analysis_readiness_support.py`、`analysis_remediation_support.py`、`analysis_artifacts.py`、`analysis_finalization_support.py`，所以继续新建 parallel scanner service 是过度设计。

## 2026-05-06 主项目 / Hotpost / 小程序边界侦查

- 当前不是“主项目 vs 小程序二选一”。正确结构是三轨：
  - 主项目轨：`community -> crawl -> semantic -> analyze -> report`，对应 Web 主产品和后台治理。
  - Hotpost 日运营轨：`collect -> plan -> gate -> review/publish -> release -> mini snapshot`，负责每天出卡。
  - 小程序产品轨：`hotpost-mini/hotpost-mini-app`，只消费正式发布后的快照和云函数数据。
- `hotpost-mini/hotpost-mini-app` 是独立 git 子项目；当前子仓库干净。主仓库当前有大量既有 dirty diff，后续必须避免把主仓整理动作混进小程序。
- 小程序不是内容真相源。`mini_snapshots` 和 `hotpost-mini/.../cloudfunctions/*/data` 都是派生产物，只能由 `push_mini_snapshot.py` 写入。
- Web 路由和后端 API 都已经分出主项目与 hotpost 运营面；边界问题主要是协作和任务归类，不是代码完全混成一团。
- 规划产物已落到 `docs/superpowers/specs/2026-05-06-project-boundary-operating-model-design.md`。
- 执行护栏已落地：根仓本地 exclude 忽略 `/hotpost-mini/`，`make boundary-status` 可分开显示根仓与小程序子仓状态。
- 干跑验证需要检查 `add 'hotpost-mini/...` 路径，而不是粗搜 `hotpost-mini`；粗搜会误命中文档文件名。

## 2026-05-06 运营规划

- 05 月以来正式发布历史里，首次出现的新社区是：`r/3Dprinting`、`r/AsianBeauty`、`r/AutoDetailing`、`r/Coffee`、`r/DIY`、`r/NewParents`、`r/SkincareAddiction`、`r/VacuumCleaners`、`r/carcamping`、`r/agi`。
- 这些新社区不是同一种资产：
  - `r/agi` 是 AI 大事件 / AGI 路线争议入口，适合和 `r/OpenAI / r/singularity / r/artificial` 联动看。
  - `r/AsianBeauty / r/SkincareAddiction / r/Coffee / r/VacuumCleaners / r/AutoDetailing / r/NewParents / r/carcamping` 更适合做用户需求侧 SKU 发现。
  - `r/DIY / r/3Dprinting` 更适合找工具、小配件、功能打印、替代方案，但容易混入作品展示，必须看评论有没有购买/替代/使用场景。
- 配置审计发现：`r/agi` 和 `r/AsianBeauty` 已进入发布历史，但未在 `hotpost_supply_discovery_v2.yaml` 的显式社区配置中命中；今天如果继续出强卡，后续应考虑补正式发现链。
- 今日不应继续单压 `r/DigitalMarketing` 或 `r/espresso`。昨天 top community 已经偏集中，今天应主动用新社区扩来源健康。
- 今日第一轮采集的真实质量分层：
  - AI 新增较厚，强候选集中在 Grok 被诱导转账、GPT-5.5 rollout、AI lab 状态谎报、Meta 训练数据诉讼、OpenAI/Musk 控制权争议。
  - GEO 有可用增量，重点是 AI search visibility 报告失真、llms.txt 之外的 AI 可见性、第三方页面 / Quora / Wikipedia / Wikidata 对 AI 引用的影响。
  - SKU 仍偏薄，真正接近“用户想买 / 值得做 SKU”的只有亚洲防晒囤货、工具质量信任、3D 打印机品牌体验、旧剃须刀柄兼容刀片；Skincare 个人求助和平台运营帖不能算 SKU。
  - gate 显示 publish 只说明新鲜度够，不代表内容价值够；本轮必须把 FBAds 情绪帖、SEO 版规帖、Etsy 抱怨帖、Amazon/FBA 操作帖挡在 V13 前。
- 今日发布验证：
  - 机器 gate 推荐池不能直接发布，人工挡噪音是必要步骤。
  - hot 争议图发布链路正常，`push_mini_snapshot --refresh-hot-controversy` 与同步检查均通过。
  - `google/gemini-3-flash-preview` semantic 仍会在个别帖子返回坏 JSON；正确处理是跳过失败样本，不切旧模型。
  - GEO 补厚有效，本轮新增 AI 搜索报告、llms.txt、Quora 分发三张商业增长卡，但来源仍偏 `DigitalMarketing / TechSEO`，后续还要继续拓来源。
- 首页排序问题根因不是 Upsert，也不是昨日卡消失，而是 `mini_snapshot` 的历史卡治理混排打散了最近发布日。产品正确口径应保护最近两天连续性：今天卡后面先接昨天卡，再让更早历史卡进入 lane / scope / breakdown 混排。
- 最新产品口径已进一步收紧：在没有检索、专题页和明确旧卡入口之前，首页不做任何旧卡混排；读者看到的就是运营发卡节奏，按 `published_at` 倒序排列。

## 2026-05-03 运营节奏规划

- 继续吃 7D 后的新结论：不是所有 7D 都没有货，而是高质量 SKU 候选集中在少数买家社区；卖家平台社区和 TikTok/Temu/AliExpress 搜索主要产出平台抱怨、账号风控和泛运营问题。
- 本轮强候选池扩厚到这些方向：
  - espresso / coffee：入门机、磨豆机、无塑料机器、可访问咖啡机
  - carry / outdoor：9L 出差包、30L 旅行包、SUV tent、睡垫/炉具/雨衣对比
  - BIFL / home / pet：桌面小升级、完整小工具包、ThumbScraper 替代、dog door、diaper bag
  - marketplace / maker：Etsy 产品图/材料采购、3D 打印商店反推、功能打印产品替代
- 明确弱项：厨房小家电、DIY 家装、roadtrip、Frugal、TikTokShop、Amazon/Shopify 卖家社区的净 SKU 命中率低；它们可作验证层，不适合作为下一轮主要发现入口。
- final gate 仍是 `rewrite`，说明系统层面还不能宣称“可发 15 张”；下一步如果要出卡，应先人工确认强候选清单，再逐个进入 V13 semantic，而不是继续扩大 7D query。
- 18 张补发已验证一个边界：候选池里能通过人工挑选发出强 SKU 卡，但 gate 仍会保留非 SKU / 低优先级 / 其他 scope 项；所以“发布 18 张”不能等同于“系统发布面清零”。
- `1t00xjt` 两次失败在同一个 semantic JSON 位置，属于当前 V13 semantic 修复链的边界样本；不能切旧模型绕过，也不应继续无上限重试。

- 继续深挖后的新判断：7D 不是完全吃干净，但标准 profile 的净新增已经变薄；必须按子类拆窄 query 才能继续出货。
- 15D 等效扩窗可用，但必须手动挡掉 `2026-04-18` 以前的 30D 老题，不能把月度结果当成 15D。
- 本轮真正补厚的 SKU 子类：
  - travel / carry：9L conference setup、30L onebag trip report、diaper bag、Dragonfly 容量反馈
  - coffee / kitchen：espresso beginner vs upgrade、grinder、accessories、used Gaggia deal、Zerno pre-order
  - product page / sourcing：Etsy makeup bag mockup、Etsy sourcing materials
  - pet / outdoor：dog door、Coleman stove / griddle
- Amazon / Shopify 的 15D 验证层不如预期：可见候选多是已发布、旧于 15D、平台操作或店铺技术问题，不能强行算 SKU 选品。
- 当前 queue 虽然 gate 显示 `publish`，但混入 AI / SEO / 社区元讨论；发前仍必须人工按 SKU 口径二次筛，不可直接发布。

- 用户反馈成立：日常运营不能直接从候选进入发布；正确节奏应是先列“当前能出的卡有多少、分别是什么内容领域”，等用户判断补什么，再进入 V13 seed / review / publish。
- 7D SKU 方向仍偏薄，原因不是没有任何候选，而是强 SKU 候选比例低：
  - 标准 `crossborder-sku-selection-7d` 复跑主要返回已发布题，净新增很少。
  - custom watch 如果 candidate_cap 被单一社区吃满，会导致 pet / outdoor / home 没被充分搜索。
  - 卖家社区继续容易产出平台操作、库存配置、社区元讨论，不天然等于 SKU 选品。
- 本轮 7D 二次深挖后，强 SKU 候选集中在：
  - 露营炉具 / griddle 取舍
  - dog door 值不值得买
  - Etsy makeup bag 产品图是否必须实拍
  - Etsy 新店材料采购质量取舍
- 弱候选集中在：
  - 医疗/眼镜镜片指数
  - 毛巾异味清洁
  - Shopify multipack 库存配置
  - Shopify 色块滚动修复报价
  - Etsy gift shop 店铺反馈

- 今日运营验证了一个实际边界：宽口径 `all-scope 7d` 在当前供给和接口状态下不适合作为唯一等待点；当它长时间无输出且不产出计划文件时，应收窄到明确薄领域 profile，而不是继续空等。
- `crossborder-sku-selection-7d` 能比礼品线更接近用户要求的“跨境 SKU 选品”：这轮发布的靴子、户外地毯、智能玄关收纳、FBA 库存、Etsy IP 风险、Amazon Listing 转化，都是商品 / 卖家可行性判断，不是送礼泛讨论。
- freshness gate 的 `publish_ready=true` 不能替代人工 review：final gate 仍保留 5 个 item，但其中有重复 AI 估值、社区元讨论、SEO 低优先级和平台规则噪音，不能为了清零硬发。
- V13 semantic 仍有治理价值：`1sw9a4f` 在 semantic 阶段坏 JSON，本轮正确处理是跳过，不切旧模型绕过。

- `reports/ops-log` 当前只有 `2026-04-30.md` 和 `2026-05-01.md` 两个最近发布日；没有 `2026-05-02.md` 和 `2026-05-03.md`。
- `2026-05-01` 发布 `29` 张，全部是电商与卖家，但包含较多 `GiftIdeas`，已经被事后纠偏：礼品消费观察不能直接算跨境 SKU 选品。
- 当前直接发卡不成立：pre-card audit 显示 no-collect freshness gate 为 `fail`，目标 `15`、实际 `1`、`stale_ratio=1.0`。
- 当前 validate queue 只有 `1t0d021` 候选和 `1su9hhp` 旧草稿；write queue 里仍有大量礼品、泛 BIFL、Kickstarter 候选，必须重新过 V13 人审，不能当可发库存。
- 今天正确节奏不是“补昨天日期”，而是用今天发布日志承接 05-02/05-03 内容窗口：先 fresh 采集，再 crossborder SKU 定向补薄，再 review / publish / snapshot。

## 2026-05-03

- V13 semantic 继续优化的关键不再是把 prompt 写长，而是把 brief 结构变成可审计资产：
  - lane-specific readout 让 hot / signal / breakdown 各自拿到对应判断位。
  - 结构化 `evidence_basis` 能降低证据串错风险。
  - `uncertainty` 能把弱证据、缺证据、单帖风险显式传给 writer/reasoning。
- 第 4 个治理能力已落地到 V13 shadow / published shadow / review CSV；补卡前可以抽样检查 Gemini semantic brief 是否读偏。

- V13 semantic prompt 原本只有 `core_scene / supported_claim / risk_bounds` 三个字段，能防止放大，但给 writer/reasoning 的信息密度偏低。
- 原链路里 semantic brief 只注入第一轮写卡 prompt；breakdown 阶段没有直接拿到 brief，只能看已经生成过的 signal draft。
- 更合理的最小增强是让 semantic brief 显式产出：
  - 主体与场景
  - 证据 basis
  - 用户/业务张力
  - why_now 读数
  - 风险边界
  - 写作焦点
  - 禁写结论
- 运行时审计确认当前生产链路已生效：V13 profile 是 Gemini semantic + DeepSeek Pro writer；默认 fast 是 DeepSeek Flash；reasoning/report 是 DeepSeek Pro。
- `backend/scripts/evals/run_hotpost_three_tab_prompt_ab_v8.py` 到 `v12.py` 仍保留历史实验用 `xiaomi/mimo-v2.5-pro`，但不属于当前 production profile。

## 2026-05-01

- “跨境选品”不能等同于“礼品/送礼”。礼品帖只能说明消费场景，不能自动证明某个 SKU 有跨境销售机会。
- 更可靠的选品真相源应分三层：
  - 用户/爱好者社区先发现真实购买需求、替代、耐用性、复购、场景痛点。
  - 卖家/平台社区只验证商业可行性，如利润、退货、变体、主图、价格、转化、类目拥挤度。
  - 众筹/预售社区只验证实物产品的早期信任、定价、设计、交付和原创性。
- `AmazonSeller / FulfillmentByAmazon / EtsySellers / shopify / ecommerce / TikTokShop` 这类社区不能当品类发现第一入口；它们天然更容易产出平台规则、运营抱怨和履约问题。
- `GiftIdeas` 应降级为显式礼品线来源，不能混入日常跨境 SKU 选品默认入口。

## 2026-04-22

- 当前小程序“登录 / 绑手机号 / 详情门禁”不是一条完整统一链：
  - 登录会话已完成
  - 当前 v1 决策已经改成只要求微信授权登录
  - 本地 backend 不再承担手机号绑定、积分、邀请奖励能力
- 前端 [auth.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/auth.ts) 当前是双分支：
  - 云环境：`miniAuth.login / bindPhone`
  - 非云环境：走本地 `wx-auth/login`
  - 且非云环境直接禁止 `bindPhone`
- 当前旧的“未登录可免费看 3 张”逻辑已经移除，详情页只剩登录 + 积分门禁。
- 当前云函数 `miniAuth` 已经具备：
  - `login`
  - `updateProfile`
  - `bindPhone`
  - 且 `mini_users` 云库已有 `phone_number / phone_masked / phone_bound_at`
- 当前最合理的路径不是补本地 backend，而是把 **整个用户系统** 统一收口到云开发：
  - 登录
  - 积分
  - 签到
  - 邀请奖励
- 这条路径的最小架构应该是：
  - `miniAuth`：只管登录、资料、绑手机号
  - `miniPoints`：只管积分余额、扣分、签到、邀请、流水
- “关注公众号 +100” 当前没有现成核验链，不能直接做真积分；这条只能标成阻塞项或后置项，不能在本轮假落地。
- 详情扣分最稳的落点不是首页点击时，而是详情接口成功拿到卡片后再扣；这样不会因为详情请求失败白扣积分。
- 邀请奖励最稳的完成时机不是“点分享”，而是“新用户完成首次授权登录”；否则无法证明是真新用户。
- 为了不把内容链一起切云，开发态新增单独的 `TARO_APP_USER_CLOUD_ENV_ID`，只把用户系统切到云开发，卡片内容链保持原调试方式。
- 当前小程序 AppID 是“个人主体已认证”，所以 `getPhoneNumber` 能力不成立；这不是代码 bug，而是主体权限边界。
- 因为当前 v1 决策是继续使用个人主体，小程序用户系统必须改收成“只登录”，不能再把手机号绑定作为门禁或积分触发条件。
- 这轮正确做法不是删掉手机号链，而是隐藏前端入口，同时把奖励、签到、详情门禁和邀请奖励全部改成只依赖登录。
