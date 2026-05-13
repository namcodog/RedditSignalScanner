# Phase 581 - Rant 补本地 why_important，并给“有流量但卖不动”问题帖更高排序权重

## 发现了什么？

在 Phase 580 之后，`rant` 的首屏 quote 已经干净很多了，但又暴露了两个判断层问题：

1. 泛讨论高热帖仍可能压过更明确的“有流量但卖不动”问题帖
2. 本地链路里的 `top_post.why_important` 默认还是空的
   - 太依赖 LLM 后补
   - 一旦 LLM 没给，这条证据就只剩“为什么相关”，没有“为什么重要”

## 是否需要修复？

需要，而且这轮已经完成。

## 精确修复方法

### 1. 给 `rant` 加一层轻量问题聚焦分

文件：

- `backend/app/services/hotpost/evidence_collection_workflow.py`

本轮新增：

- `_rant_focus_score()`

额外加权的情况包括：

- `traffic + loss`
- `ads + loss`
- `no sales`
- `no conversions`
- `nobody buys`

目标不是加新框架，而是让更像“问题本身”的帖子别再被泛讨论帖压下去。

### 2. 给 `rant` 增加本地 `why_important`

文件：

- `backend/app/services/hotpost/evidence_collection_workflow.py`

本轮新增：

- `_build_rant_why_important()`

当前会优先说明：

- 这是成交层问题，不只是流量波动
- 这不是泛抱怨，而是经营判断信号
- 如果评论里有人继续接这个问题，说明它更像重复出现的困扰

## 验证

### 定向测试

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_evidence_collection_workflow.py -k 'specific_rant_problem or why_important_for_conversion_loss' -q`
- 结果：`2 passed`

### hotpost 定向回归

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_runtime.py tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_hotpost_retrieval_precision.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_query_resolver.py tests/services/hotpost/test_hotpost_keywords.py tests/services/hotpost/test_evidence_collection_workflow.py tests/services/hotpost/test_hotpost_mode_contract.py tests/services/hotpost/test_hotpost_preview_projection.py tests/services/hotpost/test_hotpost_quality_contract.py -q`
- 结果：`66 passed`

### 编译检查

- `python -m py_compile backend/app/services/hotpost/evidence_collection_workflow.py backend/tests/services/hotpost/test_evidence_collection_workflow.py`
- 结果：通过

### live 无缓存验证

验证 query：

- `为什么tiktok上做的内容有流量但却没有转化购买？`

验证方式：

- 清 `redis://localhost:6379/5`
  - `hotpost:query_translate:*`
  - `reddit_hot:rant:*`
- 使用 `8006` 当前热更新实例

最终 live 结果：

- `status="completed"`
- `mode_state="preview"`
- `summary="TikTok内容有流量但广告转化差，用户发现大部分销售来自自然流量，对付费广告的价值产生怀疑。"`
- `top_post.why_important` 已不再为空
- `top_quotes` 继续保持干净

## 这次执行的价值是什么？

这轮的价值是：

- `rant` 不再只是“抓到证据”
- 开始具备“为什么这条证据重要”的本地判断骨架

也就是说，系统现在没那么依赖 LLM 临场补话了。

## 下一步系统性的计划是什么？

下一步继续只打最影响成品感的三块：

1. 补 `top_quotes[].why_important`
2. 继续收紧代表帖子排序
3. 继续削表达层的 AI 味
