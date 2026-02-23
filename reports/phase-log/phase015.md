# phase015 · 分析报告主线与生成优化

- Spec：[`015-分析报告主线与生成优化.md`](../../.specify/specs/015-分析报告主线与生成优化.md)
- 当前阶段：Phase 0（主线确认与文档落地）
- 目标：主业务线文档落地，明确后续 Stats / Clustering / Report Agent 的接入位。

## 今日进展

- 新增：`backend/app/services/t1_stats.py`（Stats Layer 汇总：活跃度、P/S 比、痛点分布、品牌共现），`backend/scripts/generate_t1_stats_snapshot.py` → `reports/local-acceptance/t1-stats-snapshot.json`。
- 新增：`backend/app/services/t1_clustering.py`（规则版痛点聚类），`backend/scripts/generate_t1_pain_clusters.py` → `reports/local-acceptance/t1-pain-clusters.json`。
- 新增：`backend/app/services/report/t1_market_agent.py` + `backend/scripts/generate_t1_market_report.py`，可一键生成 `reports/t1-auto.md`（纯模板版，无 LLM 依赖）。
- Makefile 增加 `t1-stats-snapshot` / `t1-pain-clusters` / `t1-report-auto` 入口，便于跑离线路径。
- 测试：新增 `backend/tests/test_t1_market_agent.py`（模板渲染 smoke），未实际运行（缺 DB 环境）。
- 集成进展：在 `report_service.py` 增加 `_is_market_mode_enabled` + `_build_t1_market_report_md`，当 `enable_market_report` 或 `report_mode=market` 时优先使用 T1 pipeline 生成 Markdown，失败自动回退原版。
- 配置清理：`report_mode`/`market_report_template_path` 重复定义已移除；新增单测 `backend/tests/services/test_report_service_market_switch.py` 覆盖开关判定。
- 新增：`backend/scripts/t1_data_audit.py`（Make: `t1-data-audit`）用于输出 `reports/local-acceptance/t1-data-audit.json`；增加市场模式 Markdown 构建单测 `backend/tests/services/test_report_service_t1_market_md.py`。
- 新增文档：`reports/phase-log/phase015-data-audit.md`、`reports/phase-log/phase015-t1-review.md`、`reports/phase-log/phase015-acceptance.md`（DoD 检查）。
- 备注（Spec016 相关）：`/api/admin/metrics/semantic` 需 admin token 与可用 DB，未接权限或无库时会 YAML fallback（参见 Makefile TODO）。

## 风险/阻塞

- 尚未验证现有数据库快照是否满足 T1（48 个社区、12 个月）要求；Phase 1 需优先跑数据盘点。
- Report Agent 接入路径尚未落地，market 模式默认关闭；需要在 Phase 3 以后设计回退策略。
- 配置仍需梳理：`report_mode` 重复定义，market 模式未做端到端验证；需补充集成测试与回退策略说明。
- 尚未在有数据的环境跑端到端（需 DB）；市场模式回归测试未执行。
- 跨 Spec 文档未同步（Spec 008/010/013 尚未引用 T1 流水线与 market 模式）。

## 下一步

1) R015-T42：补充配置文档与 Spec 008/010/013 的引用更新，明确 technical/executive/market 三模式。  
2) 端到端回归（market 模式）并记录到 phase log。  
3) 评审差异修正：按 `phase015-t1-review.md` 建议优化品牌共现/聚类命名（可择机迭代）。

---

## 补充进展（facts_v2 防跑偏 · Phase1 上游锁盘）

### 发现了什么问题/根因？

- **B2B 话题撞上 B2C 模式的“盾牌”**：topic 是卖家侧（Shopify/广告/转化），但默认 market insight 会“屏蔽卖家社区”，导致真正的战场（`r/shopify`/`r/ecommerce`/`r/dropshipping`）被误杀，系统只能去大社区硬匹配关键词，最后跑到 `r/cooking` 这类生活盘。
- **锚点词过泛导致误命中**：像 `store` 这种词会把 “grocery store” 误当成赛道命中，进一步把生活内容引进来。

### 是否已精确定位？

- 是。跑偏链路发生在 **社区池筛选 + 样本抓取（posts/comments）** 两关：社区没被 topic 锁住，样本抓取又被泛词/聚类词污染，导致 facts_v2 “长得像对的，但内容不对味”。

### 精确修复方法（已落地）

