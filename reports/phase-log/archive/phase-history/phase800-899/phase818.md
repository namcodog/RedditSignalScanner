# phase818

## 本轮目标

确认 `hot controversy_chart` 的 v8 回灌已经真正接入主链，并对主链状态做一轮完整审计。

## 主链状态

- 当前分支：`main`
- 当前 HEAD：`0123086`
- `hot controversy_chart` 回灌链路已接入：
  - [backend/app/services/hotpost/mini_snapshot.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/mini_snapshot.py)
  - [backend/app/services/hotpost/hot_controversy_chart.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hot_controversy_chart.py)
  - [backend/app/services/hotpost/hot_controversy_llm.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hot_controversy_llm.py)

## 审计范围

只审 `hot controversy_chart` 这一条主链：

- 生成 prompt / output contract
- 模型锁定
- snapshot 接线
- 测试回归
- recent 10 hot 真实复核

## 审计结果

### 1. 主链接线

- `mini_snapshot` 在构建发布卡时会调用 `refresh_hot_controversy_cards_sync`
- `refresh_hot_controversy_cards_sync` 会走 `build_hot_controversy_result`
- `build_hot_controversy_result` 已锁到 `google/gemini-2.5-flash-lite`
- `LLM_SUMMARY_VERSION = cn_human_point_slots_v8`

### 2. 回归测试

```bash
cd backend && pytest tests/services/hotpost/test_hot_controversy_llm.py tests/services/hotpost/test_card_content_llm_router.py tests/services/hotpost/test_hot_comment_sample.py tests/scripts/hotpost/test_push_mini_snapshot.py -q
```

结果：`16 passed`

### 3. recent 10 hot 真实复核

评估结果：

- `decision = publish`
- `distinct_ratio_combo_count = 9`
- `chinese_focus_count = 10/10`
- `clear_focus_count = 10/10`
- `human_points_count = 9/10`
- `low_sample_overclaim_count = 0`
- `extreme_ratio_count = 0`

输出文件：

- [hot-controversy-chart-v8-recent10.json](/Users/hujia/Desktop/RedditSignalScanner/backend/tmp/hot-controversy-chart-v8-recent10.json)
- [hot-controversy-chart-v8-summary.json](/Users/hujia/Desktop/RedditSignalScanner/backend/tmp/hot-controversy-chart-v8-summary.json)

## 风险与边界

- 当前仓库工作树本身很脏，存在大量与本任务无关的改动，本轮没有尝试清理。
- 本轮只确认 `hot controversy_chart` 主链可用，不扩展到 `signal / breakdown`。
- 仍有少量边缘卡的人话短句可继续微调，但不影响主链上线判断。

## 结论

- `hot controversy_chart` 已真正进入项目主链
- 当前实现建议正式作为主链版本使用
