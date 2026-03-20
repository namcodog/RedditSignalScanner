# Phase 328 - 第三轮：hotpost 模块继续拆 LLM 摘要工作流

## 1. 发现了什么？

这次第三轮顺手继续打了 `hotpost` 模块里一条还挂在主服务里的重逻辑：

- LLM 摘要生成

之前 `HotpostService._maybe_llm_summary(...)` 还在自己背：

- 低置信度短路
- 缺 key 短路
- fallback summary 生成
- prompt 拼装
- client 调用
- 空输出回退

大白话说：

- `HotpostService` 还在一边编排搜索，一边亲手跑摘要 LLM 子流程。

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库表结构，没有新 migration。  
改的是 `hotpost` 模块里摘要 workflow 的边界、主服务职责和测试门禁。

## 3. 精确修复方法？

这次做了三件事：

- 新增独立 workflow：
  - `backend/app/services/hotpost/summary_workflow.py`
  - 正式收了：
    - `HotpostSummaryWorkflowInput`
    - `HotpostSummaryWorkflowDeps`
    - `build_hotpost_fallback_summary(...)`
    - `generate_hotpost_summary(...)`

- 把 `backend/app/services/hotpost/service.py` 收成薄委托：
  - `_maybe_llm_summary(...)` 现在只负责组装 workflow 输入和 deps
  - `_fallback_summary(...)` 也改成委托给公共 fallback builder

- 先补 workflow 测试，再用旧 hotpost 摘要测试锁兼容：
  - `backend/tests/services/hotpost/test_hotpost_summary_workflow.py`
  - 覆盖：
    - fallback summary 合同稳定
    - 低置信度会走 fallback
    - LLM 成功时返回 `source=\"llm\"`

## 4. 验证结果

- 定向回归：
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost/test_hotpost_summary_workflow.py tests/services/hotpost/test_hotpost_summary.py tests/services/hotpost/test_hotpost_response_bundle.py -q`
  - `9 passed`

- 语法自检：
  - `python -m py_compile backend/app/services/hotpost/summary_workflow.py backend/app/services/hotpost/service.py backend/tests/services/hotpost/test_hotpost_summary_workflow.py`
  - 通过

- 主门禁：
  - `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这次最值钱的地方很直接：

- `hotpost` 模块里“摘要怎么生成、什么时候该回退”现在开始只有一个正式真相源了
- 主服务继续变薄
- fallback 和 LLM 输出的合同更稳定

一句大白话收口：

- 这刀把 `hotpost` 模块里还挂在主服务里的摘要 LLM 子流程拆开了，第三轮又顺了一层。
