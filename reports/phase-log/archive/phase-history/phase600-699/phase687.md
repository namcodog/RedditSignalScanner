# phase687 - card autoresearch lab v1 full eval closure

## 本阶段完成
- 将 `card-autoresearch-lab v1` 从 smoke 提升到完整 `signal eval` 规模。
- `run_card_autoresearch_lab_v1.py` 已支持：
  - `--offset`
  - `--batch-size`
  - `--concurrency`
  - 分批汇总
- `card_autoresearch_lab.py` 已支持单 case 容错：
  - 变体或 judge 单次异常不再打断整轮实验
  - 会记录为 `lab_runtime_error`
- 新增结果文档：
  - `reports/evals/card_autoresearch_lab_v1_full_eval.md`

## 关键结果
- 完整样本：`31`
- baseline：
  - `human_summary_tight_why_now_v1 = 11/31 pass`
- 实验变体：
  - `judgment_forward_summary_v2 = 11/31 pass`
  - `judgment_forward_summary_strict_v2 = 10/31 pass`
- 结论：
  - 当前没有新的 `keep`
  - baseline 继续保留
  - 两个 judgment-forward 变体继续 `discard`

## 验证
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_card_autoresearch_lab.py -q`
  - `3 passed`
- `python backend/scripts/evals/run_card_autoresearch_lab_v1.py --limit 8 --batch-size 4 --concurrency 4`
  - 已验证分批 runner 正常工作
- `python backend/scripts/evals/run_card_autoresearch_lab_v1.py --batch-size 4 --concurrency 4`
  - 已跑完整 `31` 条 signal eval

## 当前边界
- `card-autoresearch-lab v1` 现在适合：
  - prompt 层离线实验
  - keep/discard 评估
- 暂不适合：
  - 自动 promote
  - 主链自治优化
  - 用总 prompt 直接救所有 pack

## 下一步
- 保留当前 baseline：
  - `human_summary_tight_why_now_v1`
- 如果继续推进 autoresearch：
  - 优先扩到 `polish` 层
  - 或转到更窄的 pack 变体实验
