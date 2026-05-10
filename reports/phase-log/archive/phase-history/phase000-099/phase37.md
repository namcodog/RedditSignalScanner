# Phase 37 - 升级版赛道路由落地

## 目标
- 让 `TopicProfile` 能定义默认 `mode`，未显式传入时自动落库，保证赛道规则贯通。

## 变更
- `backend/app/services/topic_profiles.py`：增加 `mode` 字段与解析逻辑。
- `backend/config/topic_profiles.yaml`：为现有赛道补 `mode: operations`。
- `backend/app/schemas/task.py`：`mode` 改为可选，未传入时由后端自动决策。
- `backend/app/api/v1/endpoints/analyze.py`：新增 `mode` 自动解析（显式优先、规则兜底）。
- `backend/tests/api/test_analyze.py`：新增 topic_profile 自动 mode 与显式覆盖测试。
- `backend/tests/services/test_topic_profiles.py`：新增 mode 解析测试。

## 测试
- `pytest -q backend/tests/services/test_topic_profiles.py backend/tests/api/test_analyze.py -k "topic_profile or explicit_mode_overrides"`

## 结果
- 未显式传 `mode` 时，按 `TopicProfile` 自动落库。
- 显式传 `mode` 时优先级最高，不被赛道规则覆盖。
