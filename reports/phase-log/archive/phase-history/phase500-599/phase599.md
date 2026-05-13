# Phase 599 - 语义账本继续收尾：saturation_matrix 切到 semantic_observation

## 1. 发现了什么？

继续扫语义库剩余旧读路径后，发现 `saturation_matrix` 仍然直接依赖 `content_entities`：

- 品牌饱和度矩阵还是从 `content_entities(entity_type='brand')` 统计
- 这会让 report 侧的竞品饱和度继续绕开统一语义账本

同时 `analysis_engine` 里的说明文字也还停留在旧口径：

- 注释仍写 `content_labels/content_entities`
- 日志也仍写旧表名

## 2. 是否需要修复？

需要。

这条链虽然不像 `candidate_extractor` 那样显眼，但它直接影响：

- 竞品饱和度判断
- 机会窗口识别
- 报告里的竞争格局输入

如果不切，report 侧仍然会保留一块旧语义依赖。

## 3. 精确修复方法？

### 3.1 `saturation_matrix`

文件：

- `backend/app/services/analysis/saturation_matrix.py`

修复：

- 改成从 `semantic_observation` 读取品牌观测：
  - `content_type='post'`
  - `observation_type='content_entity'`
  - `label_key='brand'`
- 不再直接读 `content_entities`
- 社区 canonical 统一改走 `subreddit_key(...)`

### 3.2 `analysis_engine`

文件：

- `backend/app/services/analysis/analysis_engine.py`

修复：

- 把语义信号提取的注释和日志口径改成 `semantic_observation`
- 避免代码真实行为已经切了，但注释/日志还在说旧表

### 3.3 测试

文件：

- `backend/tests/services/analysis/test_saturation_matrix.py`

修复：

- 测试种数改成写 `semantic_observation`
- 不再写 `content_entities`
- 同时把测试清理改成显式 `async_truncate_test_tables`
- 顺手修掉旧测试社区名不符合当前 `posts_hot.subreddit` 约束的问题

## 4. 验证

执行：

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/analysis/test_saturation_matrix.py \
  tests/services/semantic/test_candidate_extractor.py \
  tests/services/analysis/test_t1_clustering_semantic_observation.py \
  tests/services/analysis/test_t1_stats_semantic_observation.py \
  tests/services/analysis/test_ps_ratio.py \
  tests/services/analysis/test_analysis_signal_support.py -q
```

结果：

- `14 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这轮的价值是把 report 侧一个高影响统计口径也拉进了统一语义账本：

- 品牌饱和度不再依赖旧 `content_entities`
- 竞品机会窗口判断也开始读 `semantic_observation`
- 语义读侧剩余高影响旧路径进一步收窄到：
  - `analysis_engine` 内部部分聚合路径

当前结论：

- 语义库现在已经不只是“候选词/聚类/统计摘要”接上
- 竞品饱和度这条 report 侧关键输入也接上了
- 下一步应该继续收 `analysis_engine` 内部剩余旧聚合，再回到 live 报告主链看真实提分
