# Phase 755 - 小程序卡片语义发布链路深层审计

日期：2026-04-10

## 发现了什么

- 新生成链路已经吃到新 prompt，但旧 published 卡在 `mini_snapshot / cloud_db / cloudfunctions` 发布物里仍会带出旧口径。
- 真实发布物里还残留：
  - `这帖问的是`
  - `这帖吵的不是`
  - `评论区真正`
  - `越来越多人`
  - `1个帖子`
  - `继续盯 / 先放过`
  - `赛道`
  - `min_test_action`
- `check_mini_release_sync.py` 之前只核对 release 和 feed contract，不会拦截语义旧口径。
- `backfill_published_cards()` 仍通过 `replace_published_cards()` 整体替换 published，和“只按 card_id 合并回写 published”的边界不一致。

## 是否需要修复

需要。否则即使新卡 prompt 变好了，前台仍会被旧发布物和旧脚本路径污染。

## 精确修复方法

- 新增 `backend/app/services/hotpost/card_content_rules_config.py`
  - 把 `card_content_rules.yaml` 读取入口从 generator 拆出来，供 snapshot/check 复用。
- `backend/app/services/hotpost/mini_snapshot.py`
  - 发布出口统一对 `title / summary_line / audience / why_now / detail` 做配置化语义清洗。
  - 继续移除 `detail.min_test_action`，确保云数据库导入物不再带旧字段。
- `backend/config/card_content_rules.yaml`
  - 扩充 `semantic_readout.rewrite_phrases`，集中处理旧卡残留口径，不在 Python 里堆文案硬编码。
  - 将 `赛道` 加入生成禁词，防止新卡继续写报告腔。
- `backend/scripts/hotpost/check_mini_release_sync.py`
  - 增加 `cloud_db copy guard`，同步检查时直接拦旧字段和旧话术。
- `backend/app/services/hotpost/card_content_generator.py`
  - `backfill_published_cards()` 改为 `merge_published_cards()`，不再整桶替换 published。
- 小程序前端
  - 将“值得关注”类 UI 文案改成“值得看”。

## 验证

```bash
cd backend && pytest tests/scripts/hotpost/test_push_mini_snapshot.py tests/services/hotpost/test_card_content_generator.py::test_signal_prompt_does_not_ask_llm_to_generate_min_test_action tests/services/hotpost/test_reddit_guide_prompt_assets.py -q --tb=short -p no:schemathesis
cd backend && python -m py_compile app/services/hotpost/card_content_rules_config.py app/services/hotpost/card_content_generator.py app/services/hotpost/semantic_readout.py app/services/hotpost/mini_snapshot.py scripts/hotpost/check_mini_release_sync.py
cd backend && python scripts/hotpost/push_mini_snapshot.py && python scripts/hotpost/check_mini_release_sync.py
cd hotpost-mini/hotpost-mini-app && npm run build:weapp
```

结果：

- `pytest`：6 passed
- `py_compile`：通过
- `build:weapp`：通过
- 新 release：`release-7ab4ccb72fc6`
- `card_count=125`
- `feed_contract=30/30`
- `cloud_db copy guard: ok`
- 对 `latest.json / cloud_db / miniRelease / miniFavorites` 的产品字段扫描：旧口径命中 `0`

## 下一步

- 后续每次 `push_mini_snapshot.py` 后必须跑 `check_mini_release_sync.py`，让 release 对齐和 copy guard 一起过。
- 如果还要继续提升读感，优先改 `card_content_rules.yaml` 和 prompt，不再绕过发布出口做零散补丁。
