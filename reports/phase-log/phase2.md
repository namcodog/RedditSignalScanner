# 阶段二·收尾执行记录（Spec 011 / Phase 2 Closeout）

时间：$DATE_PLACEHOLDER$

## 产出清单

- backend/config/entity_dictionary/crossborder_v2_diverse.csv（100项，brands≤30，pain≥35，短语优先）
- backend/reports/local-acceptance/entity-metrics_diverse.csv（覆盖/Top10/按类覆盖）
- backend/reports/local-acceptance/metrics/metrics_diversity_diff.csv（baseline vs diverse 对比）
- backend/config/semantic_sets/crossborder_v2.1_refined.yml（Unique@500=500）
- backend/config/semantic_sets/versions/crossborder_v2.1_refined_YYYYMMDD.yml（归档）

## 指标对比摘录（最新）

- Overall 覆盖：baseline 0.8730 → diverse (ST 网格最优) ≈ 0.8462（≥0.80 达标）
- Pain 覆盖：baseline 0.5175 → diverse ≈ 0.5158（≥0.45 达标）
- Brands 限额：≤ 30（达标）
- Top10 Unique Share：baseline 0.8101 → diverse (ST 网格最优) ≈ 0.7348（较基线显著下降，距≤0.70 仍差少许）

网格搜索摘要：`backend/reports/local-acceptance/metrics/grid_search_summary.csv`（sim-max ∈ {0.45, 0.50, 0.55} × replace-n ∈ {12,16,18,20}）。

详见：`backend/reports/local-acceptance/metrics/metrics_diversity_diff.csv` 与最新 `entity-metrics_diverse.csv`。

## 四问总结

1) 发现/根因：Top10 占比高，主要由“单词型头部项”（shipping/items/commerce 等）与头部品牌（shopify/amazon 等）拉高；pain 单词（problem/issue）也贡献集中命中。

2) 定位：构建脚本仅对 features 做了弱过滤，未覆盖更多泛化单词；pain_points 未短语优先；且 features 回填后顺序导致可能挤占 pain（后续已调整为 brands+pains+features 顺序）。

3) 修复方法：
- 扩充泛化单词过滤（features）；保持“短语优先”。
- 保证 pain_points 序列在裁剪前（brands+pains+features），并设置 pain 下限（≥42）保障覆盖。
- 失败时的试点：离线“长尾短语”增广（基于本地语料正则匹配+频次），替换小部分 features 以分散 Top10 命中。

4) 下一步：若需继续压低 Top10≤0.70，可用更精细的近邻模型（sentence-transformers）筛选“非品牌、非泛化”的长尾短语，并引入更严格的短语停用词表；当前已提供 `phase2-success` 一键产出命令。

5) 效果/结果：满足红线（overall≥0.80、pain≥0.45、brands≤30），Top10 占比较 baseline 显著下降（≈ -0.08）；语义集 refined 保持 Unique@500=500 并已归档。
