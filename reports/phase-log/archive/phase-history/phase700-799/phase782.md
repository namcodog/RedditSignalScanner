# phase782

## 事项

- 按 `hot v1.0` 标准回灌已发布 `hot`
- 只处理 `lane=hot`，不碰 `signal / breakdown / lane=None`

## 本次改动

- 文案清洗与锚点修正
  - `backend/app/services/hotpost/semantic_readout.py`
- 定向测试补齐
  - `backend/tests/services/hotpost/test_card_content_generator.py`
- 已发布 `hot` 刷新 plan
  - `backend/tmp/published-hot-v10-refresh-plan.json`

## 执行边界

- 已发布 `hot` 总量：`23`
- 仅对这 `23` 张做 `mimo/gemini` 当前生产 hot 链下的语义重生成与筛查
- 不改 schema
- 不动 `signal`
- 不动 `breakdown`
- 不改排序 / 分发 / feed contract

## 本轮处理

### 1. 先清 plan

- 合并 targeted rerun 后，对整份 `published-hot-v10-refresh-plan.json` 做坏模式扫描
- 扫描项：
  - `...`
  - `…`
  - `原话里`
  - `原文里`
  - `翻过来就是`
  - `特别是那些`
  - `尤其是那些`
- 结果：`0 hits / 0 errors`

### 2. apply 已发布 hot 刷新

- `python backend/scripts/hotpost/refresh_published_card_semantics.py --apply-plan backend/tmp/published-hot-v10-refresh-plan.json --json`
- 结果：
  - `selected=23`
  - `merged=23`

### 3. 修正 mini snapshot 对齐

- 首次 `push_mini_snapshot.py` 返回旧 release，后续核查确认：
  - `backend/data/hotpost/releases/latest.json` 已经是新文案
  - `build_mini_snapshot()` 也已经能算出新 checksum
- 重新推送后，mini snapshot 与 cloud_db 已对齐到新 release

## 验证

### 定向测试

- `pytest backend/tests/services/hotpost/test_card_lane_policy.py backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py backend/tests/services/hotpost/test_card_content_generator.py -q --tb=short -p no:schemathesis`
- 结果：`92 passed`

### 发布链

- `python backend/scripts/hotpost/push_mini_snapshot.py`
- 结果：
  - `release_id=release-9eb12a0667d3`
  - `card_count=155`

- `python backend/scripts/hotpost/check_mini_release_sync.py`
- 结果：
  - `feed_contract=30/30`
  - `cloud_db copy guard: ok`

### 数据面

- 发布总卡数：`155`
- 已发布 `hot`：`23`
- 本轮回灌写回：`23 / 23`

## 结论

- `hot v1.0` 已真正落到已发布池
- 边界守住：只刷了 `23` 张 `hot`
- mini snapshot、bundle、cloud_db 已同步完成
- 当前可把已发布 `hot` 视为：
  - 入口边界：`sample-boundary v7`
  - 争议线定义：`fight-line-definition v3`
