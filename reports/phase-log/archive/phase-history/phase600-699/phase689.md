# phase689 - promote clean summary polish to production

## 本阶段完成
- 已将 `card-autoresearch-lab v2` 跑出的 keep：
  - `clean_summary_polish_v1`
  promote 到生产 `polish` 层。
- 生产侧改动：
  - `backend/app/services/hotpost/card_content_polish.py`
    - `summary_line` 默认执行去转述腔清理
- 实验侧保留：
  - `signal_polish_variant_policy.py`
  - `signal_polish_experiment.py`
  - `run_card_autoresearch_lab_v2.py`

## 关键结果
- 完整 `31` 条样本里：
  - `baseline_polish_v1 = 13/31 pass`
  - `clean_summary_polish_v1 = 15/31 pass`
  - `clean_summary_tight_why_now_polish_v1 = 8/31 pass`
- 当前 promote 边界：
  - 只 promote `summary` 去转述腔
  - 不 promote 统一 `why_now` 压缩

## 验证
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_signal_polish_experiment.py backend/tests/services/hotpost/test_card_autoresearch_lab.py backend/tests/services/hotpost/test_card_content_generator.py -q`
  - `20 passed`
- `python -m py_compile backend/app/services/hotpost/card_content_polish.py backend/app/services/hotpost/signal_polish_experiment.py backend/app/services/hotpost/signal_polish_variant_policy.py backend/scripts/evals/run_card_autoresearch_lab_v2.py`
  - 通过

## 当前边界
- 当前这轮只把 `summary_line` 的去转述腔 promote 到生产。
- `why_now` 统一短句化已证伪，继续保留现有生产写法。
- 如果后面继续做 `autoresearch-lab v3`，更值的是：
  - 标题去报告腔
  - pack 级 polish
