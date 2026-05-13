# Community Recommendation Backend Architecture

日期：2026-05-08
状态：当前后端架构口径

本文件只定义后端边界。当前不做前端、不做 API、不写 Gold DB。

## 1. 目标

把社区推荐后端收成一条可复用链路：

```text
已有数据 + 语义库 + Hotpost 探测
  -> 系统生成可服务标签
  -> 推荐社区 + 理由 + 证据
  -> 输出 preview / audit
```

以后如果接 API 或前端，只能调用同一个服务入口，不能在接口层重写一套推荐逻辑。

## 2. 分层

| 层 | 文件 | 职责 |
|---|---|---|
| 配置真相源 | `backend/config/community_interest_tags.json` | 用户可见兴趣标签、后台映射、权重、文案模板 |
| 旧分类配置 | `backend/config/community_business_categories.json` | 旧 DB 8 大领域和 Phase 2 分类推断追溯 |
| 数据加载 | `backend/app/services/community/community_recommendation_loader.py` | 从 Dev DB 和 Hotpost 证据只读组装社区信号 |
| 领域计算 | `community_recommendation_core/text/ranker/builder.py` | 标签匹配、状态判断、排序、推荐理由 |
| 应用服务 | `backend/app/services/community/community_recommendation_service.py` | 统一生成 preview、audit 和验收摘要 |
| 输出适配 | `community_recommendation_payload.py`、`community_recommendation_markdown.py`、`community_recommendation_audit.py` | JSON / Markdown / 审核表 |
| CLI | `backend/scripts/community/community_recommendation_preview.py` | 离线生成报告；只调用应用服务 |

## 3. 当前硬边界

- `community_pool` 是社区总池，不是推荐结果页。
- 旧社区发现 / 治理脚本只作为历史审计和 Dev 写入追溯，不接当前产品主链。
- 用户可见标签、关键词、权重和文案不写进 Python。
- 推荐服务只读：不持有 `SessionFactory`，不调用写库脚本，不 `commit`。
- Hotpost 是内部证据源和新社区探测器，用户文案里不出现系统词。

## 4. 后续接入方式

API / 前端后续要接时，入口固定为：

```python
build_community_recommendation_report(session, tag_limit=..., community_limit=...)
```

CLI 已经走这个入口。后续只允许增加薄适配层，不允许在 API、前端或脚本里复制标签生成、排序、理由拼装逻辑。

## 5. 当前验收

当前离线报告产物：

- `reports/community-recommendation/preview.md`
- `reports/community-recommendation/preview.json`
- `reports/community-recommendation/audit.md`
- `reports/community-recommendation/audit.json`

当前后端完成标准：

- 能从现有数据和语义证据生成具像化兴趣标签。
- 能输出社区推荐、理由、证据和审核表。
- CLI 和未来 API 共享同一个服务入口。
- 不依赖用户输入标签。
- 不写 Gold DB，不影响 Hotpost 日运营和小程序 snapshot 链。
