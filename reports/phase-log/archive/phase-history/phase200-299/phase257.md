# Phase 257 - Dev 库社区治理整治报告（只读快照 + dry-run）

## 执行时间
- 2026-03-13

## 执行目标
- 不做真实删除，只对 `reddit_signal_scanner_dev` 输出一份可执行的社区治理整治报告。
- 统一回答 4 个问题：
  - 现在真正生效的社区是哪些？
  - 还在候选池里的社区是哪些？
  - 应该清理的垃圾社区是哪些？
  - 有没有异常状态需要人工介入？

## 执行口径（本次固定）
- 真正生效的社区，只认 `community_pool` 中满足以下条件的记录：
  - `is_active = true`
  - `deleted_at is null`
  - `is_blacklisted = false`
- `discovered_communities` 只算候选池，不算生效池。
- `Top1000` 永远视为废弃噪音源，只允许 `deprecated_ignored`，不参与导入。
- 本次只跑 `build_snapshot()` + `cleanup_dev(dry_run=True)`。
- 本次 **没有** 执行真实删除。
- 本次 **没有** 修改数据库表结构，也 **没有** 新增 migration。

## 目标数据库
- `reddit_signal_scanner_dev`

## 快照结果总览

| 维度 | 数量 |
| --- | ---: |
| 生效社区 | 141 |
| 候选社区 | 126 |
| Pool 垃圾社区 | 190 |
| Discovered 垃圾记录 | 39 |
| 异常记录 | 0 |

## dry-run 预计删除量

| 删除目标 | 数量 |
| --- | ---: |
| `community_pool` 待删行 | 190 |
| `community_cache` 待删行 | 190 |
| `discovered_communities` 待删行 | 39 |

说明：
- 这里只是 dry-run 结果，不代表已经删除。
- 如果后续执行真实清理，删的是垃圾记录，不会动当前 141 个生效社区。

## 关键结论

### 1. 现在真正生效的社区有 141 个
- 它们已经是当前系统真正起作用的社区池。
- 分类分布如下：

| 分类 | 数量 |
| --- | ---: |
| `Home_Lifestyle` | 30 |
| `Ecommerce_Business` | 21 |
| `Tools_EDC` | 20 |
| `Family_Parenting` | 19 |
| `Minimal_Outdoor` | 19 |
| `Frugal_Living` | 14 |
| `Food_Coffee_Lifestyle` | 13 |
| `AI_Workflow` | 5 |

### 2. 候选池有 126 个，但里面有 108 个和旧垃圾池重名
- 这 108 个不是“当前生效社区”，只是 `pending` 候选。
- 它们之所以看起来混乱，是因为同名社区同时存在：
  - 一份旧的、失效的 `community_pool` 垃圾记录
  - 一份新的、还在审核的 `discovered_communities` 候选记录
- 这正是“社区列表黑盒”的主要来源之一。

### 3. 真正应该清理的垃圾一共 229 条
- `community_pool` 垃圾：190
- `discovered_communities` 垃圾：39
- 当前没有异常状态（`anomaly_count = 0`）

### 4. Top1000 不会再污染社区池
- 这轮口径已经纠正完成。
- 即使文件还在，也只会被记成 `deprecated_ignored`，不会再导入。

## 生效社区明细（141）

### AI_Workflow（5）
- `r/automation`
- `r/chatgpt`
- `r/localllama`
- `r/promptengineering`
- `r/stablediffusion`

### Ecommerce_Business（21）
- `r/aliexpress`
- `r/dropship`
- `r/dropshipping`
- `r/ecommerce`
- `r/ecommercemarketing`
- `r/entrepreneur`
- `r/etsy`
- `r/etsysellers`
- `r/facebookads`
- `r/flipping`
- `r/freelance`
- `r/logistics`
- `r/marketing`
- `r/printondemand`
- `r/saas`
- `r/seo`
- `r/smallbusiness`
- `r/startups`
- `r/techseo`
- `r/tiktokshop`
- `r/walmartsellers`

### Family_Parenting（19）
- `r/autism_parenting`
- `r/babybumps`
- `r/beyondthebump`
- `r/blendedfamilies`
- `r/cats`
- `r/daddit`
- `r/divorce`
- `r/dogs`
- `r/education`
- `r/familyissues`
- `r/homeschool`
- `r/marriage`
- `r/parenting`
- `r/parentingteenagers`
- `r/pets`
- `r/puppy101`
- `r/relationship_advice`
- `r/relationships`
- `r/toddlers`

