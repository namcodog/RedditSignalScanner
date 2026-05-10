# Card Autoresearch Lab V1 Smoke

## 目标

验证 `card-autoresearch-lab v1` 是否已经具备最小可用能力：

- 读取冻结 eval set
- 跑多组 signal prompt 变体
- 用现有 judge 打分
- 产出 keep / discard

## 运行方式

```bash
python backend/scripts/evals/run_card_autoresearch_lab_v1.py --limit 2
```

## 本轮变体

1. `human_summary_tight_why_now_v1`（baseline）
2. `judgment_forward_summary_v2`
3. `judgment_forward_summary_strict_v2`

## 结果

| variant | pass | fail | pass_rate | decision |
| --- | ---: | ---: | ---: | --- |
| `human_summary_tight_why_now_v1` | 2 | 0 | 1.0 | baseline |
| `judgment_forward_summary_v2` | 1 | 1 | 0.5 | discard |
| `judgment_forward_summary_strict_v2` | 2 | 0 | 1.0 | discard |

## 结论

- `card-autoresearch-lab v1` 已经能完成最小闭环：
  - 变体实验
  - judge 评估
  - keep / discard 输出
- 当前 keep/discard 逻辑是：
  - 只有严格优于 baseline 才 `keep`
  - 与 baseline 持平也不会自动 `keep`
- 这符合当前“受控实验室”定位，避免实验一开始就过度 promote。

## 当前边界

- 这只是 2 条样本的 smoke，不代表真正的全量结论。
- 当前只支持 `signal` 的 prompt 层实验。
- 还没有扩到：
  - `breakdown`
  - `polish`
  - `rules.yaml`
