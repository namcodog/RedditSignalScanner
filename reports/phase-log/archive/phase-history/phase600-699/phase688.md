# phase688 - card autoresearch lab v2 polish keep

## 本阶段完成
- 新增 `polish` 层实验能力：
  - `backend/app/services/hotpost/signal_polish_variant_policy.py`
  - `backend/app/services/hotpost/signal_polish_experiment.py`
  - `backend/scripts/evals/run_card_autoresearch_lab_v2.py`
  - `backend/tests/services/hotpost/test_signal_polish_experiment.py`
- `card-autoresearch-lab v2` 已跑完整 `signal eval`，不再停在 8 条小样本。
- 新增结果文档：
  - `reports/evals/card_autoresearch_lab_v2_full_eval.md`

## 关键结果
- 完整样本：`31`
- baseline：
  - `baseline_polish_v1 = 13/31 pass`
- 实验变体：
  - `clean_summary_polish_v1 = 15/31 pass` -> `keep`
  - `clean_summary_tight_why_now_polish_v1 = 8/31 pass` -> `discard`

## 结论
- `polish` 层比继续找新的全局总 prompt 更有效。
- 当前唯一值得 promote 的是：
  - `clean_summary_polish_v1`
- 当前不该 promote 的是：
  - `clean_summary_tight_why_now_polish_v1`

## 验证
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_signal_polish_experiment.py backend/tests/services/hotpost/test_card_autoresearch_lab.py -q`
  - `5 passed`
- `python backend/scripts/evals/run_card_autoresearch_lab_v2.py --limit 8 --batch-size 4 --concurrency 4`
  - 小样本验证通过
- `python backend/scripts/evals/run_card_autoresearch_lab_v2.py --batch-size 4 --concurrency 4`
  - 已跑完整 `31` 条 signal eval

## 下一步
- promote `clean_summary_polish_v1`
- 暂不改统一 `why_now` polish
- 如果继续做 v3，优先：
  - 标题去报告腔
  - pack 级 polish