- 新增 Topic Profile 机制：`backend/app/services/topic_profiles.py` + `backend/config/topic_profiles.yaml`，用“允许社区/社区模式/必须命中锚点/必须排除词”把分析宇宙锁死。
- 生成脚本接入 Topic Profile：`backend/scripts/generate_t1_market_report.py` 在 market insight 模式下，对 **卖家社区** 做 profile 例外（有 allowlist 就不再自动屏蔽），并对最终社区集合强制做 profile allow 过滤，避免 `r/cooking` 混入。
- 样本抓取加硬约束：posts/comments 抓取路径补齐 `required_entities` + `exclude_keywords`，并让评论抽取同时允许“锚点命中在帖子端”，减少“评论不提 Shopify 但在讨论 Shopify 广告”的误伤。
- 补单测：`backend/tests/services/test_topic_profiles.py`（纯逻辑单测，不依赖 DB）；为跑纯单测，`backend/tests/conftest.py` 增加 `SKIP_DB_RESET=1` 时跳过 DB truncate。

### 下一步做什么？

- 进入 Phase2：把 facts_v2 的 **口径统一**（source_range/aggregates 全部只算本次分析样本），并把 **high_value_pains / brand_pain / solutions** 从“空架子”改成“有数字、有证据”的真内容。

### 这次修复的效果是什么？

- 已把“跑偏的入口”钉住：Topic Profile 命中时，社区池与样本抓取都被收紧，默认策略从“泛召回”变成“宁可少，不要错”。
- 证据：已通过 `SKIP_DB_RESET=1 pytest -q backend/tests/services/test_topic_profiles.py`；脚本可编译（`python -m py_compile backend/scripts/generate_t1_market_report.py`）。

---

## 补充进展（facts_v2 防跑偏 · Phase2 中游：口径统一 + 真信号落地）

### 发现了什么问题/根因？

- **source_range 写错口径**：把 `days`（比如 180 天）当成 “样本条数”，导致报告里出现“我只看了 180 条，但聚合里像 10 万+”这种精神分裂。
- **痛点/品牌/方案模块是空壳**：pain_clusters / high_value_pains 转换时字段对不上（拿 pain_tree 当 cluster），brand_pain 链路拿不到作者，导致 `mentions>0 但 unique_authors=0`。

### 是否已精确定位？

- 是。问题集中在 facts_v2 的“中游组装层”：数据结构和统计口径没对齐，导致看起来像有模块，但其实没有“人+话+数字”的闭环证据。

### 精确修复方法（已落地）

- **口径统一（硬修）**
  - `backend/scripts/generate_t1_market_report.py`：`data_lineage.source_range` 改为真实样本量（`len(top_posts_db)` / `len(sample_comments_db)`），不再写 days。
  - `backend/scripts/generate_t1_market_report.py`：`aggregates.communities` / `aggregates.trend_analysis` 改为只基于本次样本统计（不再引用社区大盘量），从根上消灭 “180 vs 10万+”。
- **真信号落地（痛点/品牌/方案）**
  - 新增：`backend/app/services/facts_v2/midstream.py`：从本次样本里产出：
    - `pain_clusters_v2`：有 `mentions/unique_authors/evidence_quote_ids`（证据是 comment quote_id）
    - `brand_pain_v2`：按“品牌×痛点”聚合，拿作者去重，避免 `unique_authors=0` 的假数据
    - `solutions_v2`：按 topic_profile 做“宁缺毋滥”过滤，明显跑题的直接丢掉
  - `backend/scripts/generate_t1_market_report.py`：接入上述 midstream 产物，facts_v2 的关键模块不再靠“旧字段硬搬运”。
- **补齐必要字段**
  - `_fetch_top_posts` / `_fetch_sample_comments`：补回 `author_id/author_name/created_at/post_id`，让“唯一作者数”和“趋势按月”能算出来。
- **测试优先（已补）**
  - 新增：`backend/tests/services/test_facts_v2_midstream.py`（4 个纯单测），覆盖 source_range、pain_clusters、brand_pain、solutions 过滤。

### 下一步做什么？

- 进入 Phase3：加“质量闸门”，只要 facts_v2 跑偏或关键模块不完整，就**直接拒绝生成报告**（不调用 LLM，不落 report 文件），并把失败原因写清楚。

### 这次修复的效果是什么？