### Food_Coffee_Lifestyle（13）
- `r/airfryer`
- `r/askculinary`
- `r/barista`
- `r/cheap_meals`
- `r/coffee`
- `r/cooking`
- `r/espresso`
- `r/fermentation`
- `r/pourover`
- `r/smoking`
- `r/sousvide`
- `r/tea`
- `r/wine`

### Frugal_Living（14）
- `r/budgetfood`
- `r/buyitforlife`
- `r/eatcheapandhealthy`
- `r/frugal`
- `r/frugalmalefashion`
- `r/leanfire`
- `r/mealprepsunday`
- `r/minimalism`
- `r/preppers`
- `r/simpleliving`
- `r/thrifting`
- `r/ukpersonalfinance`
- `r/walmartcanada`
- `r/zerowaste`

### Home_Lifestyle（30）
- `r/appliances`
- `r/aquariums`
- `r/cleaningtips`
- `r/cozyplaces`
- `r/diy`
- `r/electricians`
- `r/fixit`
- `r/gardening`
- `r/handyman`
- `r/home`
- `r/homeautomation`
- `r/homebrewing`
- `r/homebuilding`
- `r/homedecorating`
- `r/homeimprovement`
- `r/homeowners`
- `r/houseplants`
- `r/hvac`
- `r/ikeahacks`
- `r/interiordesign`
- `r/landscaping`
- `r/lawncare`
- `r/malelivingspace`
- `r/plumbing`
- `r/reeftank`
- `r/remodel`
- `r/smarthome`
- `r/solar`
- `r/tinyhouses`
- `r/woodworking`

### Minimal_Outdoor（19）
- `r/backpacking`
- `r/bicycling`
- `r/bikepacking`
- `r/bushcraft`
- `r/campingandhiking`
- `r/cycling`
- `r/digitalnomad`
- `r/hammockcamping`
- `r/hiking`
- `r/mountaineering`
- `r/onebag`
- `r/overlanding`
- `r/running`
- `r/solotravel`
- `r/survival`
- `r/trailrunning`
- `r/travel`
- `r/ultralight`
- `r/vanlife`

### Tools_EDC（20）
- `r/3dprinting`
- `r/askelectronics`
- `r/autodetailing`
- `r/battlestations`
- `r/carpentry`
- `r/desksetup`
- `r/flashlight`
- `r/justrolledintotheshop`
- `r/knives`
- `r/lockpicking`
- `r/mechanicalkeyboards`
- `r/metalworking`
- `r/multitools`
- `r/outdoorsgear`
- `r/pens`
- `r/tacticalgear`
- `r/tools`
- `r/watches`
- `r/welding`
- `r/workbenches`

### 额外口径提示
- 生效社区的 `tier` 基本都是 `high`。
- 只有 `r/battlestations` 还是旧口径 `Tier A`，说明池里还留有一条旧 tier 命名风格记录，但它当前是有效社区，不属于垃圾。

## 候选社区明细（126）

### 纯候选（18）
- 这些名字当前不在垃圾 pool 里，是真正值得后续评估的候选。
- 名单如下：
- `r/artificial`
- `r/asianamerican`
- `r/china`
- `r/chineselanguage`
- `r/conspiracy`
- `r/crafts`
- `r/icleanedmyroom`
- `r/indianhomedecor`
- `r/machinelearning`
- `r/modelmakers`
- `r/nosleep`
- `r/openclaw`
- `r/paintbynumbers`
- `r/stocks`
- `r/tarotjourneys`
- `r/toys`
- `r/twoxchromosomes`
- `r/ufyh`

### 候选与旧垃圾 pool 重名（108）
- 这些不应该算生效社区。
- 真正要做的是：删掉旧的 pool 垃圾记录，保留 `pending` 候选，后续重新评估。
- 代表性高频候选如下（按 `discovered_count`）：
- `r/edc` (40)
- `r/onlineincomehustle` (39)
- `r/twoxchromosomes` (36)
- `r/conspiracy` (30)
- `r/indianhomedecor` (30)
- `r/stocks` (30)
- `r/toys` (30)
- `r/digitalincomepath` (25)
- `r/u_softtechhubus` (24)
- `r/paintbynumbers` (23)
- `r/bestofredditorupdates` (21)
- `r/worldnews` (21)
- `r/dumbphones` (20)
- `r/ufyh` (19)
- `r/passive_income` (18)

