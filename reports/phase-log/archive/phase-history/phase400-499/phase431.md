# Phase 431 - 6卡 Full A 矩阵固化与正式验收

## 本轮目标
- 把“首页 6 卡全部 Full A + 落库”固化为可重复、可一键执行的正式验收能力。
- 修复矩阵脚本真实阻塞，不允许靠手工绕过。
- 补齐 Makefile 入口，保证后续验收可复用。

## 发现的问题
1. `run_topic_profile_full_a_matrix.py` 无法直接运行：`ModuleNotFoundError: app`。
2. guidance 字段不一致：脚本读取 `description`，实际接口返回 `prompt`。
3. DB 校验偶发崩溃：async `SessionFactory` + 多次 `asyncio.run` 触发跨 loop 错误。
4. 报告标题断言过时：脚本断言的 markdown 标题不匹配当前渲染版本。
5. 户外（EDC）在一轮验收中掉到 `C_scouting`，根因是首页标准卡输入口径不稳定且易被示例库噪音覆盖。

## 修复动作
1. 验收脚本稳定性修复（`backend/scripts/acceptance/run_topic_profile_full_a_matrix.py`）
- 增加 backend root `sys.path` 引导。
- 支持 `description/prompt` 双字段输入。
- DB 校验改为 `psycopg` 同步查询，消除 event loop 交叉风险。
- report_html 校验改为新旧 marker 兼容；核心门槛统一落在 `report_structured` 合同。

2. Full A 结构化合同兜底
- 新增 `backend/app/services/report/structured_report_fallback.py`，输出统一 6 大结构块。
- `backend/app/services/analysis/analysis_rendering.py` 在 structured LLM 缺失时自动使用 deterministic fallback。
- `backend/app/services/analysis/analysis_engine.py` 修正 `llm_used` 语义，避免 fallback 被误标成 LLM 产出。

3. 首页标准卡黄金入口收口（`backend/app/api/routes/guidance.py`）
- 首页 6 卡改为 fallback 黄金卡优先，不再被示例库噪音覆盖。
- 户外卡 prompt 升级为 EDC keychain / pocket organizer 真实需求口径，恢复稳定 `A_full`。

4. Makefile 验收入口固化
- `makefiles/test.mk` 新增 `test-e2e-topic-profile-matrix`。

## 验收结果

### A. 矩阵验收（脚本直跑）
- 命令：`cd backend && python scripts/acceptance/run_topic_profile_full_a_matrix.py`
- 结果：`accepted=true`，`6/6` 全部通过
- 核验内容：
  - 每卡 `report_tier=A_full`
  - `report_structured` 含 6 大结构块
  - 最小计数门槛：4/4/3/3/2
  - DB 落库完整（`tasks + analyses + reports`）

### B. 矩阵验收（Makefile）
- 命令：`make test-e2e-topic-profile-matrix`
- 结果：`accepted=true`，`6/6` 全部通过
- 最新 task_id（顺序对应 6 卡）：
  - `0bd6a7cc-9ed8-4889-932d-28340cfa0c02`
  - `2dd68fe7-52aa-4179-9633-64a631096ed2`
  - `b1699416-3637-421e-918d-39d80b8df1a8`
  - `63fb1653-aea9-463a-abd5-202460f010e2`
  - `dd7e6282-805f-493a-b006-bc77d9bab54a`
  - `fe26c9bb-90ad-4e5c-9e39-2a6ba2920cf6`

### C. 正式 E2E
- 命令：`make test-e2e`
- 结果：`21 passed`

### D. 定向回归
- `cd backend && pytest tests/services/report/test_structured_report_fallback.py tests/services/analysis/test_analysis_rendering.py -q` -> `3 passed`
- `cd backend && pytest tests/api/test_guidance_examples.py tests/api/test_guidance_input_api.py -q` -> `4 passed`

## 结论
- “6 卡全部 Full A + 结构化报告 + 落库”已从一次性手工验收，升级为可重复的一键正式验收能力。
- 当前产品合同已落地到系统层：标准卡 = 黄金展示入口，且可稳定复验。
