# Phase 657 - Signal Eval Set V1 实现落地

## 结果

`signal eval set v1` 已从合同推进到真实产物，不再只是设计稿。

本轮完成了三件事：

1. 落地 real-first 构建器
   - 新增 `signal_eval_set_builder`
   - 统一把已发布 `validate` 卡和候选生成卡打包成 eval case

2. 落地导出脚本
   - 新增 `backend/scripts/evals/build_signal_eval_set_v1.py`
   - 直接导出到 `reports/evals/`

3. 跑通真实生成链
   - 已成功生成：
     - `36` 条 real case
     - `12` 条 synthetic 计划
     - `36` 条待标注 label

## 产物

已生成：

- `reports/evals/signal_eval_set_v1.jsonl`
- `reports/evals/signal_eval_labels_v1.jsonl`
- `reports/evals/signal_eval_synthetic_plan_v1.jsonl`
- `reports/evals/signal_eval_generation_failures_v1.jsonl`
- `reports/evals/signal_eval_manifest_v1.json`

manifest 结果：

- `real_count = 36`
- `synthetic_plan_count = 12`
- `generation_failure_count = 0`
- `source_scope_counts = {ai: 13, ecommerce: 11, growth: 12}`
- `origin_counts = {published_validate: 16, candidate_generated: 20}`

## 关键修复

这轮不是一次跑通的，中间补了 3 个真实边界：

1. `detail` 序列化边界
   - 生成链里的 `detail` 可能是 Pydantic 对象，也可能已经是 dict
   - 已改成统一 JSON-like dump，不再假设固定类型

2. 脚本环境优先级
   - shell 里原本带着占位 `OPENAI_API_KEY`
   - 已让脚本优先用 `backend/.env` 里的真配置覆盖占位值

3. 批量构建的显式失败记录
   - 若某条 candidate 生成失败，不再整批崩掉
   - 现在会记入 `signal_eval_generation_failures_v1.jsonl`，然后继续向前

## 当前判断

现在第一块地基已经有了：

**可以正式开始 `human review -> failure taxonomy -> judge calibration`。**

下一步不该回头继续改 collect/publish，而是该开始读这 36 条 case，做第一轮人工 error analysis。
