# Phase 815 - Hot 真实争议占比落地

## 目标

- 只在小程序独立发布线里，把 `hot` 的争议图改成真实评论样本聚合。
- 不碰 dev 数据库。
- 不改前端 schema。
- 失败时只允许低置信或无图，禁止回退旧模板比例。

## 本次改动

- 新增 [hot_comment_sample.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hot_comment_sample.py)
  - `source_link -> post_id`
  - `smart_shallow + limit=40 + depth=2`
  - 去掉 `[deleted]`、超短评论、重复评论
- 新增 [hot_controversy_llm.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hot_controversy_llm.py)
  - 单卡一次 LLM 汇总
  - 输出 `support/oppose/neutral` 计数、代表观点、分歧点
  - 比例由代码按真实计数算，不让 LLM 硬编百分比
- 改造 [hot_controversy_chart.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/hot_controversy_chart.py)
  - 删除旧固定桶位生成逻辑
  - 新增发布前刷新 `hot` 卡争议图
- 改造 [mini_snapshot.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/mini_snapshot.py)
  - `publish_mini_snapshot(...)` 先刷新 `published hot`
  - `build_mini_snapshot(...)` 继续只做纯整理
- 新增测试
  - [test_hot_comment_sample.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_hot_comment_sample.py)
  - [test_hot_controversy_llm.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_hot_controversy_llm.py)
- 更新测试
  - [test_push_mini_snapshot.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/scripts/hotpost/test_push_mini_snapshot.py)

## 验证

```bash
cd backend && pytest tests/services/hotpost/test_hot_comment_sample.py tests/services/hotpost/test_hot_controversy_llm.py tests/scripts/hotpost/test_push_mini_snapshot.py -q
cd backend && python -m py_compile app/services/hotpost/hot_comment_sample.py app/services/hotpost/hot_controversy_llm.py app/services/hotpost/hot_controversy_chart.py app/services/hotpost/mini_snapshot.py
```

结果：

- `11 passed`
- `py_compile passed`

## 结论

- `hot` 争议图现在已经从“固定模板桶位”切到“真实评论样本 + 单卡 LLM 汇总”这条链。
- 失败行为已经锁死：
  - 无效链接、抓取失败、LLM 坏结果都不会再偷偷补模板比例。
- 当前剩下的不是工程边界问题，而是真实数据 spot check：
  - 样本够不够
  - 比例组合是否摆脱模板感
  - 代表观点是否真像评论区在吵的内容
