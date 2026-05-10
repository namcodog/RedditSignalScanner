# Phase 503 - Hotpost 缺口驱动自动补证闭环（配置驱动 + 保真输出）

## 时间
- 2026-03-27

## 目标
- 对齐新约束：
  - 不做硬编码
  - 不掩盖数据真相
  - 暴露缺口后自动朝正确方向补证并重算

## 执行内容

### 1) 配置中心落地（替代硬编码）
- 新增配置文件：
  - `backend/config/hotpost_quality.yaml`
- 新增加载器：
  - `backend/app/services/hotpost/hotpost_config.py`
- 覆盖配置项：
  - query keyword extraction（pattern/min/max/stopwords）
  - quality contract limits（top_quotes/topic/trend thresholds）
  - auto remediation 策略（max rounds / mode terms / gap terms / subreddit hints）

### 2) query_resolver 改为配置驱动
- 文件：
  - `backend/app/services/hotpost/query_resolver.py`
- 变更：
  - 删除硬编码 stopwords/关键词规则
  - 改为读取 `hotpost_quality.yaml` 的 keyword extraction 配置
  - fallback/英文 query 场景下关键词提取统一走配置策略

### 3) quality_contract 保真收口
- 文件：
  - `backend/app/services/hotpost/quality_contract.py`
- 变更：
  - 保留“证据派生型补齐”（如：`top_quotes`、trending topics）
  - 去掉“无证据占位填充”路线（不再用 summary/默认模板伪装完整）
  - rant/opportunity 仅在有真实帖子证据时生成最小结构；无证据时保留缺口并降级

### 4) 自动补证闭环接入主流程
- 文件：
  - `backend/app/services/hotpost/remediation.py`（新增）
  - `backend/app/services/hotpost/search_workflow.py`
- 变更：
  - 读取 `debug_info.quality_contract_gaps`
  - gap 命中后自动生成补证计划（扩展 query parts + 社区）
  - 自动执行补证回合并重算 response
  - 比较“当前结果 vs 补证结果”质量分，自动采用更优结果
  - `api_calls` 统计包含补证回合

## 测试与验证

- 命令：
  - `cd backend && SKIP_DB_RESET=1 pytest tests/scripts/acceptance/test_run_live_hotpost_acceptance.py tests/services/hotpost/test_hotpost_query_resolver.py tests/services/hotpost/test_hotpost_quality_contract.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_response_bundle.py tests/services/hotpost/test_hotpost_schema.py tests/services/hotpost/test_hotpost_remediation.py tests/services/hotpost/test_hotpost_runtime_config.py -q`
- 结果：
  - `34 passed`

## 四问回顾
1. 发现了什么？
- 旧实现里存在“硬编码策略 + 占位回填”组合，会导致质量缺口被弱化，难以持续提质。

2. 是否需要修复？
- 需要，而且必须是系统级修复，不是局部 patch。

3. 精确修复方法？
- 用 `hotpost_quality.yaml + loader` 接管策略参数；
- quality contract 改成“证据派生优先，缺证据显式暴露”；
- 在 search workflow 接入 gap-driven auto remediation 回合。

4. 下一步系统性计划是什么？
- 跑一轮真实 `acceptance-hotpost-quality-smoke`，核对三模式在 live 数据下的自动补证命中率；
- 将补证回合命中率/收益写入 acceptance 报告，决定是否把 `max_rounds` 从 1 提升到 2。

5. 这次执行的价值是什么？达到了什么目的？
- Hotpost 从“发现缺口只能降级”升级成“发现缺口后自动补证再重算”，并且全程配置驱动、保真输出，可持续优化。
