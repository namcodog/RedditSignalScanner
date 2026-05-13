# phase817

## 本轮目标

把 key-os 已验证通过的 `cn_human_point_slots_v8` 回灌到项目侧 `hot controversy_chart` 生成链，只改 prompt / output contract，并锁定模型到 `google/gemini-2.5-flash-lite`。

## 实际改动

- 更新 [backend/app/services/hotpost/hot_controversy_llm.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hot_controversy_llm.py)
  - 模型锁定为 `google/gemini-2.5-flash-lite`
  - `LLM_SUMMARY_VERSION` 更新为 `cn_human_point_slots_v8`
  - prompt 回灌为 v8 语义：中文、冲突短句、人话短句、neutral 具体、禁模板词、低样本保守
  - 接入项目侧输出归一化：英文名转中文替代、`还在观察/还在观望` 收敛到 `先看`
- 更新 [backend/tests/services/hotpost/test_hot_controversy_llm.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_hot_controversy_llm.py)
  - 补 v8 版本号断言
  - 补模型锁定断言
  - 补中文归一化断言

## 验证

### 测试

```bash
cd backend && pytest tests/services/hotpost/test_hot_controversy_llm.py tests/services/hotpost/test_card_content_llm_router.py tests/services/hotpost/test_hot_comment_sample.py tests/scripts/hotpost/test_push_mini_snapshot.py -q
```

结果：`16 passed`

### recent 10 hot 真实复核

导出文件：

- [hot-controversy-chart-v8-recent10.json](/Users/hujia/Desktop/RedditSignalScanner/backend/tmp/hot-controversy-chart-v8-recent10.json)
- [hot-controversy-chart-v8-summary.json](/Users/hujia/Desktop/RedditSignalScanner/backend/tmp/hot-controversy-chart-v8-summary.json)

评估命令：

```bash
python3 /Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_hot_controversy_chart_quality_evaluator_v1.py \
  --input /Users/hujia/Desktop/RedditSignalScanner/backend/tmp/hot-controversy-chart-v8-recent10.json \
  --summary-json /Users/hujia/Desktop/RedditSignalScanner/backend/tmp/hot-controversy-chart-v8-summary.json
```

结果：

- `decision = publish`
- `distinct_ratio_combo_count = 9`
- `chinese_focus_count = 10/10`
- `clear_focus_count = 10/10`
- `human_points_count = 9/10`
- `low_sample_overclaim_count = 0`
- `extreme_ratio_count = 0`

## spot check

- `card-cand-ai-automation-1sk82sc-validate`
  - `0.21 / 0.42 / 0.37`
  - `这到底是治安事件还是反人工智能情绪越线了？`
- `card-cand-business-growth-ops-1sjw2o6-validate`
  - `0.42 / 0.12 / 0.46`
  - `平台算法到底废了还是素材更新太慢`
- `card-cand-ai-automation-1siqwmp-validate`
  - `0.12 / 0.67 / 0.21`
  - `模型降级乱收费，用户到底该不该继续买单？`

## 结论

- 项目侧 `hot controversy_chart` 已锁到 `google/gemini-2.5-flash-lite`
- v8 prompt / output contract 已回灌到主生成链
- recent 10 hot 复核达到 key-os 给出的 publish 线
- 建议正式进入主链