完整 126 个候选名录：
- `r/3dprintentrepreneurs`
- `r/alphaandbetausers`
- `r/amazonfbatips`
- `r/anticonsumption`
- `r/artificial`
- `r/asianamerican`
- `r/askreddit`
- `r/assholedesign`
- `r/atyr_alpha`
- `r/aves`
- `r/beermoneyuk`
- `r/bestofredditorupdates`
- `r/buhaydigital`
- `r/businessideas`
- `r/casualpt`
- `r/ccw`
- `r/chess`
- `r/china`
- `r/chineselanguage`
- `r/clickup`
- `r/cofounderhunt`
- `r/conspiracy`
- `r/couchtuner`
- `r/crafts`
- `r/craftycommerce`
- `r/damnthatsinteresting`
- `r/damnthatsreal`
- `r/deduction`
- `r/digitalincomepath`
- `r/digitalminimalism`
- `r/dnd`
- `r/dropshipnospam`
- `r/dumbphones`
- `r/edc`
- `r/edmproduction`
- `r/electricdaisycarnival`
- `r/entrepreneurs`
- `r/eticaret_yildizi`
- `r/etsycommunity`
- `r/europe`
- `r/everydaycarry_india`
- `r/facepalm`
- `r/freelance_forhire`
- `r/glocks`
- `r/hamiltonwatches`
- `r/hfy`
- `r/icleanedmyroom`
- `r/indiabusiness`
- `r/indianentrepreneur`
- `r/indianhomedecor`
- `r/interestingasfuck`
- `r/jenova_ai`
- `r/leagueoflegends`
- `r/leatherman`
- `r/london`
- `r/machinelearning`
- `r/mademesmile`
- `r/managers`
- `r/manybaggers`
- `r/melanotan2`
- `r/mildlyinteresting`
- `r/modelmakers`
- `r/motorbuzz`
- `r/movies`
- `r/news`
- `r/nlsalaris`
- `r/nosleep`
- `r/nostupidquestions`
- `r/notion`
- `r/notiondeutsch`
- `r/onlineincomehustle`
- `r/openclaw`
- `r/paintbynumbers`
- `r/passive_income`
- `r/pcmasterrace`
- `r/piracy`
- `r/pmcareers`
- `r/printify`
- `r/productivity`
- `r/productivityapps`
- `r/productresearcher`
- `r/projectmanagement`
- `r/recruitinghell`
- `r/redditpregunta`
- `r/reviewmyshopify`
- `r/romancenovels`
- `r/sandiego`
- `r/selfhosted`
- `r/shopify`
- `r/shopify_hustlers`
- `r/shopifydev`
- `r/sidehustlegrind`
- `r/sideproject`
- `r/siliconvalleybayarea`
- `r/sketchywatches`
- `r/skookum`
- `r/smallbusinessindia`
- `r/startups_promotion`
- `r/stocklaunchers`
- `r/stockmarket`
- `r/stocks`
- `r/superstonk`
- `r/sweatypalms`
- `r/tariffs`
- `r/tarotjourneys`
- `r/technology`
- `r/thesidehustle`
- `r/thinkingdeeplyai`
- `r/tiktokcringe`
- `r/tiktokshophelps`
- `r/toys`
- `r/trumptariffnews`
- `r/twoxchromosomes`
- `r/tybusers`
- `r/u_enoumen`
- `r/u_jasoncarlmorgan`
- `r/u_lilyymagno`
- `r/u_softtechhubus`
- `r/ufyh`
- `r/virtualassistant4hire`
- `r/wallstreetbets`
- `r/wayofthebern`
- `r/webdev`
- `r/whaaat_ai`
- `r/whatsinmybag`
- `r/worldnews`

## 应清理的垃圾明细

### A. `community_pool` 垃圾（190）

