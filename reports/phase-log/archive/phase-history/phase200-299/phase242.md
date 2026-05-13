# Phase 242 - Phase240 Round 2 (`--anchor-ts` + pains fallback)

## 这轮做了什么

### 1. 报告脚本支持固定时间锚点
- 文件：`backend/scripts/report/generate_t1_market_report.py`
- 新增 `--anchor-ts` CLI 参数，支持传入 ISO 8601 时间。
- 新增 `_parse_anchor_ts_arg()`，统一把 CLI 时间解析成 UTC。
- 入口改成优先吃 `--anchor-ts`，不传时才回退到当前 UTC 时间。

### 2. 固定输出里的时间字段和运行 ID
- `facts_dict["generated_at"]` 改成直接用 `anchor_ts`。
- `meta.time_window.end` 改成直接用 `anchor_ts`。
- `meta.time_window.start` 改成 `anchor_ts - days`。
- 当显式传入 `--anchor-ts` 时，`run_id / snapshot_id` 改成由 `topic + product_desc + mode + days + anchor_ts` 生成稳定 UUID，避免同参复跑时文件名和 `report_id` 自己漂。

### 3. V1→V2 pains 边界回退
- 把 pain 选择逻辑抽成 `_select_final_pains()`。
- 当 `V2 pains <= 1` 且 `V1 pains >= 5` 时，优先使用 V1 pains。
- 增加日志：
  - `⚠️ V1→V2 pains fallback: V2={v2_count} < 2, using V1={v1_count}`

### 4. 确定性模式下跳过写回副作用
- 这轮实跑时发现：即使 `--skip-llm`，脚本仍会执行 JIT comment labeling 和 `label_posts_recent()`，会改数据库状态，导致第二次运行输入已经变了。
- 为了让 `--anchor-ts` 真正能用于“确定性验证/回测”，当显式传入 `--anchor-ts` 时，脚本现在会跳过：
  - `_jit_label_comments(...)`
  - `label_posts_recent(...)`
- 运行时会打印：
  - `🧪 Deterministic validation mode: skipping JIT labeling/post labeling side effects.`

## 补的测试

- `backend/tests/services/report/test_report_logic.py`
  - `test_parse_anchor_ts_arg_accepts_iso_string`
  - `test_build_run_identifiers_are_stable_when_anchor_is_fixed`
  - `test_select_final_pains_prefers_v1_when_v2_is_too_thin`

## 验证结果

### 代码级验证
- AST:
  - `backend/scripts/report/generate_t1_market_report.py`
  - `backend/tests/services/report/test_report_logic.py`
  - 通过

### 回归测试
- 定向回归：
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_report_logic.py tests/services/analysis/test_facts_v2_quality_gate.py tests/services/analysis/test_facts_v2_midstream.py -q`
  - 结果：`36 passed`
- 质量门禁：
  - `SKIP_DB_RESET=1 make test-quality-gate`
  - 结果：`24 passed`

## 实跑结论（重要）

### 已确认修好的点
- `--anchor-ts` 已接通，运行日志会打印固定时间：
  - `🕒 Anchor timestamp: 2026-03-12T03:00:00+00:00`
- 输出文件路径和 `report_id` 在固定 `anchor-ts` 下已稳定，例如：
  - `facts_v2_ba686724-b8a2-54bc-bbff-27f4fd66d5c8.json`
- V1→V2 pains 边界兜底已生效，复跑时能看到：
  - `⚠️ V1→V2 pains fallback: V2=1 < 2, using V1=15`

### 这轮新发现的残留问题
- **同一个 `anchor-ts` 连跑两次，`facts_v2` 仍未完全一致。**
- 证据：
  - 在加入 `--anchor-ts` + 稳定 `run_id/report_id` 后，一次完整导出的哈希为：
    - `fbb7a743c4920ff4664186ac3092ced4cf4e8249`
  - 随后用同样参数再次复跑，**还没到导出阶段**，日志就已经开始分叉：
    - `_expand_topic_semantically()` 映射出的 token 集合不同
    - dynamic whitelist / blacklist 命中的社区不同
    - dedup 后评论数不同（例如 `132 -> 104` 与 `128 -> 106`）
  - 说明漂移源已经不只是在时间戳和输出元数据上。
- 说明：
  - 这说明 FIX-6 解决了“时间锚点自己漂”和“输出时间/ID 自己漂”的问题。
  - 但完整的确定性问题还没收完，至少还有 **topic semantic expansion / community relevance / dynamic whitelist** 这一段链路还在漂。

## 额外发现

- `--skip-llm` 跑完后，脚本还会尝试调用：
  - `backend/scripts/validate_facts_v2.py`
- 当前本地缺这个文件，日志会打印：
  - `can't open file '/Users/.../backend/scripts/validate_facts_v2.py'`
- 这次不影响脚本最终退出，也不影响 `facts_v2` 文件导出，但这是个现成的路径问题。

## 下一步建议

1. 把 `_expand_topic_semantically()` 的结果固定下来（如果内部用了非稳定排序 / LLM / 向量近邻，得补 tie-break 或缓存）。
2. 检查 `fetch_topic_relevant_communities()` 的 SQL / 排序 /打分口径，尤其是同分时的 tie-break。
3. 检查 dynamic whitelist / blacklist 生成链，确认：
   - 输入集合是否稳定
   - `context_scores` 的来源是否稳定
   - 相同分数时是否有明确排序
4. 这三块收完后，再重跑 `buy it for life products` 的双跑哈希比对。
