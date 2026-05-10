# Phase 480: 八领域横向 Live 验证与洞察合同断点定位

## 本轮目标

- 在主链重构跌破 `3000` 行之后，做 8 个领域的横向 live 验证。
- 验证 warzone 路由、insights 落库、report 装配三层是否对齐。
- 找出为什么多领域下 `Full A` 仍然漂移。

## 本轮执行

### 1. 起隔离 live runtime

- 使用 `backend/scripts/acceptance/manage_live_runtime.py` 启动隔离 runtime
- 端口：`8016`
- 确认：
  - backend 单实例
  - `analysis-live` 单实例
  - `bulk-live` 单实例
  - 无重复 worker

### 2. 跑第一轮 8 领域横向 live

- 结果文件：
  - `backend/reports/local-acceptance/warzone_live_matrix_1774428217.json`
- 结果摘要：
  - `3/8` 首轮 `A_full`
  - `5/8` 未过线
- 关键发现：
  - `open_topic_route` 在 `analyses.sources.analysis_diagnostics` 里是存在的
  - 但 `/api/report` 返回的 payload 没把诊断字段带下来
  - 更深一层看，`analyses.insights` 里 `pain_points / top_communities / drivers` 普遍缺失或为空
  - 报告层只能 fallback，出现：
    - `关键痛点 2/3`
    - 空 `target_communities`
    - 英文噪音机会

### 3. 修 insight synthesis 通用根因

- 修改：
  - `backend/app/services/analysis/insight_synthesis.py`
- 修复内容：
  - 英文 pain/opportunity 不再因为没有 CJK 直接被整条吞掉
  - 新增中文业务脚手架：
    - pain -> `高频抱怨：...`
    - opportunity -> `产品机会：...`
  - `finalize_insights_summary(...)` 正式落库：
    - `insights.top_communities`
    - `insights.drivers`
- 新增测试：
  - `backend/tests/services/analysis/test_insight_synthesis.py`
- 验证：
  - `5 passed`
  - 相关 analysis 主链回归 `12 passed`

### 4. 重新起 runtime 后再次横向 live

- 中途发现一个真实执行问题：
  - 第二轮 rerun 仍在使用旧 runtime 进程
  - 结果不能用于判断新修复是否生效
- 因此执行：
  - 停止 runtime
  - 重新启动 runtime
  - 重新跑横向验证

### 5. 修 report payload schema 断点

- 新 runtime 下的 live 暴露出新的硬断点：
  - `/api/report` 返回 `HTTP 500 Failed to validate analysis payload`
- 日志明确显示：
  - `insights.drivers` 是额外字段
  - `insights.top_communities` 是额外字段
- 根因：
  - `AnalysisRead / InsightsPayload` 的读取合同没有同步升级
- 修改：
  - `backend/app/schemas/analysis.py`
  - `backend/tests/services/report/test_analysis_payload_loader.py`
  - `backend/tests/schemas/test_schemas.py`
- 新增合同：
  - `InsightsPayload.top_communities: list[str]`
  - `InsightsPayload.drivers: list[DriverSignal]`
- 验证：
  - `pytest tests/services/report/test_analysis_payload_loader.py tests/schemas/test_schemas.py -q`
  - `15 passed`

### 6. 最终有效 8 领域 live 结果

- 最终结果文件：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774430723.json`

#### 逐领域结果

- `Ecommerce_Business`
  - `task_id = 0c297035-a6d9-4ea2-822b-73e88e152e16`
  - `A_full`
- `Home_Lifestyle`
  - `task_id = cdb9737d-064f-4190-afdc-b28c6de926a7`
  - `C_scouting`
- `Tools_EDC`
  - `task_id = 6394e234-7808-4591-8d81-8d9658c70f86`
  - `B_trimmed`
- `AI_Workflow`
  - `task_id = eb18a656-4b35-4eba-8506-95080ff7d9bc`
  - `B_trimmed`
- `Family_Parenting`
  - `task_id = c05d3941-0303-442a-9137-55523ef3bed8`
  - `C_scouting`
- `Food_Coffee_Lifestyle`
  - `task_id = 24c0bd08-fa07-41be-a6db-e162d3ecf9c6`
  - `B_trimmed`
- `Minimal_Outdoor`
  - `task_id = f9154b93-6a9d-4a78-8099-e60577223d2a`
  - `B_trimmed`
- `Frugal_Living`
  - `task_id = 90489884-d450-432c-b053-2a84483c891f`
  - `B_trimmed`

## 关键结论

### 已确认修复/成立

- `analysis_engine.py` 保持在 `2680` 行，未反弹
- `open_topic_route` 的 8 领域路由方向是成立的
- 新增 `top_communities / drivers` 后，report schema 断点已被修掉
- runtime 现场已能保持单实例、可复验

### 仍然存在的系统级问题

1. 多数领域虽然不再直接 500，但洞察质量仍然不足
   - 典型表现：
     - `B_trimmed`
     - `C_scouting`
     - `关键痛点 3`
     - `target_communities` 仍为空

2. 新增的中文脚手架虽然防止了整条 signal 被吞掉，但当前仍偏“兜底态”
   - 典型表现：
     - `高频抱怨：...` 后面仍是英文原始句
   - 说明当前还没到最终产品验收线，只是把“空洞察”拉回到“有洞察但还不够业务化”

3. `top_communities` 已进入 analysis 合同，但 canonical/report 层还没有把它真正转成 `target_communities`
   - 这说明：
     - schema 已对齐
     - canonical 组装仍未完全吃到新洞察面

4. `Home_Lifestyle / Family_Parenting` 掉到 `C_scouting`
   - 当前更像样本量和评论深度不足
   - 不是纯 report 装配问题

## 本轮价值

- 这轮没有停在“代码重构完成”的幻觉上，而是用 8 领域真实 live 把主链剩余问题继续打穿了
- 当前已经把问题从“路线不清楚”收敛成更明确的两层：
  - `Insight -> canonical target_communities` 还没完全接通
  - `多领域 query/evidence` 的深度仍然不够，导致 `B_trimmed / C_scouting`

## 下一步

1. 修 canonical/report 层，把 `insights.top_communities` 真正映射到 `canonical_report_json.target_communities`
2. 继续改善 pain/opportunity 的通用中文转译，避免 `高频抱怨：英文原句` 这种半成品表达
3. 对 `Home_Lifestyle / Family_Parenting` 优先打样本深度和 query focus
4. 再跑一轮 8 领域横向 live，目标不是只看是否不报错，而是看：
   - `A_full` 数量是否继续上升
   - `target_communities` 是否回归
   - `关键痛点 2/3` 是否继续减少
