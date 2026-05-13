# Progress

## 2026-05-06

- 已完成主项目复位审计规划：
  - 已新建 CEO 视角审查文档：`docs/superpowers/specs/2026-05-06-mainline-reset-audit-ceo-review.md`。
  - 已新建独立执行计划：`docs/superpowers/plans/2026-05-06-mainline-reset-audit-plan.md`，没有写入根目录日运营 `task_plan.md`。
  - 计划采用只读优先：先做边界预检、脏工作区分桶、phase-log 真相源复核、主链地图、过度工程化审计、最小测试证据，再输出审计报告。
  - 已把根仓极脏纳入 P0 审计输入：当前 `git status --short | wc -l = 1474`，分布为 `720 D / 43 M / 711 ??`。
  - 验证通过：计划文档 `git diff --check` 无输出；`make boundary-status` 显示小程序子仓仍干净。
- 已执行主项目复位审计主体：
  - 审计报告已写入 `reports/audits/mainline-reset-audit-2026-05-06.md`。
  - 已校正过度工程化判断：报告模块历史上已完成实质解耦，当前不应重做 `ReportService` 解耦；剩余最大风险是 `analysis_engine.py`。
  - 后端主线 smoke：`70 passed, 1 skipped, 22 warnings`。
  - 前端主线 smoke：`5 files passed / 27 tests passed`。
  - 数据边界已核实：默认 Dev 库，Gold 库有 guard；旧 archive 里的直连金库命令不能当当前 SOP。
  - 收口验证：`make boundary-status` 通过，小程序子仓 `git status --short` 为空，审计报告 `git diff --check` 通过。
- 已完成“小程序机制反哺主项目瘦身”的融合规划：
  - 设计文档：`docs/superpowers/specs/2026-05-07-mainline-mini-inspired-slimming-design.md`。
  - CEO 审查：`docs/superpowers/specs/2026-05-07-mainline-mini-inspired-slimming-ceo-review.md`。
  - 工程审查：`docs/superpowers/specs/2026-05-07-mainline-mini-inspired-slimming-eng-review.md`。
  - 执行计划：`docs/superpowers/plans/2026-05-07-mainline-mini-inspired-slimming-plan.md`。
  - 核心结论：借小程序的发布机制、gate、snapshot、只读前台和单一真相源，不借它的浅分析深度。
  - 第一刀范围：只收 `analysis_engine.py` 中 readiness / insufficient sample / remediation 的重复边界，让已有 support 模块成为真实单一真相源。

- 已完成主项目 / Hotpost / 小程序边界侦查与规划：
  - Serena 确认项目已激活，Python 侧主项目分析/报告入口和 hotpost API 入口分层存在。
  - 核实 Web 路由里主项目页面与 `/hotpost...` 运营页面分开；小程序是 `hotpost-mini/hotpost-mini-app` 独立 git 子项目，当前子仓库干净。
  - 已新建规划文档：`docs/superpowers/specs/2026-05-06-project-boundary-operating-model-design.md`。
  - 本轮没有改小程序子仓库、没有改 hotpost 发布资产、没有覆盖当天出卡 `task_plan.md`。
- 已完成边界防污染护栏落地：
  - 根仓本地 `.git/info/exclude` 已忽略 `/hotpost-mini/`，防止误 `git add .` 纳入小程序目录。
  - 新增 `scripts/check-boundary-status.sh` 和 `make boundary-status`，用于提交前分开检查根仓 / 小程序子仓状态。
  - `AGENTS.md` 已补简洁边界规则；边界设计文档和独立执行 plan 已同步。
  - 验证通过：`make boundary-status`、小程序子仓 `git status --short`、针对 `hotpost-mini` 的 `git add -n` 干跑、`git diff --check`。

- 已完成今天发卡运营规划：
  - 使用 05-03 至 05-05 运营日志确认近期节奏：05-03 SKU 偏重、05-04 GEO/商业偏重、05-05 均衡但无 breakdown。
  - 从最新发布历史核实 05 月以来新增社区 10 个，其中 SKU 用户需求社区 9 个、AI 路线社区 1 个。
  - 已把今天计划写入 `task_plan.md`，把新社区判断写入 `findings.md`。
