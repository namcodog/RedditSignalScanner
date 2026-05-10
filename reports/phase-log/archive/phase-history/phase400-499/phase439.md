# Phase 439 - 残留清理收尾

## 本轮目标

把上一轮留下的两个真实残留收掉：

1. `canonical_report_json` 已补齐，但 DB 原始 `report_structured` 还没同步回写
2. `saas_collaboration_v1` live 重跑会掉到 `C_scouting`

## 发现

### 1. DB / API 双真相

- 原因不在分析任务本身，而在 `/api/report/:taskId` 的请求链：
  - 报告接口在运行时会补齐 sparse structured output
  - 但补齐后的 canonical 没有回写到 `analyses.sources.report_structured`
- 结果就是：
  - API 对外是 4 个战场
  - DB 原始 JSON 还可能只有 2 或 3 个战场

### 2. saas live 掉级根因

- 不是 prompt 漂了，是 Dev 库缺样本。
- `saas_collaboration_v1` 当时 live 跑出的 `facts_slice` 显示：
  - 只覆盖 6 帖 / 0 评论
  - 还混入 `r/ecommerce / r/stripe / r/artificial` 这类噪音样本
  - `analysis_blocked=insufficient_samples`
- 进一步对比金库与 Dev 库发现：
  - Dev 库里 `r/saas / r/startups / r/entrepreneur` 对应帖子几乎为空
  - 金库里这三个社区有足够样本

## 修复

### 1. 持久化同源

- 新增仓储回写方法：
  - `backend/app/repositories/report_repository.py`
- 报告请求工作流新增持久化钩子：
  - `backend/app/services/report/report_request_workflow.py`
- 运行时工厂接通该钩子：
  - `backend/app/services/report/report_runtime_factory.py`
  - `backend/app/services/report/report_runtime.py`

结果：

- `/api/report/:taskId` 输出的 canonical structured 会回写到 DB
- 现在同一次报告请求后，DB 与 API 的 `report_structured` 结构一致

### 2. saas 样本补齐

- 按“金库 -> Dev，仅复制相关任务数据”的规则，
  只把 `saas_collaboration_v1` 相关 3 个社区样本补到 Dev：
  - `r/saas`
  - `r/startups`
  - `r/entrepreneur`
- 实际补入：
  - authors: `2191`
  - posts_raw: `2684`

## 验收

### 持久化同源

- 访问 `task_id=234e2015-7ae2-4da7-8acc-ffc1151d80c4` 的报告接口后复查：
  - API `battlefields=4`
  - DB `battlefields=4`
  - DB `decision_cards=4`

### saas live

- `run_live_report_acceptance.py`
- 输入：
  - `topic_profile_id=saas_collaboration_v1`
  - prompt = 远程团队项目管理与协作工具，解决跨时区沟通、任务拆解与进度跟踪问题，关注 Notion/Asana/Trello 的使用痛点与替代机会。
- 结果：
  - `attempt=1`
  - `report_tier=A_full`
  - `analysis_blocked=""`
  - `result_url=http://127.0.0.1:3006/report/234e2015-7ae2-4da7-8acc-ffc1151d80c4`

### 回归

- `pytest backend/tests/services/report/test_report_request_workflow.py backend/tests/services/report/test_report_request_deps_factory.py backend/tests/services/report/test_report_assembly_workflow.py -q`
- 结果：`6 passed`

## 当前状态

- 上一轮明确提出的两个残留都已清掉
- 首页标准卡固定快照继续可用
- `saas_collaboration_v1` live 也恢复到可验收状态

## 下一步

- 后续再单独和产品口径对齐前端交互，不再混着处理工程残留
