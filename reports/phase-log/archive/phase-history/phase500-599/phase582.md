# Phase 582 - Rant 去掉“正确的废话”里的脏原话与假竞品

## 发现了什么？

这轮 live 把两类很典型的“正确但没用”的内容暴露得很清楚：

1. `top_quotes` 已经干净了，但 `pain_points.evidence[].key_quote` 和 markdown 报告里的“代表性帖子”还在抄第一条评论。
   - 结果就是 AutoModerator 的 Discord 邀请会混进正式分析。
   - 这不是数据没拿到，而是系统内部有两套 quote 选择逻辑。
2. `competitor_mentions` 还会把 `sales / organic` 这类普通词当成“竞品/替代”。
   - 这也是典型的正确废话：
     - 词本身没错
     - 但对用户判断没有价值

## 是否需要修复？

需要，而且这轮已经完成。

## 精确修复方法？

### 1. 把“选代表原话”收成同一套轻逻辑

文件：

- `backend/app/services/hotpost/evidence_focus.py`
- `backend/app/services/hotpost/quality_contract.py`
- `backend/app/services/hotpost/report_llm.py`
- `backend/app/services/hotpost/report_export.py`

本轮调整：

- 新增 `extract_key_quote_from_comments()`
- `is_noise_comment()` 改成同时支持 schema 对象和 dict
- `quality_contract._first_post_quote()` 不再直接抄第一条评论
- `report_llm._build_evidence_from_post()` 不再把第一条评论硬塞进 evidence
- `report_export` 的 `代表性帖子` 也改成只取真实用户原话

效果是：

- `top_quotes`
- `pain_points.evidence[].key_quote`
- markdown 报告里的 `代表性帖子`

现在终于开始走同一套 quote 选择规则，不再一处干净、一处还在抄机器人。

### 2. `top_quotes` 不再让 fallback 反客为主

文件：

- `backend/app/services/hotpost/quality_contract.py`

本轮调整：

- `_merge_top_quotes()` 不再把当前 `top_quotes` 和 fallback quotes 按分数重排
- 改成：
  - 当前 `top_quotes` 先保留顺序
  - fallback 只负责补位
  - duplicate 仍保留更强版本

这解决了一个隐蔽问题：

- 上游已经挑好的 quote
- 会被 fallback quote 挤到后面
- 于是 `why_important` 看起来像“又丢了”

### 3. `rant` 的 quote 解释只保留有判断增量的版本

文件：

- `backend/app/services/hotpost/quality_contract.py`

本轮调整：

- 新增 `_quote_why_is_generic()`
- 新增 `_build_rant_quote_why_important()`
- 当前规则改成：
  - 已有具体判断就保留
  - 只有泛话术时，用具体判断替换
  - 没有真实判断信号时，直接留空

也就是说：

- 不再为了“每条都像分析”去硬写模板句

### 4. `competitor_mentions` 只保留像真实对象的东西

文件：

- `backend/app/services/hotpost/response_bundle.py`

本轮调整：

- 新增 `_sanitize_competitor_mentions()`
- `rant` 下的 `competitor_mentions` 现在会：
  - 过滤 query/domain/problem 自身词
  - 过滤普通业务词：
    - `sales`
    - `organic`
    - `traffic`
    - `conversion`
    - `purchase`
    - `ads`
  - 统一要求至少 `2` 次 mention 才允许上屏

这一步的核心原则很简单：

- 没有稳定替代对象，就不要假装有“竞品分析”

## 验证

### 定向测试

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_quality_contract.py tests/services/hotpost/test_hotpost_report_merge.py tests/services/hotpost/test_hotpost_report_export.py tests/services/hotpost/test_hotpost_response_bundle.py -q`
- 结果：`25 passed`

### 更宽 hotpost 回归

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_runtime.py tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_hotpost_retrieval_precision.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_query_resolver.py tests/services/hotpost/test_hotpost_keywords.py tests/services/hotpost/test_evidence_collection_workflow.py tests/services/hotpost/test_hotpost_mode_contract.py tests/services/hotpost/test_hotpost_preview_projection.py tests/services/hotpost/test_hotpost_quality_contract.py tests/services/hotpost/test_hotpost_response_bundle.py tests/services/hotpost/test_hotpost_report_merge.py tests/services/hotpost/test_hotpost_report_export.py -q`
- 结果：`84 passed`

### 编译检查

- `python -m py_compile backend/app/services/hotpost/evidence_focus.py backend/app/services/hotpost/quality_contract.py backend/app/services/hotpost/report_llm.py backend/app/services/hotpost/report_export.py backend/app/services/hotpost/response_bundle.py`
- 结果：通过

### live 无缓存验证

验证 query：

- `为什么tiktok上做的内容有流量但却没有转化购买？`

验证方式：

- 清 `redis://localhost:6379/5`
  - `hotpost:query_translate:*`
  - `reddit_hot:rant:*`
- 使用 `8006` 当前实例

最终 live 结果：

- `query_id=d25ba943-fd5c-4807-8686-c5e274a80d68`
- `status=completed`
- `mode_state=preview`
- `summary=TikTok内容有流量但广告转化效果不明显，导致卖家更依赖自然流量出单，对付费广告的投入产出比感到困惑。`
- `pain_points[0].evidence[0].key_quote` 已变成真实用户原话，不再是 Discord/AutoModerator
- markdown 报告的 `代表性帖子` 已不再抄 bot 评论
- `competitor_mentions=[]`
- `migration_intent.destinations=[]`
- `top_quotes[0].why_important` 已非空且为具体判断

## 下一步系统性的计划是什么？

下一步继续只打 `rant` 的真实价值，不回头长新层：

1. 继续收 `top_quotes[1..]` 的解释质量
   - 避免不同原话复用同一句泛判断
2. 清掉 `key_comments` 里的 AutoModerator 噪音
3. 继续收 summary / why_important 的表达去 AI 味

## 这次执行的价值是什么？

这轮的价值不是“字段更多了”，而是系统又少了两层最伤产品感的假内容：

1. 机器人原话冒充证据
2. 普通问题词冒充竞品/替代

也就是说，`rant` 现在离“轻量，但真的有判断价值”又近了一步。