- 当前下一步：
  - 跑基础 `all-scope 7d`。
  - 围绕新社区做定向深挖。
  - 再列出“当前能出的候选数量和领域”，给用户确认后进入 V13 seed / review / publish。

- 已完成今天第一轮采集与 gate：
  - `all-scope 7d` dry-run 长时间无有效输出，已终止，避免空等。
  - 定向采集新增：AI 大事件 `12` 条、SKU 消费需求 `6` 条、工具/家居/车品 SKU `2` 条、GEO/AI 搜索 `14` 条。
  - 当前 validate queue 为 `25` 个候选；离线计划统计 `candidate_count=89`、`publish_surface_count=21`、`weak_candidate_count=57`。
  - no-collect freshness gate 最终 `decision=publish`，但推荐池混入 FBAds 情绪帖、SEO 版规帖、Etsy 平台噪音，不能直接自动发。
  - 下一步是先人工筛噪音，再给用户确认进入 V13 seed / review / publish 的候选清单。

- 已完成今天第一轮正式发卡：
  - 发布 `11` 张：`hot 3 / signal 8 / breakdown 0`。
  - 类别分布：`AI 与自动化 4 / 商业增长与运营 3 / 电商与卖家 4`。
  - 最新小程序快照：`release-6e41636c3a58`，`card_count=678`。
  - 同步检查通过：`check_mini_release_sync.py`、`npm run check:mini-snapshot-data`。
  - GPT-5.5 卡在 Gemini semantic 阶段坏 JSON，Demis Hassabis 卡被 V13 文案校验挡下；未切旧链路绕过。
  - post-publish gate 仍为 `decision=publish / publish_ready=true / actual_total=13`，但剩余项多为噪音、重复或失败样本；本轮发卡完成，系统收口未清零。

- 已修复首页最近发布日排序：
  - 根因：mini snapshot 生成时把“今天卡之后的历史卡”继续做治理混排，导致 2026-05-05 马斯克 / OpenAI 卡被旧 breakdown 和更老卡打散。
  - 修复后：首页顺序恢复为 `今天卡 -> 昨天卡 -> 更早历史卡治理混排`。
  - 新快照：`release-0632318e5539`，`card_count=678`。
  - 验证：前 11 条为 2026-05-06，新 25 条 2026-05-05 紧随其后；`check_mini_release_sync.py` 和 `npm run check:mini-snapshot-data` 通过。

- 已按用户确认关闭旧卡混排：
  - 首页展示改为纯运营发卡顺序，不再为了 lane / scope / breakdown 多样性插入旧卡。
  - 新快照：`release-57ccf5b2a52b`，`card_count=678`。
  - 验证：首页顺序为 `2026-05-06 -> 2026-05-05 -> 2026-05-04...`，马斯克 / OpenAI 昨日卡紧跟在 05-05 日内顺序里。
  - `test_mini_snapshot.py`、`check_mini_release_sync.py`、`npm run check:mini-snapshot-data` 均通过。

## 2026-05-03

- 已把 SKU 7D 继续深挖到主要可见增量，不进入 V13 seed / publish：
  - 覆盖家居清洁、众筹实体产品、小工具/耐用品、厨房小家电、育儿、护肤美妆、桌面办公、车载、DIY 家装、maker/3D 打印。
  - 对有效桶提高到 `candidate-cap=20` 做最后一轮：espresso、carry/outdoor、BIFL/home/pet、maker/parenting。
  - validate queue 从 `49` 增至 `57`；final no-collect gate 仍为 `rewrite / publish_ready=false`，`actual_total=8`，`lane_counts=hot 7 / signal 1`，原因是 `signal_target_window_underfilled`。
  - 结论：7D 已吃到主要可见增量，但不能直接发布；下一步只能从强 SKU 候选里人工挑选，再走 V13 semantic。

