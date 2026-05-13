# phase686 - card autoresearch lab v1 runner

## 本阶段完成
- 新增 `card-autoresearch-lab v1` service：
  - `backend/app/services/hotpost/card_autoresearch_lab.py`
- 新增 runner：
  - `backend/scripts/evals/run_card_autoresearch_lab_v1.py`
- 新增测试：
  - `backend/tests/services/hotpost/test_card_autoresearch_lab.py`
- 新增 smoke 结果：
  - `reports/evals/card_autoresearch_lab_v1_smoke.md`

## 关键结果
- 当前 lab 已能完成最小闭环：
  - 读取冻结 `signal eval set`
  - 跑多个 prompt 变体
  - 调用现有 judge
  - 输出 keep / discard
- 本轮 smoke（`--limit 2`）结果：
  - `human_summary_tight_why_now_v1 = baseline`
  - `judgment_forward_summary_v2 = discard`
  - `judgment_forward_summary_strict_v2 = discard`

## 验证
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_card_autoresearch_lab.py -q`
  - `2 passed`
- `python backend/scripts/evals/run_card_autoresearch_lab_v1.py --limit 2`
  - 已真实输出 keep/discard，并落盘到 `reports/evals/card_autoresearch_lab_*`

## 当前边界
- V1 只支持 `signal` 的 prompt 层实验。
- 不碰生产主链。
- 不自动 promote。
