# Phase 499 - hotpost 三模式质量合同落地（P0/P3 第一批）

## 时间
- 2026-03-27

## 目标
- 按提质 tasks list 先落第一批可执行改动：
  - 三模式统一质量合同（后端）
  - 结果兜底 + 缺项降级机制
  - acceptance 脚本模式级校验
  - 三模式质量 smoke 入口

## 执行内容

### 1) 新增独立质量合同模块（低耦合）
- 新文件：
  - `backend/app/services/hotpost/quality_contract.py`
- 核心能力：
  - `apply_hotpost_quality_contract(...)`
  - 公共合同兜底：
    - `top_quotes` 自动回填（从证据帖/评论抽）
    - `next_steps.suggested_keywords` 自动回填
  - 模式专属兜底：
    - `trending`：无 topics 时自动回填最小 topics + trend + evidence
    - `rant`：无 pain_points 时自动回填最小主痛点
    - `opportunity`：无 unmet_needs/market_opportunity 时自动回填最小结构
  - 合同缺项检测：
    - 输出 `gaps` + `notes`

### 2) 接入 response bundle（高内聚）
- 文件：
  - `backend/app/services/hotpost/response_bundle.py`
- 接入点：
  - 在最终返回 `HotpostSearchResponse` 前统一调用合同模块
- 行为：
  - 将合同缺项写入 `debug_info.quality_contract_gaps`
  - 缺项映射为 `degraded_reasons`（`quality_contract:*`）
  - 当原状态是 `completed` 且合同仍缺项时，自动降级为 `degraded`

### 3) 扩展 debug schema
- 文件：
  - `backend/app/schemas/hotpost.py`
- 新增：
  - `HotpostDebugInfo.quality_contract_gaps: list[str]`

### 4) 强化 hotpost acceptance 脚本
- 文件：
  - `backend/scripts/acceptance/run_live_hotpost_acceptance.py`
- 在原有通用校验上新增模式级校验：
  - 所有模式：必须有 `top_quotes`
  - trending：必须有 `topics + time_trend + topic evidence`
  - rant：必须有 `pain_points` 且能提取用户原话
  - opportunity：必须有 `unmet_needs + market_opportunity`

### 5) Makefile 增加三模式质量 smoke
- 文件：
  - `makefiles/test.mk`
- 新增目标：
  - `acceptance-hotpost-quality-smoke`
- 行为：
  - 依次跑 `trending / rant / opportunity` 三条 fresh query 验证

## 测试与验证

### 后端定向测试
- 命令：
  - `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_quality_contract.py tests/services/hotpost/test_hotpost_response_bundle.py tests/services/hotpost/test_hotpost_schema.py tests/scripts/acceptance/test_run_live_hotpost_acceptance.py -q`
- 结果：
  - `24 passed`

### Makefile 入口检查
- 命令：
  - `make -n acceptance-hotpost-quality-smoke`
- 结果：
  - 三模式命令展开正确（trending/rant/opportunity）

## 四问回顾
1. 发现了什么？
- 之前 hotpost 主要有“能跑出结果但质量形态不稳定”的风险，尤其是模式关键块缺失时不易被及时发现。

2. 是否需要修复？
- 需要。否则三模式会长期出现“偶发结果看起来不值钱”的体验波动。

3. 精确修复方法？
- 抽离独立质量合同模块并在 response_bundle 统一接入；
- 缺项直接标记到 `debug_info` 并触发降级；
- acceptance 增加模式级验收条件；
- Makefile 补三模式 smoke 入口。

4. 下一步系统性计划是什么？
- 下一轮进入 P1：
  - 查询扩展与社区扩展提质
  - 证据排序从“热度优先”升级到“价值优先”
- 再下一轮进入 P2：
  - 分别优化 `trending/rant/opportunity` 的专项判断质量。

5. 这次执行的价值是什么？
- 三模式输出从“能返回”升级为“有合同约束、缺项可观测、验收可自动化”，是后续持续提质的稳定底座。
