# Phase 645 - Hotpost Mini Topic-Pack 路由落地

## 结果

`topic-pack` 已经真正接进 `hotpost-mini` 的后端采集链，不再只是合同文档。

- 保留原有 3 个 `source_scope`
- 在 scope 内新增 `topic_pack_id`
- 电商供给已改成：
  - `selection-signals`
  - `category-winds`
  - `kill-signals`
- AI 与增长也已按合同拆成各自 3 个 topic-pack

## 实现边界

- 不改前端
- 不改已有卡片 schema 的主结构
- 不复用主系统 `warzones` 数据链
- 单文件控制在 200 行以内，配置与逻辑拆开

## 代码落点

- `backend/app/services/hotpost/source_scope_catalog.py`
- `backend/app/services/hotpost/reddit_search_spec_builder.py`
- `backend/app/services/hotpost/source_scope_candidate_collector.py`
- `backend/app/services/hotpost/topic_pack_scope_ai.py`
- `backend/app/services/hotpost/topic_pack_scope_ecommerce.py`
- `backend/app/services/hotpost/topic_pack_scope_growth.py`
- `backend/app/schemas/hotpost_source_scopes.py`
- `backend/app/schemas/hotpost_card_candidates.py`

## 验证

已通过定向测试：

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/api/test_hotpost_source_scopes.py \
  backend/tests/api/test_hotpost_card_candidates.py \
  backend/tests/services/hotpost/test_source_scope_catalog.py -q
```

结果：`12 passed`

## 当前判断

这轮完成的是“供给轴改造”，不是 prompt 改造。

也就是说：

- 前端继续看 `📡 信号 / 🔍 拆解`
- 但后端开始按更清晰的 topic-pack 去抓内容
- 电商 feed 后面会自然提高选品信号和类目风向的占比，不再被运费/仲裁/平台问题一边倒占满
