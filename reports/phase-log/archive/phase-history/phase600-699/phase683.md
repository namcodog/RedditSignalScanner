# phase683 - workflow dry-run makefile closure

## 本阶段完成
- 新增 workflow dry-run 服务：
  - `backend/app/services/hotpost/workflow_dry_run.py`
- 新增 workflow dry-run CLI：
  - `backend/scripts/hotpost/workflow_dry_run.py`
- 新增定向测试：
  - `backend/tests/services/hotpost/test_workflow_dry_run.py`
- 在 `Makefile` 中固化 3 个入口：
  - `hotpost-breakdown-materialize`
  - `hotpost-breakdown-overlap`
  - `hotpost-workflow-dry-run`

## 关键结果
- `workflow dry-run` 已能输出一轮完整工作流摘要：
  - 各 scope collect 数量
  - 当前 signal 队列预览
  - breakdown materialize 结果
  - 当前 write draft 队列预览
  - overlap 预警数量
- `hotpost-workflow-dry-run` 默认已收成轻量配额：
  - `HOTPOST_DRY_RUN_MAX_CANDIDATES = 1`
  - `HOTPOST_DRY_RUN_QUEUE_LIMIT = 2`
- 这样运行时不会看起来像“卡死”，更适合作为日常 SOP 验收入口

## 验证
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_workflow_dry_run.py -q`
  - `1 passed`
- `make hotpost-workflow-dry-run`
  - 返回真实 JSON：
    - `collect_results.ai-automation = 1`
    - `collect_results.ecommerce-sellers = 1`
    - `collect_results.business-growth-ops = 1`
    - `breakdown_materialize.count = 0`
    - `overlap_pair_count = 4`

## 当前边界
- 这次只固化 dry-run 入口，不改业务规则。
- dry-run 只跑到“待人工 review”边界，不做自动 publish。

## 下一步
- 继续按 SOP 跑日常产卡。
- 以后如果再固化 workflow，优先考虑触发条件和角色边界，不再扩 Makefile 为第二套业务系统。
