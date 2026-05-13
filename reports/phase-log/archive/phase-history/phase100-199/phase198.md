# Phase 198

## 目标
- 将爆帖速递限流默认口径对齐到文档：100 QPM / 10min。

## 变更
- 默认限流参数调整：`backend/app/services/hotpost/service.py`
  - `DEFAULT_RATE_LIMIT=100`
  - `DEFAULT_RATE_WINDOW=600`
- 新增限流默认值与 env 覆盖单测：`backend/tests/services/hotpost/test_hotpost_rate_limit.py`

## 验证
- `PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_rate_limit.py -q`

## 结论
- 限流默认口径与文档一致，仍可通过环境变量覆盖。

## 影响范围
- 仅爆帖速递限流策略。
