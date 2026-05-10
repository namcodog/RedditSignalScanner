# phase811

- 时间：2026-04-14
- 主题：hot 真实争议占比执行方案

## 审计结果

- 当前 `hot` 首页争议图不是评论级真实 NLP 比例，而是 `hot_controversy_chart.py` 的固定桶位近似值。
- `hot` 卡具备真实落地条件：
  - 卡片里有 `source_link/source_post_id`
  - 评论表 `comments` 已可按 `source_post_id` 追样本
  - 评论标签表 `comment_llm_labels` 已存在
- 前端现有 `controversy_chart` schema 可复用，不需要重做第二套结构。

## 产出

- 设计文档：
  - `docs/superpowers/specs/2026-04-14-hot-real-controversy-ratio-design.md`
- 计划文件已同步：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## 结论

- 正确方向不是继续调图表样式，而是把 `controversy_chart` 背后的数据源从固定桶位切到真实评论样本聚合。
- 范围锁定：
  - 只做 `hot`
  - 不扩 `signal / breakdown`
  - 不动 publish plan
  - 不改前端 schema
