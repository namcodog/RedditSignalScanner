# Phase 356 - legacy backfill 持久化从 task 壳回到服务层

## 时间
- 2026-03-17

## 本轮目标
- 收掉 `llm_label_task` 里 legacy backfill 还挂着的两个 task 私有 wrapper
- 让 `legacy backfill` 持久化继续回到服务层，不让 task 壳保留第二套持久化入口

## 发现了什么
- `backend/app/tasks/llm_label_task.py` 里还留着：
  - `_upsert_post_label(...)`
  - `_upsert_comment_label(...)`
- 它们本质上只是“搬运工”：
  - build row
  - upsert rows
- 真正更合理的归宿应该是服务层，而不是 task 壳。

## 这次做了什么
- 新增独立服务：
  - `backend/app/services/llm/legacy_label_persistence.py`
- 正式收了：
  - `upsert_legacy_post_label(...)`
  - `upsert_legacy_comment_label(...)`
- 收薄 task：
  - `backend/app/tasks/llm_label_task.py`
  - `legacy backfill` 现在直接依赖服务层持久化入口
- 新增定向测试：
  - `backend/tests/services/llm/test_legacy_label_persistence.py`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/llm/test_legacy_label_persistence.py tests/services/llm/test_legacy_label_backfill_workflow.py tests/tasks/test_llm_label_task.py -q`
- `cd backend && python -m py_compile app/services/llm/legacy_label_persistence.py app/tasks/llm_label_task.py`
- `SKIP_DB_RESET=1 make test-quality-gate`

## 结果
- `llm_label_task` 又薄了一层
- `legacy backfill` 的标签落库入口开始只有服务层真相源
- task 壳不再保留第二套 legacy 持久化写法

## 下一步
- 继续第三轮，优先专打剩余最重的几块：
  1. `facts / 报告模块`
  2. `数据采集模块`
  3. `语义 / 标签模块`