- facts_v2 的关键模块从“长得像对的”变成“有证据、有数字、口径一致”。
- 证据：`SKIP_DB_RESET=1 pytest -q backend/tests/services/test_facts_v2_midstream.py` 通过；脚本可编译（`python -m py_compile backend/scripts/generate_t1_market_report.py`）。

---

## 补充进展（facts_v2 防跑偏 · Phase3 下游：质量闸门硬挡 + 报告前置拦截）

### 发现了什么问题/根因？

- 以前的流程是：facts_v2 先生成 → 不管质量如何都继续走到 LLM 生成报告。结果就是“跑偏的 facts_v2 也会被写成一本正经的报告”，越写越离谱。
- 另外，facts_v2 的“自检脚本”只看了很少的字段，挡不住“内容跑偏”这种更致命的问题。

### 是否已精确定位？

- 是。必须在 **进入报告生成之前** 做硬闸门：只要跑偏/口径不一致/关键模块空，就直接拒绝生成报告。

### 精确修复方法（已落地）

- 新增质量闸门：`backend/app/services/facts_v2/quality.py`
  - 检查 3 件事：
    1) 赛道匹配度（样本里“锚点/关键词”命中比例）
    2) 核心模块完整度（痛点、品牌痛点、解决方案是否够用）
    3) 口径一致性（source_range 与 aggregates 汇总是否对得上）
  - 输出：`passed` + `flags` + `metrics`（给排查用）。
- 报告前置拦截：`backend/scripts/generate_t1_market_report.py`
  - facts_v2 写入文件前先跑 quality gate，把结果写回 `facts_v2.diagnostics.quality_gate`；
  - 若 `passed=false`：直接打印阻断原因并 `return`，**不再调用 LLM，不生成报告**。
- 修正 LLM 输入切片：`backend/scripts/generate_t1_market_report.py`
  - `build_facts_slice_for_report()` 支持 facts_v2 结构，避免 v2 包进了 LLM 但切片为空。
- 测试优先（已补）
  - 新增：`backend/tests/services/test_facts_v2_quality_gate.py`（3 个用例：topic_mismatch / range_mismatch / pass）。

### 下一步做什么？

- 用 Shopify topic 实跑一次 `backend/scripts/generate_t1_market_report.py --skip-llm`：
  - 先看 `facts_v2_*.json` 的 `diagnostics.quality_gate` 是否通过；
  - 不通过就按 flags 回溯（该补 profile、还是该收紧过滤、还是样本不足）。

### 这次修复的效果是什么？

- 系统做到“宁可不出报告，也绝不跑偏”：facts_v2 质量不达标时，报告阶段会被硬挡住。
- 证据：`SKIP_DB_RESET=1 pytest -q backend/tests/services/test_facts_v2_midstream.py backend/tests/services/test_facts_v2_quality_gate.py` 通过；脚本可编译（`python -m py_compile backend/scripts/generate_t1_market_report.py`）。

---

## 严厉测试（Shopify topic 实跑验收）

### 测试动作

- 单测回归（纯逻辑，不依赖 DB reset）：
  - `SKIP_DB_RESET=1 pytest -q backend/tests/services/test_topic_profiles.py backend/tests/services/test_facts_v2_midstream.py backend/tests/services/test_facts_v2_quality_gate.py`
- 真实生成（禁用 LLM 报告阶段，仅产出 facts_v2）：
  - `PYTHONPATH=backend OPENAI_API_KEY= python backend/scripts/generate_t1_market_report.py --topic "Shopify Traffic Ads Conversion" --product-desc "面向 Shopify 卖家的广告优化与转化率提升工具" --days 180 --mode market_insight --skip-llm`

### 验收结果（关键对齐项）

- ✅ 社区不再跑到生活盘：facts_v2 的核心社区以 `r/shopify / r/facebookads / r/ecommerce / r/dropshipping` 为主。
- ✅ 口径一致：
  - `data_lineage.source_range.posts/comments` = `sample_posts_db/sample_comments_db` 的真实条数；
  - `aggregates.communities` 的 posts/comments 汇总 = source_range（不再出现 180 vs 10万+ 的矛盾）。
- ✅ 质量闸门生效（宁可不出报告）：
  - 本次生成的 facts_v2 文件：`backend/reports/local-acceptance/facts_v2_2bb9ff2d-689b-4e07-870a-75878fa03a19.json`
  - `diagnostics.quality_gate.passed=false`，flags=`["pains_low","brand_pain_low","solutions_low"]` → 报告阶段会被硬挡住。

### 额外发现（测试中暴露的真实问题）

