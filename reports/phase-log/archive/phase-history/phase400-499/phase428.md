# Phase 428 - 合同修复实施（第一批落地）

## 目标

按 Phase 32 的实施计划，先落地三件高价值修复：
1. 首页标准卡可携带 `topic_profile_id` 进入黄金路径
2. 开放提问（无 profile）不再因 fallback topic check 被硬拦 `X_blocked`
3. `X_blocked` 交付不再只有废话提示，降级结果要有可用内容

## 本轮改动

### 1) 标准卡 -> 黄金入口接线

- 后端 guidance 示例结构新增 `topic_profile_id`：
  - 文件：[guidance.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/api/routes/guidance.py)
  - fallback 示例中为可用赛道补了 profile：
    - `cross_border_payment_v1`
    - `shopify_ads_conversion_v1`
    - `vacuum_cleaner_v1`
  - `build_guidance_examples()` 会透传 DB 示例里的 `topic_profile_id`（若存在）。

- 前端输入页接入 `topic_profile_id`：
  - 文件：[guidance.api.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/api/guidance.api.ts)
  - 文件：[InputPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/InputPage.tsx)
  - 标准卡点击后会记录该卡绑定的 `topic_profile_id`，提交时一起发给 `/api/analyze`。
  - 用户后续手动改写描述时会自动清掉该 profile，避免“卡片 profile 误绑到新描述”。

### 2) 开放提问主链去硬拦

- 文件：[analysis_engine.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/analysis/analysis_engine.py)
- `quality_check_facts_v2()` 调用从固定 `skip_topic_check=False` 改为：
  - `skip_topic_check = (topic_profile is None)`

结果：
- 有 profile 的黄金路径仍保留 topic check 门禁
- 无 profile 的开放提问不再因为 fallback 英文 token 被误杀为 `topic_mismatch -> X_blocked`

### 3) X_blocked 降级交付增强

- 文件：[analysis_rendering.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/analysis/analysis_rendering.py)
- `report_tier == "X_blocked"` 时，报告正文会附带 `render_scouting_report()` 内容，而不是只给拦截说明。

- 文件：[product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)
- 前端将 `X_blocked` 从 `directional` 调整为 `enriching` 路径。
- 报告首屏文案从“先把方向定下来”改为“先看已抓到的线索，不直接下结论”。

## 测试与验证

### Backend

```bash
cd backend && pytest tests/api/test_guidance_examples.py tests/services/analysis/test_facts_v2_quality_gate.py tests/services/analysis/test_analysis_engine.py::test_run_analysis_does_not_hard_block_open_question_without_profile -q
```
- 结果：`22 passed`

```bash
cd backend && pytest tests/services/analysis/test_analysis_rendering.py tests/services/analysis/test_analysis_engine.py::test_run_analysis_quality_gate_blocks_when_topic_mismatch -q
```
- 结果：`2 passed`

```bash
cd backend && pytest tests/api/test_guidance_input_api.py -q
```
- 结果：`1 passed`

### Frontend

```bash
cd frontend && npm run test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ReportPage.test.tsx
```
- 结果：`12 passed`

```bash
cd frontend && npm run build
```
- 结果：通过

### Full-chain Acceptance

```bash
make test-e2e
```
- 结果：`21 passed`

```bash
make test-e2e-live-report-5x
```
- 结果：通过（`5/5`，每轮 `required-tier=A_full`）

## 结论

- 合同修复第一批已经落地，核心偏差点（标准卡不走黄金入口、开放题被硬拦、X_blocked 只交废话）都已进入可运行状态。
- 当前 Phase 32 已完成。
- 下一步进入 Phase 33：补齐“首页 6 张标准卡黄金路径”端到端验收。
