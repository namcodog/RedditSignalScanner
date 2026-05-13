# Phase 584 - Rant 收最后一层表达空话，压 summary 和代表帖子解释

## 发现了什么？

前面几轮已经把：

- 脏 quote
- 假竞品
- key_comments 噪音

都压下去了。

但 live 结果还残着最后一层很伤产品感的“正确的废话”：

1. `summary` 还会写成：
   - `核心痛点`
   - `系统性问题`
   - `商业风险信号`
   这种看起来对，但 punchline 不够硬的话
2. `top_post.why_important` 还会被 LLM 写成长句空话
   - 典型就是：
     - `不是简单的吐槽`
     - `第一手挫败体验`
     - `根本性缺陷`
   - 句子不算错，但对产品经理没有新增判断价值

## 是否需要修复？

需要，而且这轮已经完成。

## 精确修复方法？

### 1. `rant` summary 改成 deterministic 的一句话判断

文件：

- `backend/app/services/hotpost/response_bundle.py`

本轮新增了一层很薄的 `rant` 表达收口：

- 不再盲信 LLM summary
- 而是根据当前真实证据里的：
  - `traffic`
  - `conversion / sales`
  - `ads / paid`
  - `random / unstable`
  这些信号，直接生成更短、更硬的一句话结论

当前能稳定收成类似：

- `TikTok内容有流量却卖不动，商家开始怀疑继续投广告到底值不值。`

### 2. `top_post.why_important` 只保留短、硬、带判断的版本

文件：

- `backend/app/services/hotpost/response_bundle.py`

本轮同时新增：

- `_build_rant_post_why()`
- `_should_replace_rant_post_why()`
- `_sanitize_rant_expression()`

现在规则是：

- 只处理 `rant`
- 只在：
  - 解释为空
  - 解释太长
  - 解释明显是空泛套话
  时，才替换为更短、更硬的本地判断

也就是说：

- `trending / opportunity` 不动
- `rant` 只把空话换掉，不继续长新链路

## 验证

### 定向测试

- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_response_bundle.py -q`
- 结果：`12 passed`

### hotpost 更宽回归

- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_runtime.py backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_hotpost_retrieval_precision.py backend/tests/services/hotpost/test_hotpost_search_workflow.py backend/tests/services/hotpost/test_hotpost_query_resolver.py backend/tests/services/hotpost/test_hotpost_keywords.py backend/tests/services/hotpost/test_evidence_collection_workflow.py backend/tests/services/hotpost/test_hotpost_mode_contract.py backend/tests/services/hotpost/test_hotpost_preview_projection.py backend/tests/services/hotpost/test_hotpost_quality_contract.py backend/tests/services/hotpost/test_hotpost_response_bundle.py backend/tests/services/hotpost/test_hotpost_report_merge.py backend/tests/services/hotpost/test_hotpost_report_export.py -q`
- 结果：`88 passed`

### 编译检查

- `python -m py_compile backend/app/services/hotpost/response_bundle.py backend/tests/services/hotpost/test_hotpost_response_bundle.py`
- 结果：通过

### live 验证

本轮已把本地 `8016` 实例切到最新代码，并验证：

- `GET /api/v1/health` -> `ok`

无缓存 live query：

- `为什么tiktok上做的内容有流量但却没有转化购买？`
- `query_id=fb6a536d-60b7-4817-ba74-e212e8cb17fd`

当前真实结果：

- `status=completed`
- `mode_state=preview`
- `summary=TikTok内容有流量却卖不动，商家开始怀疑继续投广告到底值不值。`
- `top_post.why_important=这条帖子不是在抱怨曝光少，而是在怀疑继续投广告后到底能不能成交。`

## 下一步系统性的计划是什么？

下一步不再继续补后端表达层了，直接进入小程序验收：

1. 跑 `rant` 真 query 看首屏成品感
2. 确认 `summary / 代表帖子解释 / 原话解释` 是否已经脱掉 AI 味
3. 再按验收结果决定只收页面文案，还是继续回头打结果层

## 这次执行的价值是什么？

这轮把 `rant` 最后一层“看起来像分析，其实没判断增量”的空话压下去了。

现在结果至少开始像：

- 一句话告诉你问题在哪
- 一句话告诉你这条帖子为什么值得看

而不是：

- 一长段看似正确、但读完没有动作价值的话