#### A1. `inactive`（130）
- 这些是失效 pool 记录，应直接删除。
- 名单如下：
- `r/3dprintentrepreneurs`
- `r/aliexpressbr`
- `r/alphaandbetausers`
- `r/amazon_influencer`
- `r/amazonanswers`
- `r/amazonecho`
- `r/amazonprime`
- `r/amazonvine`
- `r/amitheasshole`
- `r/anticonsumption`
- `r/askmen`
- `r/askreddit`
- `r/assholedesign`
- `r/atyr_alpha`
- `r/aves`
- `r/baking`
- `r/beermoneyuk`
- `r/bestofredditorupdates`
- `r/buhaydigital`
- `r/businessideas`
- `r/casualpt`
- `r/ccw`
- `r/chess`
- `r/childfree`
- `r/clickup`
- `r/climbing`
- `r/cofounderhunt`
- `r/couchtuner`
- `r/craftycommerce`
- `r/damnthatsinteresting`
- `r/damnthatsreal`
- `r/decorating`
- `r/deduction`
- `r/digitalincomepath`
- `r/digitalminimalism`
- `r/dnd`
- `r/dropshipnospam`
- `r/dumbphones`
- `r/edmproduction`
- `r/electricdaisycarnival`
- `r/entrepreneurs`
- `r/eticaret_yildizi`
- `r/etsycommunity`
- `r/europe`
- `r/everydaycarry_india`
- `r/facepalm`
- `r/fixedgearbicycle`
- `r/freelance_forhire`
- `r/geartrade`
- `r/glocks`
- `r/hamiltonwatches`
- `r/hfy`
- `r/indiabusiness`
- `r/indianentrepreneur`
- `r/interestingasfuck`
- `r/jenova_ai`
- `r/leagueoflegends`
- `r/leatherman`
- `r/london`
- `r/mademesmile`
- `r/managers`
- `r/manybaggers`
- `r/matcha`
- `r/mechanicadvice`
- `r/melanotan2`
- `r/mildlyinteresting`
- `r/mommit`
- `r/motorbuzz`
- `r/movies`
- `r/news`
- `r/nlsalaris`
- `r/nostupidquestions`
- `r/notion`
- `r/notiondeutsch`
- `r/onlineincomehustle`
- `r/passive_income`
- `r/pcmasterrace`
- `r/peopleofwalmart`
- `r/piracy`
- `r/pmcareers`
- `r/printify`
- `r/productivity`
- `r/productivityapps`
- `r/productresearcher`
- `r/projectmanagement`
- `r/raisedbynarcissists`
- `r/recruitinghell`
- `r/redditpregunta`
- `r/reviewmyshopify`
- `r/romancenovels`
- `r/sandiego`
- `r/selfhosted`
- `r/shopify_hustlers`
- `r/sidehustlegrind`
- `r/siliconvalleybayarea`
- `r/sketchywatches`
- `r/skookum`
- `r/smallbusinessindia`
- `r/spellcasterreviews`
- `r/startups_promotion`
- `r/stepparents`
- `r/stocklaunchers`
- `r/stockmarket`
- `r/superstonk`
- `r/sweatypalms`
- `r/tariffs`
- `r/teachers`
- `r/technology`
- `r/thesidehustle`
- `r/thinkingdeeplyai`
- `r/thrifty`
- `r/tiktokcringe`
- `r/tiktokshophelps`
- `r/tiktokshopsellersclub`
- `r/toolporn`
- `r/trumptariffnews`
- `r/tybusers`
- `r/u_enoumen`
- `r/u_jasoncarlmorgan`
- `r/u_lilyymagno`
- `r/u_softtechhubus`
- `r/virtualassistant4hire`
- `r/wallstreetbets`
- `r/walmart`
- `r/walmart_rx`
- `r/wayofthebern`
- `r/webdev`
- `r/whaaat_ai`
- `r/whatsinmybag`
- `r/worldnews`

