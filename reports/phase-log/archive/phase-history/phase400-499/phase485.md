# Phase 485 - 用语义一致性替代领域硬编码扩张

## 本轮目标

- 回答一个核心担忧：当前系统里是否还在继续堆硬编码领域规则。
- 用更科学的方式处理两个统一断点：
  1. 跨领域中文 pain 串味
  2. 低信号英文机会标题穿透
- 继续用真实 live 证明修复不是靠运气。

## 发现

### 1. 仓库里确实有旧的语义识别能力

- SOP 里明确写过 `LLM Semantic Mapping`：
  - `docs/sop/数据挖掘sop_v5.2_pure_data.md`
- 代码里已有通用语义能力：
  - `backend/app/services/analysis/hybrid_matcher.py`
  - `backend/app/services/semantic/text_classifier.py`
  - `backend/app/services/discovery/warzone_classifier.py`
- 但这些能力之前主要停在“前置理解/匹配”，没有接到当前报告链的领域一致性过滤上。

### 2. 当前旧 fallback 里确实存在不允许继续扩张的硬编码

- `backend/app/services/report/analysis_payload_loader.py`
  里的 `_PRODUCT_DESCRIPTION_PAIN_RULES` 属于代码级领域规则。
- 这类规则可以作为短期兜底存在，但不能继续当主方案扩张。
- 原则已经明确：
  - 不再继续靠加更多领域 if/规则表推进
  - 不允许 mock 数据
  - 不允许把硬编码当成主链能力

## 本轮修复

### 1. 新增领域语义一致性过滤

- 文件：
  - `backend/app/services/report/analysis_payload_loader.py`
- 新增能力：
  - `_get_warzone_classifier()`
  - `_classify_warzone(...)`
  - `_collect_pain_evidence_texts(...)`
  - `_enforce_domain_coherence_on_pain_points(...)`
- 行为：
  - 先用现有 `WarzoneClassifier` 判断题面属于哪个 warzone
  - 再对每条 pain 的标题/描述/样例帖子做 warzone 归属判断
  - 如果痛点明显属于别的 warzone，就从当前 canonical 输入里剔除
  - 然后再用当前题面的中文痛点脚手架补齐缺口

### 2. 新增低信号英文机会标题拦截

- 文件：
  - `backend/app/services/report/structured_report_fallback.py`
- 新增能力：
  - `_is_low_signal_scaffold_opportunity_title(...)`
- 行为：
  - 对 `高频抱怨：<纯英文半句>` 这类标题直接判低信号
  - 回退为围绕中文 pain 的业务机会标题

## 测试

- `pytest backend/tests/services/report/test_analysis_payload_loader.py backend/tests/services/report/test_structured_report_fallback.py -q -k 'cross_warzone or prefixed_high_frequency_english_opportunity_title or coffee or outdoor or frugal or parenting or workflow'`
- 结果：
  - `11 passed`

新增定向测试：
- `test_validate_report_analysis_payload_filters_cross_warzone_pain_leakage`
- `test_enforce_structured_report_contract_replaces_prefixed_high_frequency_english_opportunity_title`

## 真实 live 验证

### Coffee

- `task_id = 1973a808-75b9-45be-b4bb-74fdb7426e25`
- `report_tier = C_scouting`
- `analysis_blocked = scouting_brief`
- `target_communities`
  - `r/pourover`
  - `r/espresso`
  - `r/Coffee`
  - `r/superautomatic`
- `pain_titles`
  - `每次磨豆和萃取参数都要重新试，出杯很难稳定`
  - `同一包豆子也容易忽好忽坏，稳定复现很难`
  - `机器、磨豆机和豆子搭配太多，新手很难少走弯路`
- `opportunity_titles`
  - `围绕「每次磨豆和萃取参数都要重新试，出杯很难稳定」的产品机会`
  - `围绕「同一包豆子也容易忽好忽坏，稳定复现很难」的产品机会`

结论：
- 低信号英文机会标题已经被打掉。
- 现在剩下的是样本深度不足，不是输出乱漂。

### Frugal

- `task_id = f1071499-e603-4d59-97aa-7fe0d75e497a`
- `report_tier = C_scouting`
- `analysis_blocked = scouting_brief`
- `target_communities`
  - `r/Frugal`
  - `r/povertyfinance`
  - `r/personalfinance`
- `pain_titles`
  - `订阅默默续费后才发现，账单总在事后才补救`
  - `价格一点点往上调，长期支出被悄悄放大`
  - `为了省一点钱要来回比价切换，执行成本反而很高`
- `opportunity_titles`
  - `围绕「订阅默默续费后才发现，账单总在事后才补救」的产品机会`
  - `围绕「价格一点点往上调，长期支出被悄悄放大」的产品机会`

结论：
- 跨领域电商收款 pain 串味已经被打掉。
- 现在剩下的也主要是 `scouting_brief`，不是跨领域输出污染。

## 本轮结论

- 当前系统里确实存在旧的领域硬编码兜底，但这条路已经明确停止扩张。
- 这轮开始把旧的语义能力接到报告链断点上，用 warzone 语义一致性做过滤。
- 两个统一问题都已经被真实 live 打到：
  1. `Frugal` 的跨领域中文 pain 串味已消失
  2. `Coffee` 的低信号英文机会标题已消失

## 下一步

1. 继续用同一套语义一致性思路做完整 8 领域复验。
2. 判断剩余问题是否都已收敛成：
   - `scouting_brief`
   - 样本深度不足
3. 若成立，再进入下一阶段：
   - 提升 `C_scouting / B_trimmed -> A_full`
   - 固化最终 SOP
