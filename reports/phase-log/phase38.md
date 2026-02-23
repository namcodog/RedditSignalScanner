# Phase 38 - 升级版脚本收口与 SOP 完成

## 目标
- 收口脚本链路：与主链路 mode 规则对齐并标记 legacy。
- 用现行代码重写 facts_v2 SOP，保证新人可直接上手。

## 变更
- `backend/scripts/generate_t1_market_report.py`
  - mode 支持 auto（自动跟随 TopicProfile.mode）
  - 运行时打印 legacy 提示
- `backend/tests/services/test_report_logic.py`
  - 新增 `_resolve_mode` 单元测试
- `docs/sop/2025-12-13-facts-v2-落地SOP.md`
  - 全量重写为主链路版 SOP

## 测试
- `pytest -q backend/tests/services/test_report_logic.py -k resolve_mode`

## 结果
- 脚本 mode 行为与主链路一致，且明确标记为非黄金路径。
- SOP 与当前代码一致，可用于新人交接。
