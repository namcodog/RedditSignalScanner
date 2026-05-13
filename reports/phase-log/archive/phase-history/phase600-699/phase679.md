# Phase 679 - breakdown review/taxonomy/judge v1 落地

## 发现了什么

`breakdown skill optimization` 的前三步已经全部从合同推进成了真实产物：

1. `breakdown review packet v1`
2. `breakdown failure taxonomy v1`
3. `breakdown judge v1`

这意味着拆解线现在也和之前的 signal 一样，有了完整的前半段闭环：

`eval set -> human review packet -> taxonomy -> judge`

而且这次不是只写了几份文档，judge 已经在完整 `breakdown eval set v1` 上跑过一轮。

## 是否需要修复

这一步本身不需要再补结构。

当前结果已经足够进入下一环：

- 人工 review
- judge 校准
- breakdown canary

## 精确修复方法

本阶段新增：

- `backend/app/services/hotpost/breakdown_eval_review_packet_builder.py`
- `backend/scripts/evals/build_breakdown_review_packet_v1.py`
- `backend/scripts/evals/run_breakdown_judge_full_eval_v1.py`
- `backend/tests/services/hotpost/test_breakdown_eval_review_packet_builder.py`

本阶段新增文档与产物：

- `reports/evals/breakdown_eval_review_packet_v1.md`
- `reports/evals/breakdown_failure_taxonomy_v1.md`
- `reports/evals/breakdown_judge_spec_v1.md`
- `reports/evals/breakdown_judge_prompt_v1.md`
- `reports/evals/breakdown_judge_full_eval_predictions_v1.jsonl`
- `reports/evals/breakdown_judge_full_eval_summary_v1.json`

验证：

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_breakdown_eval_set_builder.py \
  backend/tests/services/hotpost/test_breakdown_eval_review_packet_builder.py -q

python backend/scripts/evals/build_breakdown_review_packet_v1.py
python backend/scripts/evals/run_breakdown_judge_full_eval_v1.py
```

结果：

- `4 passed`
- `review_cases = 18`
- `judge sample_count = 18`
- `pass_count = 17`
- `fail_count = 1`

当前 top failure tags：

- `weak_thesis`
- `quote_pack_not_supporting_claim`

## 下一步系统性的计划是什么

下一步直接进入：

1. 人工读 `breakdown_eval_review_packet_v1.md`
2. 做第一轮 breakdown failure taxonomy 校准
3. 跑 `breakdown canary`
4. 再决定是否有可 promote 的稳定拆解写法

## 这次执行的价值是什么

这次的价值不是“拆解又多了一些字”，而是把拆解卡质量优化从方向，推进成了和 signal 类似的工程化流程。

从现在开始，拆解线也不再只能靠临场感觉，而是可以用：

- 冻结样本
- 固定 review packet
- taxonomy
- judge

去稳定评估“这张拆解卡到底成不成立”。