- JIT 标签阶段的全文检索（to_tsquery）会被“带空格的短语词”（如 `conversion rate`、`Facebook Ads`）炸掉；已在脚本里把 `topic_tokens/exclusion_tokens` 改为“单词级 token”再进 to_tsquery，避免语法错误。

---

## 补充进展（Phase3.5：分级产出策略 A/B/C/X，避免“要么满配要么不出”）

### 发现了什么问题/根因？

- 现在我们已经做到“宁可不出报告，也绝不跑偏”，但副作用是：只要 `pains_low / brand_pain_low / solutions_low` 出现，就一刀切不出报告。
- 这会让很多「赛道对了但料不够」的 topic，直接变成 0/1 极端结果：不是满配 7 模块，就是啥都没有。

### 是否已精确定位？

- 是。问题不在于又跑偏了，而是“质量闸门的输出只有 PASS/FAIL”，报告层也只认这个布尔值。

### 精确修复方法（已落地）

- 质量闸门改为分级输出：`backend/app/services/facts_v2/quality.py`
  - 返回 `tier`：`A_full / B_trimmed / C_scouting / X_blocked`
  - **硬挡不变**：`topic_mismatch` 或 `range_mismatch` → `X_blocked`（依然不生成报告）
  - **允许“诚实缩水”**：
    - 满足完整信号 → `A_full`（全量报告）
    - 至少有 1 个可用痛点线索 → `B_trimmed`（只精简输出 5–6，不硬凑 7）
    - 没有可用痛点，但赛道匹配 → `C_scouting`（只出 1–3 勘探简报）
- 报告生成按 tier 分流：`backend/scripts/generate_t1_market_report.py`
  - 写回 `facts_v2.diagnostics.quality_gate.tier`，便于排查
  - `X_blocked`：直接拒绝进入报告阶段（不调用 LLM）
  - `B_trimmed`：Part1 正常 + Part2 使用精简模板（新增 `_make_prompt_part2_trimmed`）
  - `C_scouting`：只生成一次“勘探简报”（新增 `_make_prompt_scouting_brief`）
  - 额外保护：`C_scouting` 不再写入 semantic_candidates（避免用“低密度样本”污染候选词）
- 测试优先（已补）
  - `backend/tests/services/test_facts_v2_quality_gate.py` 新增 2 个用例：`B_trimmed` / `C_scouting` 分流，并更新原 3 个用例断言 tier。

### 下一步做什么？

- 用 Shopify topic 再跑一次（建议先 `--skip-llm` 看 tier 与 flags）：
  - 目标：不跑偏时至少能稳定产出 `C_scouting` 或 `B_trimmed`，让“有但不够”的情况也能给出可读的勘探结果。
- 如果长期只停留在 `C_scouting`：说明“Shopify + Ads/Conversion 实战密度”确实偏低，需要回到上游扩大有效样本（比如更强的广告语境入场条件、或更聚焦的社区白名单）。

### 这次修复的效果是什么？

- 把“报告产出”从 0/1 变成 A/B/C/X 四挡：赛道对但料少时，系统可以输出“精简但诚实”的内容，而不是直接沉默。
- 证据：`SKIP_DB_RESET=1 pytest -q backend/tests/services/test_topic_profiles.py backend/tests/services/test_facts_v2_midstream.py backend/tests/services/test_facts_v2_quality_gate.py` 通过；脚本可编译（`python -m py_compile backend/scripts/generate_t1_market_report.py`）。

---

## 补充进展（Phase3.6：窄题“放水阀门”落地：专用门槛 + 扩窗扩圈 + 双钥匙入场）

### 发现了什么问题/根因？

- Shopify Ads 这种 **B2B 窄题**，用大盘统一门槛（比如痛点 mentions>=10、作者>=5）会天然判死刑：料再怎么筛也“聚不起来”。
- 另外一个更隐蔽的坑：我们做了“双钥匙”（Shopify + 广告语境）以后，样本里很多句子命中了 `pixel/attribution/ad account` 这类 **语境词**，但质量闸门的“赛道命中比例”只认 `include_keywords_any`，不认 `context_keywords_any`，导致出现 **假 topic_mismatch**（明明在聊广告归因，却被当成跑偏）。

### 是否已精确定位？

- 是。问题分两层：
  1) **阈值一刀切**：窄题缺少专用门槛；
  2) **赛道命中统计口径不完整**：闸门没有把“语境关键词”算进来。

