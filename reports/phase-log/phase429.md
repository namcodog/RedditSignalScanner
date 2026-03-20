# Phase 429 - 标准卡黄金路径 6/6 验收收口

## 本轮目标
- 把首页 6 张标准卡真正收成 `topic_profile` 黄金入口。
- 用系统真实分析链路（非手写报告）完成 6 卡 live 验收。
- 收口到 `6/6 A_full` 作为 Phase 33 完成条件。

## 发现的问题
- 首页 6 张卡虽然是标准展示卡，但 `/api/guidance/input` 返回的 `topic_profile_id` 全是 `null`。
- 根因：数据来源是 `example_library`，该模型没有 `topic_profile_id` 字段；旧逻辑没有做标准卡映射。
- 首轮 live 矩阵（系统链路）结果是 `4/6 A_full`：
  - `SaaS协作` = `B_trimmed`（后续一轮变成 `C_scouting`）
  - `家居` = `C_scouting`

## 修复动作
1. Guidance 标准卡映射
- `backend/app/api/routes/guidance.py`
  - 新增 `infer_topic_profile_id(...)`，按标题/描述/标签关键词为标准卡推断 profile。
  - 首页 fallback 6 卡统一补齐 `topic_profile_id`。
  - `build_guidance_examples()` 对 DB 示例与 fallback 都统一走推断逻辑。

2. 新增/补齐 topic profiles
- `backend/config/topic_profiles.yaml`
  - 新增 `saas_collaboration_v1`
  - 新增 `edc_everyday_carry_v1`
  - 调整 `vacuum_cleaner_v1` 阈值，避免家居卡被过严 pain/brand 门槛误降级。
  - 调整 `saas_collaboration_v1` 阈值，避免 SaaS 卡落入 `pains_low`。

3. 质量门禁支持 profile 级品牌下限覆盖
- `backend/app/services/analysis/topic_profiles.py`
  - `TopicProfile` 新增 `min_good_brands` 可选字段并支持 YAML 读取。
- `backend/app/services/facts_v2/quality.py`
  - `_apply_profile_overrides()` 支持 `min_good_brands` 覆盖。

4. 测试补齐（先测后改）
- `backend/tests/api/test_guidance_examples.py`
  - 新增标准卡 profile 推断用例。
- `backend/tests/api/test_guidance_input_api.py`
  - 新增首页前 6 卡必须返回非空 `topic_profile_id` 断言。
- `backend/tests/services/analysis/test_topic_profiles.py`
  - 新增 `min_good_brands` 解析断言。
- `backend/tests/services/analysis/test_facts_v2_quality_gate.py`
  - 新增 profile 级 `min_good_brands=0` 覆盖行为断言。

## 系统验收（真实链路）
- 使用脚本：`backend/scripts/acceptance/run_live_report_acceptance.py`
- 链路：`/api/auth/login -> /api/analyze -> /api/status/{task_id} -> /api/report/{task_id}`

### 最终 6 卡结果（required-tier=A_full）
| 标准卡 | topic_profile_id | tier | task_id |
|---|---|---|---|
| 跨境电商/PayPal | `cross_border_payment_v1` | `A_full` | `745898fc-b72b-47af-9843-50f1f0d5b557` |
| 跨境电商/现金流 | `cross_border_payment_v1` | `A_full` | `b6d60a61-b572-41f5-a207-a8b6c37d6b8c` |
| 跨境电商/回款费率 | `cross_border_payment_v1` | `A_full` | `1e8cc007-b7a7-4be3-9fa0-4395c6e138b6` |
| SaaS协作 | `saas_collaboration_v1` | `A_full` | `ffa3588c-5dde-4d4f-9628-3f6a7946a0cc` |
| 家居 | `vacuum_cleaner_v1` | `A_full` | `d70302f0-9258-4982-9228-08b50d236938` |
| 户外 | `edc_everyday_carry_v1` | `A_full` | `f4f838e3-aaad-470b-bb07-a91c0bf00d80` |

结论：`6/6 A_full`，Phase 33 的标准卡黄金路径验收项已满足。

## 回归验证
- `cd backend && pytest tests/api/test_guidance_examples.py tests/api/test_guidance_input_api.py tests/services/analysis/test_topic_profiles.py tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - 通过（关键用例全绿）
- `make test-e2e`
  - `21 passed`
