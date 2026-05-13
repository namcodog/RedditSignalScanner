# Phase 583 - Rant 继续压 key_comments 噪音，并让次级 quote 不再复读解释

## 发现了什么？

Phase 582 之后，`rant` 的结果已经少了两层假内容，但 live 还剩两个尾巴：

1. `key_comments` 里还会带上 AutoModerator
   - 虽然小程序当前没直接展示
   - 但这条脏数据留在 payload 里，后面很容易再次污染页面
2. `top_quotes[1]` 的解释还会和第一条复读
   - 典型就是：
     - 第一条讲“自然流量 vs 广告转化”
     - 第二条讲“pay to play / gmv max”
   - 结果系统还是给同一句解释

这也是一种“正确的废话”：

- 句子没错
- 但没抓住这条原话自己的增量

## 是否需要修复？

需要，而且这轮已经完成。

## 精确修复方法？

### 1. `key_comments` 统一按去噪规则筛选

文件：

- `backend/app/services/hotpost/response_bundle.py`

本轮新增：

- `_select_key_comments()`

现在规则是：

- 按 score 排序
- 跳过 bot / AutoModerator / Discord 类噪音
- 去重后最多保留 5 条

也就是说：

- `key_comments` 终于和其他 quote 选择开始按同一套判断工作

### 2. `pay to play` 类 quote 单独解释

文件：

- `backend/app/services/hotpost/quality_contract.py`

本轮新增：

- `_build_rant_quote_why_important()` 里优先识别：
  - `pay to play`
  - `gmv max`

现在这类原话不再复读“自然流量 vs 广告”那句，而会明确解释成：

- 平台可能正在逼商家持续买量
- 转化越来越依赖付费

## 验证

### 定向测试

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_quality_contract.py tests/services/hotpost/test_hotpost_response_bundle.py -q`
- 结果：`21 passed`

### hotpost 更宽回归

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_runtime.py tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_hotpost_retrieval_precision.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_query_resolver.py tests/services/hotpost/test_hotpost_keywords.py tests/services/hotpost/test_evidence_collection_workflow.py tests/services/hotpost/test_hotpost_mode_contract.py tests/services/hotpost/test_hotpost_preview_projection.py tests/services/hotpost/test_hotpost_quality_contract.py tests/services/hotpost/test_hotpost_response_bundle.py tests/services/hotpost/test_hotpost_report_merge.py tests/services/hotpost/test_hotpost_report_export.py -q`
- 结果：`86 passed`

### 编译检查

- `python -m py_compile backend/app/services/hotpost/quality_contract.py backend/app/services/hotpost/response_bundle.py`
- 结果：通过

### live 无缓存验证

验证 query：

- `为什么tiktok上做的内容有流量但却没有转化购买？`

最终 live 结果：

- `query_id=d938de63-6d75-4cec-b3e9-bc0725534e0c`
- `status=completed`
- `key_comments` 现在只剩真实用户评论：
  - 不再包含 AutoModerator
- `top_quotes[1].why_important` 现在变成：
  - `这句原话不是在抱怨流量少，而是在担心平台最后会逼着商家持续买量，转化会越来越依赖付费。`

## 下一步系统性的计划是什么？

下一步继续只打 `rant` 的表达层：

1. 收 summary 的 AI 味
2. 收 `top_post.why_important` 的长度和废话率
3. 再做 1 轮 live，对比小程序首屏成品感

## 这次执行的价值是什么？

这轮的价值是：

- `key_comments` 不再埋着 bot 噪音
- 次级 quote 不再复读第一条解释

也就是说，`rant` 不只是“少了脏东西”，而是开始让每条证据都更像它自己。
