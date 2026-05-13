# Phase 445 - 首页 6 卡 live 稳定性 x2 通过，前端验收现场已备好

## 发现了什么？

- 按 `6 张卡 x 2 轮` 的口径继续做真实 live 稳定性验证。
- 第一轮刚开跑时，矩阵脚本自己先暴露了一个真实技术债：
  - `backend/scripts/acceptance/run_topic_profile_full_a_matrix.py`
  - 还在检查旧章节名 `## 决策卡片`
  - 但当前 narrative 报告口径已经切到 `## 决策风向标`
- 这不是产品主链挂了，而是验收门禁脚本落后于当前报告合同。

## 是否需要修复？

- 需要，而且已经顺手修了。
- 这类债不能留，因为它会把“系统真的通过”误报成“验收失败”。

## 精确修复方法

- 更新 [run_topic_profile_full_a_matrix.py](/Users/hujia/Desktop/RedditSignalScanner/backend/scripts/acceptance/run_topic_profile_full_a_matrix.py)
  - `report_html` marker 校验从单一现代口径：
    - `## 已分析赛道`
    - `## 决策卡片`
  - 改成兼容两种现代口径：
    - `## 已分析赛道` + `## 决策卡片`
    - `## 已分析赛道` + `## 决策风向标`
- 新增回归测试 [test_run_topic_profile_full_a_matrix.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/scripts/acceptance/test_run_topic_profile_full_a_matrix.py)
  - 锁定 `决策风向标` 章节在矩阵验收里被视为合法 Full A 输出

## x2 结果

### 第 1 轮

- 通过：`6 / 6`
- 输出文件：
  - `reports/local-acceptance/topic_profile_full_a_matrix_1774239650.json`
- 关键任务：
  - `跨境电商/PayPal` -> `f1d8b998-0a80-4efc-a231-9b1e6a7c7bc9`
  - `跨境电商/现金流` -> `c971e114-8ab4-45b1-92e3-b11856ff8e11`
  - `跨境电商/回款费率` -> `810346a2-e5db-4218-b633-d36dce6770c2`
  - `SaaS协作` -> `70356f72-a8d2-4752-90a7-f825a5a29078`
  - `家居` -> `b9728b87-1365-43fd-ba43-ae19e7798e0e`
  - `户外` -> `0ea085b0-7e10-4496-91bc-670303139a96`

### 第 2 轮

- 通过：`6 / 6`
- 输出文件：
  - `reports/local-acceptance/topic_profile_full_a_matrix_1774240016.json`
- 关键任务：
  - `跨境电商/PayPal` -> `675b86b8-1ee9-4207-8668-1747961f3102`
  - `跨境电商/现金流` -> `cf411651-f22f-4f15-9955-7303e25877a4`
  - `跨境电商/回款费率` -> `f6326068-f3a7-4e8a-a20c-f0f978dd9f17`
  - `SaaS协作` -> `9c6f6e32-78c2-49cd-8794-f44b34069e4b`
  - `家居` -> `1efee11a-f333-4738-9b1f-5398dad733d3`
  - `户外` -> `bf199faa-9e8b-4587-a4ec-be54df49454f`

## 验证

- `cd backend && ../.venv/bin/pytest tests/scripts/acceptance/test_run_topic_profile_full_a_matrix.py -q`
  - `1 passed`
- 两轮都执行：
  - `make test-e2e-live-report-cleanup-apply`
  - `make test-e2e-live-report-preflight`
  - `make test-e2e-topic-profile-matrix`
- 结果：
  - 第 1 轮 `6/6`
  - 第 2 轮 `6/6`

## 前端现场

- backend 已开启：
  - `http://127.0.0.1:8006/api/healthz`
- frontend 已开启：
  - `http://127.0.0.1:3006`
- 可直接用测试账号上前端验收：
  - `test@test.com / Test123!`

## 下一步系统性的计划是什么？

1. 让你先走真实前端验收，确认首页、输入页、报告页、标准卡入口的主观观感。
2. 如果你在前端现场发现问题，再以本轮 `x2` 稳定结果为基线，只修 UI/交付层，不再怀疑主链稳定性。
3. 你验完前端后，再决定要不要继续升到更严的 `5x` 门禁。

## 这次执行的价值是什么？

- 这次不只是“又跑通了一次”，而是把首页 6 卡的 live 稳定性推进到了：
  - `6 张卡 x 2 轮 = 12 / 12 全过`
- 同时顺手把矩阵验收脚本和当前 narrative 章节合同重新对齐，避免后面继续被假失败误导。
