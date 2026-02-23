# Phase 196

## 目标
- 对齐爆帖速递缓存 key/TTL，并提供预热入口。

## 变更
- 新增缓存工具：`backend/app/services/hotpost/cache.py`
  - `reddit_hot:{mode}:{query_hash}:{subs_hash}` key 规则
  - TTL 按模式读取 env（trending/rant/opportunity）
- 搜索流程改用新缓存 key/TTL：`backend/app/services/hotpost/service.py`
- 新增预热脚本：`backend/scripts/warmup_hotpost_cache.py`
- 新增缓存单测：`backend/tests/services/hotpost/test_hotpost_cache.py`

## 验证
- `PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_cache.py -q`

## 结论
- 缓存 key/TTL 与文档一致，预热入口已具备。

## 影响范围
- 仅爆帖速递缓存逻辑。
