# Phase (Market Insight V2) - 角色A执行日志（社区分析）

## 今日产出（测试优先）
- 新增测试：`backend/tests/services/analysis/test_persona_generator.py`
- 新增测试：`backend/tests/services/test_saturation_matrix.py`
- 实现服务骨架：
  - `backend/app/services/analysis/persona_generator.py`（规则+LLM兜底）
  - `backend/app/services/analysis/saturation_matrix.py`（查询+分类）
  - 轻量集成：在 `report_service.get_report()` 启用 `enable_market_report` 时计算前3社区×前5品牌的饱和度均值，落到 `metrics_summary.brands`（不改 schema，零侵入）。
  - 完整并行集成（1.10 收尾）：在 `report_service.get_report()` 中（构建 overview、metadata 后）插入 `asyncio.gather()` 并发执行 Persona/Quote/Saturation；结果写入 `metadata.market_enhancements`（新可选字段，向后兼容）。
  - Phase 2（角色A支援）：新增“机会窗口”计算，用于为 GTM/Copy 提供品牌在低饱和社区的清单：
    - `SaturationMatrix.compute_opportunity_windows()`（返回每品牌 TopN 低饱和社区）
    - 单测：`backend/tests/services/test_saturation_matrix.py::test_saturation_opportunity_windows`
    - 集成：将结果落到 `metadata.market_enhancements.saturation_opportunities`

## 统一反馈四问
1) 发现了什么问题/根因？
- 新模块无落地代码，需要先明确接口并用测试锁定行为；
- Persona 依赖 LLM 与规则双通道，需要定义稳定的降级路径；
- Saturation 依赖 posts_hot × content_entities，需要明确列名(entity、entity_type 等)与去重口径。

2) 是否已精确定位？
- 是。接口与数据表访问模式已固化到测试与实现：
  - Persona：comments→TF-IDF→规则/LLM→PersonaResult。
  - Saturation：posts_hot×content_entities('brand','post')→去重计数/总帖→阈值分类。

3) 精确修复方法？
- 按设计文档定义 dataclass 与 Service 接口；
- 先写测试，新增最小可用实现，确保无 LLM 时规则可用、LLM 失败可降级；
- SQL 使用 SQLAlchemy text + 子查询，保证查询简单可控，后续可优化（索引/范围）。

4) 下一步做什么？
- 补充 Persona 规则集与策略标签映射，完善 LLM prompt/解析；
- 扩充 Saturation 阈值与 overall 的加权策略，并补充更多边界测试；
- 与 `report_service.py` 完整集成（已完成，受 feature flag 控制）。
 - Phase 2 后续支援：若需要，将机会窗口结合社区加权（如 pain_density/ps_ratio）做排序增强。
- 验证 mypy 严格模式与覆盖率达标。

5) 本次效果/结果？
- 两个核心模块的接口与最小行为已经通过测试约束，具备可迭代基础；
- 后续实现细化不会破坏对外接口，便于集成推进。

## 命令与文件
- 测试文件：
  - backend/tests/services/analysis/test_persona_generator.py
  - backend/tests/services/test_saturation_matrix.py
- 实现文件：
  - backend/app/services/analysis/persona_generator.py
  - backend/app/services/analysis/saturation_matrix.py

记录人：角色A（社区分析工程师）
