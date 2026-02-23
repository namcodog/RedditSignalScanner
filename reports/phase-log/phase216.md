# Phase 216

## 目标
- 信号词检测落地并覆盖 Trending/Rant/Opportunity。

## 变更
- Trending 模式信号检测接入：`backend/app/services/hotpost/service.py`
  - `_select_signals` 增加 `detect_discovery_signals`
- 规则测试补充：`backend/tests/services/hotpost/test_hotpost_rules.py`

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_rules.py -q`

## 结论
- Phase 216 完成，信号词检测已覆盖三种模式。