- 已按用户确认发布 18 张 SKU 卡，作为 2026-05-02 内容窗口补发：
  - 实际 `published_at` 按系统真实时间记录在 `2026-05-03`，不回填伪造 05-02 时间。
  - 18 张全部为 `电商与卖家`，结构为 `hot 10 / signal 8 / breakdown 0`。
  - 本日合计变为 `25` 张：`hot 11 / signal 14 / breakdown 0`，总卡数 `590`。
  - 最新小程序快照 `release-9f44a7745215`；`check_mini_release_sync.py` 和 `npm run check:mini-snapshot-data` 通过。
  - final no-collect gate 仍为 `rewrite / publish_ready=false / actual_total=8`，原因是 `signal_target_window_underfilled`；发卡目标完成，但系统收口未完成。

- 已继续深挖跨境 SKU，不进入 V13 seed / publish：
  - 7D 新增 travel/carry、coffee/kitchen、marketplace product page 三组窄 query。
  - 15D 等效扩窗已执行：用 `month` 检索，再按 `2026-04-18` 之后的 `created_at` 口径筛。
  - queue 目前为 `20` 个候选；gate 显示 `publish`，但其中混有 AI / SEO / 社区元讨论，不能直接视为 SKU 可发池。
  - SKU 强候选从约 `4` 个扩到约 `10-12` 个，主要集中在旅行背包、咖啡设备、Etsy 产品页、宠物家居、户外炉具。
  - Amazon / Shopify 15D 方向净新增弱，多数是旧题、已发布题或平台操作题。

- 已按用户反馈修正发卡节奏，进入 SKU 7D 二次深挖，但没有发布：
  - 当前 queue 深挖前只有 `6` 个候选，SKU 相关不足。
  - `crossborder-sku-selection-7d` 复跑返回 `11` 个候选，但大多已发布或已打回，不能继续靠复跑补量。
  - 拆窄执行用户需求、宠物/家居、户外/家居、卖家验证四组 7D query。
  - 深挖后 review queue 为 `15` 个候选；其中 SKU 相关 `9` 个，强可出约 `4` 个。
  - no-collect gate 为 `rewrite`，原因是 `signal_target_window_underfilled`；本轮不进入 publish，先给用户确认。

- 已完成 05-02 / 05-03 内容窗口的发卡运营：
  - 先跑 `all-scope 7d`，但宽口径命令长时间无输出且没有生成计划文件，已终止。
  - 改跑 `crossborder-sku-selection-7d`，新增 `11` 个候选。
  - 正式发布 `7` 张：`hot 1 / signal 6 / breakdown 0`，全部为 `电商与卖家`。
  - 发布重点是跨境 SKU / 商品判断 / 众筹预售信号，没有把 `GiftIdeas` 当默认 SKU 真相源。
  - 最新同步：`release-c0a4c90f59bb`，`card_count=572`；`check_mini_release_sync.py` 和 `npm run check:mini-snapshot-data` 通过。
  - final gate 还剩 `5` 个 publish surface item，但已人工判定为重复、偏题或低优先级；发布完成，严格停机清零未达成。

- 已完成前天 / 昨天 / 今天出卡运营节奏规划前置审计：
  - 运营日志确认：`2026-05-01` 有 `29` 张发布；`2026-05-02 / 2026-05-03` 暂无运营日志。
  - 当前门禁确认：V13 配置和小程序同步链正常，但 freshness gate fail，不能直接从旧队列发布。
  - 当前队列确认：validate 只有 `1t0d021` 和旧草稿 `1su9hhp`；write queue 中礼品 / 泛 BIFL / Kickstarter 候选较多，需要重新按 SKU 口径筛。
  - 已把今日运营节奏写入 `task_plan.md`：all-scope 7d 基础轮 -> `crossborder-sku-selection-7d` 定向补薄 -> gate/review/publish/snapshot -> 更新 05-03 运营日志。

