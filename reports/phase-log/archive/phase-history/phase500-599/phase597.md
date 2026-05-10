# Phase 597 - 语义账本第一批分析读路径收尾

## 1. 发现了什么？

- 语义库上一轮已经完成了“写入闭环”，但分析主链还没有真正大面积读 `semantic_observation`。
- 这轮把 4 条高价值分析链切过去后，暴露了两个真实约束：
  1. `posts_raw` 在缺社区投影时不会留在 raw 表里，而是会被打进 `posts_quarantine`。
  2. 评论正文太弱时，即使手工传了 `business_pool='lab'`，也可能被真实规则降成 `noise`。
- 另外还抓出一个真实实现问题：
  - `ps_ratio` 对 subreddit 的处理把 `r/` 剥掉了，和现在 canonical subreddit 口径不一致。

## 2. 是否需要修复？

需要，而且这轮已经完成第一批核心修复：

- 语义主链读路径补齐
- subreddit canonical bug 修复
- 测试种数方式改成真实路径，不再手工伪造 `comments.post_id`

## 3. 精确修复方法

### 3.1 分析读路径改读 `semantic_observation`

- `backend/app/services/analysis/ps_ratio.py`
- `backend/app/services/analysis/pain_cluster.py`
- `backend/app/services/analysis/community_ranker.py`
- `backend/app/services/analysis/t1_stats.py`

当前已经完成的语义统一读取点：

- `analysis_signal_support`
- `ps_ratio`
- `pain_cluster`
- `community_ranker`
- `t1_stats` 的核心聚合：
  - `_fetch_ps_ratio_by_sub`
  - `_fetch_aspect_breakdown`
  - `_fetch_brand_pain_cooccurrence`

### 3.2 subreddit canonical 口径修复

- `ps_ratio` 改成使用 `subreddit_key(...)`
- 不再手工 `lstrip("r/")`

### 3.3 测试改成真实写入路径

以下测试不再手工塞 `comments.post_id`，统一改成：

1. 先种合法社区
2. 再写 `posts_raw`
3. 再走 `persist_comments(...)`
4. 最后补 `semantic_observation`

涉及文件：

- `backend/tests/services/analysis/test_ps_ratio.py`
- `backend/tests/services/analysis/test_pain_cluster_from_labels.py`
- `backend/tests/services/community/test_community_ranker.py`
- `backend/tests/services/analysis/test_t1_stats_semantic_observation.py`

## 4. 验证

执行：

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/analysis/test_ps_ratio.py \
  tests/services/analysis/test_pain_cluster_from_labels.py \
  tests/services/community/test_community_ranker.py \
  tests/services/analysis/test_t1_stats_semantic_observation.py \
  tests/services/analysis/test_analysis_signal_support.py -q
```

结果：

- `8 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这轮的价值不是“多改了几条 SQL”，而是把语义库从“写入闭环”推进到了“第一批分析主链也闭环”：

- 上游标签写入会刷新 `semantic_observation`
- 下游分析开始真实消费 `semantic_observation`
- 以后如果这些统计再出问题，更容易判断是语义识别问题，还是分析逻辑问题

当前结论：

- 语义库已经不再是悬空账本
- 现在它已经真实接到分析主链的第一批高价值路径上
- 下一步该继续清 report / analysis 剩余还直读旧标签表的模块
