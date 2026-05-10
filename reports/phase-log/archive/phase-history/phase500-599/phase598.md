# Phase 598 - 语义账本继续收尾：candidate_extractor / t1_clustering 切到 semantic_observation

## 1. 发现了什么？

这轮继续扫语义库旧读路径，发现还有两条高影响链路没切干净：

1. `candidate_extractor.extract_from_db(...)`
   - 还在直接 `JOIN content_labels`
   - 会把旧标签表重新带回语义候选词入口
2. `t1_clustering._fetch_pain_comments(...)`
   - 还在直接读 `content_labels`
   - 还是“prototype 时代”的无 `subs` 过滤口径

这说明语义库虽然已经完成了写入闭环，但读侧仍有残留旧口径会回流进分析链。

## 2. 是否需要修复？

需要。

这两条都属于高影响入口：

- `candidate_extractor` 会影响候选词生成
- `t1_clustering` 会影响 T1 痛点聚类输入

如果不切，后面语义主链仍然会被旧 `content_labels` 绕回来。

## 3. 精确修复方法？

### 3.1 `candidate_extractor`

文件：

- `backend/app/services/semantic/candidate_extractor.py`

修复：

- 改成从 `semantic_observation` 读取 `content_label/pain`
- 不再直接 `JOIN content_labels`
- 用 `SELECT DISTINCT` 去掉同一评论多条 pain 观测带来的重复

### 3.2 `t1_clustering`

文件：

- `backend/app/services/analysis/t1_clustering.py`

修复：

- `_fetch_pain_comments(...)` 改成读取 `semantic_observation`
- `aspect` 改从 `so.label_value` 读取
- 把 subreddit 过滤重新接回，并统一走 `subreddit_key(...)`
- 不再让 prototype 时代的无过滤逻辑继续漂在主链里

### 3.3 测试

文件：

- `backend/tests/services/semantic/test_candidate_extractor.py`
- `backend/tests/services/analysis/test_t1_clustering_semantic_observation.py`

补充验证：

- `candidate_extractor` SQL 里必须出现 `semantic_observation`
- SQL 里不允许再出现 `content_labels`
- `t1_clustering` 的 pain 评论抓取必须走 `semantic_observation`
- subreddit 参数必须 canonical 成 `r/...`

## 4. 验证

执行：

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/semantic/test_candidate_extractor.py \
  tests/services/analysis/test_t1_clustering_semantic_observation.py \
  tests/services/analysis/test_pain_cluster_from_labels.py \
  tests/services/analysis/test_ps_ratio.py \
  tests/services/analysis/test_t1_stats_semantic_observation.py \
  tests/services/analysis/test_analysis_signal_support.py -q
```

结果：

- `12 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这轮的价值是把语义库继续从“第一批读侧闭环”推向“更完整的分析入口闭环”：

- 候选词入口不再依赖旧 `content_labels`
- T1 痛点聚类入口也不再依赖旧 `content_labels`
- 现在剩余还没完全切掉的语义旧读路径，已经进一步收窄到：
  - `saturation_matrix`
  - `analysis_engine` 内部部分聚合路径

当前结论：

- 语义库已经不是“只有写入接上”
- 现在高影响分析入口也在持续切到 `semantic_observation`
- 下一步应该继续扫剩余 report / analysis 模块，把最后几条旧读路径收掉