#### A2. `inactive + row_blacklisted`（60）
- 这些不但失效，而且行级已黑名单，更应该直接删。
- 名单如下：
- `r/amateurroomporn`
- `r/amazon`
- `r/amazonargentina`
- `r/amazondspdrivers`
- `r/amazonemployees`
- `r/amazonfba`
- `r/amazonfbaonlineretail`
- `r/amazonfbatips`
- `r/amazonfc`
- `r/amazonflexdrivers`
- `r/amazonfresh`
- `r/amazonmerch`
- `r/amazonreviews`
- `r/amazonseller`
- `r/amazonsellercentral`
- `r/amazonwtf`
- `r/askwomen`
- `r/bbq`
- `r/beer`
- `r/bestaliexpressfinds`
- `r/bigseo`
- `r/breadit`
- `r/churning`
- `r/cleaning`
- `r/cocktails`
- `r/digital_marketing`
- `r/dropshipping_guide`
- `r/dropshippingtips`
- `r/edc`
- `r/edcexchange`
- `r/fascamazon`
- `r/femalelivingspace`
- `r/financialindependence`
- `r/food`
- `r/fuckamazon`
- `r/fulfillmentbyamazon`
- `r/gadgets`
- `r/homeoffice`
- `r/hydrohomies`
- `r/instacartshoppers`
- `r/instantpot`
- `r/knifeclub`
- `r/legomarket`
- `r/organization`
- `r/outdoors`
- `r/personalfinance`
- `r/povertyfinance`
- `r/seo_marketing_offers`
- `r/shopify`
- `r/shopifyappdev`
- `r/shopifydev`
- `r/shopifyecommerce`
- `r/shopifyseo`
- `r/shopifywebsites`
- `r/sideproject`
- `r/stickerstore`
- `r/thriftstorehauls`
- `r/trueoffmychest`
- `r/vent`
- `r/walmartemployees`

### B. `discovered_communities` 垃圾（39）

#### B1. `pending_duplicate_in_effective_pool`（32）
- 这些已经在正式有效池里有同名社区了，候选记录应删。
- 名单如下：
- `r/3dprinting`
- `r/airfryer`
- `r/aquariums`
- `r/askelectronics`
- `r/automation`
- `r/cats`
- `r/chatgpt`
- `r/cozyplaces`
- `r/desksetup`
- `r/diy`
- `r/dogs`
- `r/dropship`
- `r/dropshipping`
- `r/ecommerce`
- `r/etsy`
- `r/etsysellers`
- `r/facebookads`
- `r/hvac`
- `r/justrolledintotheshop`
- `r/lawncare`
- `r/localllama`
- `r/malelivingspace`
- `r/marketing`
- `r/pets`
- `r/promptengineering`
- `r/puppy101`
- `r/reeftank`
- `r/saas`
- `r/stablediffusion`
- `r/techseo`
- `r/tiktokshop`
- `r/woodworking`

#### B2. `status_blacklisted`（6）
- 这些候选本身已经是黑名单状态，应删。
- 名单如下：
- `r/amateurroomporn`
- `r/cleaning`
- `r/femalelivingspace`
- `r/homeoffice`
- `r/instantpot`
- `r/organization`

#### B3. `approved_duplicate_in_effective_pool`（1）
- 这类说明候选记录已没有保留价值。
- 名单如下：
- `r/battlestations`

## 异常项（0）
- 当前没有“approved 但不在有效池”“未知状态”“软删异常”等异常记录。
- 这说明本次需要做的，主要是垃圾清理，不是流程救火。

## 对这次 Dev 清理的判断

### 可以直接清的
- `community_pool` 里的 190 条垃圾记录
- `community_cache` 里对应的 190 条缓存记录
- `discovered_communities` 里的 39 条垃圾记录

### 不该动的
- 141 个当前生效社区
- 126 个候选社区中的有效 `pending` 候选
- 尤其是 18 个“纯候选”社区，后面应该继续评估，不该误删

### 清理完成后的预期结果
- 生效社区仍然是当前 141 个
- 候选社区保留 126 个中的有效 `pending` 部分
- 池内历史垃圾和重复 discovered 记录会明显减少
- 后面人和 AI 再看社区治理，不会再把“失效 pool + pending 候选 + 重复 discovered”混成一团

## 输出文件
- 机器可读快照：
  - `reports/phase-log/phase257_governance_snapshot.json`
- 本报告：
  - `reports/phase-log/phase257.md`

## 验证方式
- 使用 `CommunityGovernanceService.build_snapshot()`
- 使用 `CommunityGovernanceService.cleanup_dev(dry_run=True)`
- 数据库：`reddit_signal_scanner_dev`
- 未执行真实删除