- 已完成 V13 semantic 出卡前增强：
  - schema 已加入 `lane_specific`，覆盖 hot / signal / breakdown 三类判断位。
  - `evidence_basis` 已从字符串数组改成 `claim / community / quote_text / permalink` 结构化对象。
  - 新增 `uncertainty`，包含 `confidence / missing_evidence / weak_points / single_thread_risk`。
  - V13 shadow JSON / MD、published shadow refresh plan / report、review CSV 都会携带 semantic brief 或摘要。
- 验证记录：
  - 先加红灯测试覆盖 schema 与 artifact 缺口。
  - 改完后目标回归：`47 passed`。
  - 运行时确认 V13 仍为 `google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro`。

- 已完成 Hotpost V13 LLM 配置生效审计：
  - 运行时确认 `fast_model=deepseek/deepseek-v4-flash`。
  - 运行时确认 `reasoning_model=deepseek/deepseek-v4-pro`。
  - 运行时确认 production profile 为 `hotpost_v13_title_standalone`，模型链为 `google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro`。
- 已完成 semantic prompt 最小增强：
  - schema 从 3 字段扩为主体、场景、证据、张力、why_now、边界、写作角度和禁写结论。
  - V13 breakdown 阶段现在也会收到同一份 semantic brief。
- 验证记录：
  - 先加红灯测试，确认旧 schema 信息不足、breakdown prompt 没收到 brief。
  - 修改后目标回归：`47 passed`。

## 2026-05-01

- 已完成跨境 SKU 选品纠偏治理：
  - 新增 `crossborder-sku-selection-7d` profile。
  - `selection-30d-small-goods-broad` 已移除默认 `GiftIdeas` watch。
  - `selection-30d-gift-crossborder / selection-30d-gift-emotional-value` 已明确为显式礼品任务入口。
  - 更新补卡合同、日常 SOP、运营日志、CURRENT_STATUS、OPEN_ITEMS、phase1055、phase1056 和 INDEX。
  - 新增 `backend/tests/services/hotpost/test_named_topic_watch_profiles.py`。
- 验证记录：
  - 先跑红灯测试：新 profile 不存在、旧 broad 仍含 `GiftIdeas`，符合预期失败。
  - 改配置后复跑：`PYTHONPATH=backend pytest backend/tests/services/hotpost/test_named_topic_watch_profiles.py -q`，`2 passed`。

## 2026-04-22

- 已完成：
  - 运行 `keyos status --json`、`keyos check --json`，确认当前门禁健康
  - 读取 `using-superpowers`、`plan-ceo-review`、`plan-eng-review` 相关 skill 规则
  - 核实当前小程序前端登录/绑手机号/详情门禁链
  - 核实当前云函数 `miniAuth` 与本地 backend `wx-auth` 的真实差异
  - 核实当前仓库里没有公众号关注核验链，不能直接做 `+100` 真积分
  - 新增 `miniPoints` 云函数，落地积分汇总、详情扣分、签到、邀请 token
  - 扩展 `miniAuth`，首次授权登录发 `60` 分，并在新用户完成首次授权登录时给邀请人 `+30`
  - 前端认证统一切云开发；详情门禁从“试看”改成“登录+积分”
  - 新增积分页、个人页积分卡、签到入口、分享入口
  - 首页品牌名改成 `深蓝singal`
  - 隐藏绑手机号入口，保留相关代码位待后续企业主体恢复
  - 云函数测试通过；开发构建、生产构建通过
- 当前判断：
  - P0 主体代码已经落地，剩余工作集中在云端部署和真机验收
  - 不再补本地 backend 的平行实现
  - 公众号积分仍只保留产品位，不能发真积分
  - 当前 AppID 为个人主体，绑定手机号能力在微信侧不可用；当前合同已经改收成“只登录”
- 下一步：
  - 部署云函数 `miniAuth / miniPoints / miniFavorites`
  - 在云开发数据库完成 `mini_users / mini_user_points_ledger / mini_user_referrals` 验收
  - 真机验证首次登录 +60、详情 -10、签到 +10、邀请 +30
