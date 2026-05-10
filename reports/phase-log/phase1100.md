# phase1100 - 社区推荐后端架构收口

## 这轮达到的目的
把标签式社区推荐收成后端应用服务架构，先不做前端。

## 当前状态变化
- 新增后端架构文档和 `community_recommendation_service.py`。
- CLI 已改为调用同一 service；后续 API / 前端只能做薄适配。
- 当前报告重跑为 `tags=9 / recommendations=64 / ready_count=32 / db_writes=false`。
- `电商平台政策与风向` 已接入真实 hotpost topic 证据，当前为 `ready / available_community_count=5`。

## 还没完成什么
- 还没有做 API / 前端。
- `电商平台政策与风向` 仍有审核表里的“复核匹配”项，需要后续补深层语义词。
- 深层语义观察和真实 Reddit 活跃探测还要增强。

## 下一步做什么
先验收后端推荐质量和审核表；通过后再决定是否进入 API / 前端。
