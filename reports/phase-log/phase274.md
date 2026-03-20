# Phase 274 - 非打标签问题收口验收

## 背景

用户要求先不继续扩大评论打标签方案，先把除打标签以外的遗留问题全部收口，再回头讨论 P0 成本债。

本轮针对上一轮验收剩余的 4 条失败做深修，重点在：

- `T1MarketReportAgent` 新旧调用协议漂移
- `ReportService._build_t1_market_report_md()` 仍按旧方式实例化 agent
- 社区治理 / 市场报告相关测试夹具未跟上最新 dataclass 签名

## 发现

1. `backend/app/services/report/t1_market_agent.py` 已经切到 DI + async 渲染，但：
   - `backend/app/services/report/report_service.py` 还在按旧的 `ReportInputs + quality_level` 模式调用
   - 三组测试也还在按旧接口调用 `render()`
2. 这不是单纯测试过时，而是**真实实现和调用方已经漂移**。
3. `test_report_service_market_mode_uses_market_template` 之前一直走“已有 HTML”分支，没有真正测到市场模板路径。
4. 社区治理历史壳测试里有一处测试构造和当前 schema 不符：
   - `community_pool.priority` 现在是字符串，不是整数

## 修复

### 1. T1 market agent 做双模式兼容

文件：
- `backend/app/services/report/t1_market_agent.py`

处理方式：
- 保留新模式：`stats_service + clustering_service + analyst` + `render_async()`
- 补回兼容模式：`ReportInputs` + `render()`
- `ReportInputs.product_description` 提供默认值 `跨境电商支付解决方案`
- 兼容模式下增加 `llm_used` 标记，并按 `report_quality_level=premium` 时尝试走一次轻量 LLM 增强
- 保持 markdown 结构稳定，满足现有市场报告测试合同

### 2. ReportService 调回兼容渲染入口

文件：
- `backend/app/services/report/report_service.py`

处理方式：
- `_build_t1_market_report_md()` 改为：
  - 继续构造 `ReportInputs`
  - 调 `agent.render()`
- 默认产品描述从 `T1 市场报告` 对齐到 `跨境电商支付解决方案`

### 3. 补齐测试夹具

文件：
- `backend/tests/services/community/test_community_governance_service.py`
- `backend/tests/services/report/test_report_service_market_mode.py`
- `backend/tests/services/analysis/test_t1_market_agent_llm.py`
- `backend/tests/services/report/test_t1_market_agent.py`
- `backend/tests/services/report/test_report_service_t1_market_md.py`

处理方式：
- 社区治理测试：
  - `priority` 改成字符串
  - `description_keywords` 对齐当前 schema
  - 历史帖子引用改成 `PostRaw` ORM 写法
- 市场报告测试：
  - 补 `total_pain / total_solution`
  - 补 `CommunityStat` 新字段
  - 补 `BrandPainCooccurrence` 新字段
  - `PainCluster` 改用 `keywords / samples`
  - 市场模板测试清空预置 HTML，确保真正覆盖模板生成路径

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/community/test_community_governance_service.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/analysis/test_t1_market_agent_llm.py \
  tests/services/report/test_t1_market_agent.py \
  tests/services/report/test_report_service_t1_market_md.py -q
```

结果：

- `15 passed`

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 结论

这轮先把“非打标签问题”收口完成了。

当前状态：

- 社区治理相关回归：绿
- T1 market 报告链回归：绿
- 主门禁：绿

也就是说，用户要求的“先把打标签之外的问题全部修好”这一段，现在已经可以算完成。

剩余要讨论的重点，就只剩评论 LLM 打标签的成本模型，不再被这些边角实现漂移干扰。