### 精确修复方法（已落地）

- Topic Profile 扩展（窄题专用配置）：`backend/app/services/topic_profiles.py`
  - 新增字段：`preferred_days`、`pain_min_mentions/pain_min_unique_authors`、`brand_min_mentions/brand_min_unique_authors`、`min_solutions`、`require_context_for_fetch`、`context_keywords_any`
  - 新增工具函数：
    - `build_fetch_keywords()`：样本抓取只用“语境词”，把锚点词（Shopify）从 patterns 里剔掉
    - `filter_items_by_profile_context()`：二次过滤，确保每条样本真的命中语境词（双钥匙第二把钥匙）
- Shopify topic 的窄题阀门配置：`backend/config/topic_profiles.yaml`
  - 默认扩窗到 24 个月：`preferred_days: 730`
  - 语境词白名单：`context_keywords_any: [ROAS/CPC/CTR/pixel/attribution/... ]`
  - 专用门槛：`pain_min_mentions=5`、`pain_min_unique_authors=3`、`brand_min_mentions=3`、`brand_min_unique_authors=2`、`min_solutions=3`
  - 扩圈：补充 `r/JustStart`、`r/BigSEO`
- 生成脚本改造（扩窗 + 双钥匙入场 + 更准召回）：`backend/scripts/generate_t1_market_report.py`
  - 自动扩窗：topic 有 `preferred_days` 时自动把 `--days` 拉到至少该值
  - 抓样本改用 `topic_kw_for_fetch`（语境词），并在抓取后做 `filter_items_by_profile_context()` 过滤
  - `_fetch_sample_comments()` 新增 `days` 参数，修复“主查询固定 365 天”的问题
  - `_fetch_top_posts()` 的 patterns 匹配扩展到 body（避免只看标题漏掉广告语境）
- 质量闸门补齐“语境词口径”：`backend/app/services/facts_v2/quality.py`
  - `on_topic_ratio` 统计时把 `profile.context_keywords_any` 也算入命中集合，避免窄题误判 topic_mismatch
- B 档输出更“诚实”：`backend/scripts/generate_t1_market_report.py`
  - 精简版 Part2 标题里明确写“早期观察｜样本仍在累积”，避免写成定论
- 测试优先（已补）
  - `backend/tests/services/test_topic_profiles.py`：新增 fetch_keywords / context 过滤单测
  - `backend/tests/services/test_facts_v2_quality_gate.py`：新增“topic match 认 context_keywords”的单测

### 下一步做什么？

- 如果你想把 Shopify topic 从 `B_trimmed` 再推到 `A_full`：
  - 需要把 `good_brands` 拉起来（目前仍是 `brand_pain_low`），要么提高样本量，要么考虑把 `brand_min_evidence` 做成 profile 可配（窄题证据条数要求可更现实）。

### 这次修复的效果是什么？

- **不跑偏**仍然成立（双钥匙 + allowlist）。
- Shopify Ads 这种窄题不再被“假 topic_mismatch”硬拦截，能稳定产出 **B_trimmed 早期观察版** facts_v2。
- 严厉测试证据：
  - 单测回归：`SKIP_DB_RESET=1 pytest -q backend/tests/services/test_topic_profiles.py backend/tests/services/test_facts_v2_midstream.py backend/tests/services/test_facts_v2_quality_gate.py` 通过
  - 实跑（仅出 facts，不跑 LLM）：  
    `PYTHONPATH=backend OPENAI_API_KEY= python backend/scripts/generate_t1_market_report.py --topic "Shopify Traffic Ads Conversion" --product-desc "面向 Shopify 卖家的广告优化与转化率提升工具" --days 180 --mode market_insight --skip-llm`
  - 产物：`backend/reports/local-acceptance/facts_v2_57d58ec5-890d-4a25-bcbb-9b34d1e96ab8.json`
    - `diagnostics.quality_gate.tier="B_trimmed"`，`passed=true`
    - `on_topic_ratio=1.0`
    - 样本量：posts=22、comments=50（已做语境过滤，所以量小但更“对味”）
    - `good_pains=1`（已经能写 1 张早期痛点卡），`solutions=4`
    - 仍有 flags：`pains_low`、`brand_pain_low`（符合“早期观察版”的预期）

> 备注：环境里 LLM credits 报 402，已走降级/跳过路径，所以本次验收聚焦在 facts_v2 的“赛道对齐 + 能出 B 档”。
