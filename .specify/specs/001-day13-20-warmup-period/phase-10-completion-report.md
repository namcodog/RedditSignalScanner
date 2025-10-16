# Phase 10 完成报告（Warmup Report Generator 验收与完善）

## 概览
- 依据 plan.md，完成预热期报告生成器的增强、单测、以及 CLI 验证。
- 关键修复：解决 asyncio.run 在已有事件循环中的冲突，确保在测试（异步上下文）与命令行（同步上下文）均可稳定运行。

## 交付物
- 脚本：backend/scripts/generate_warmup_report.py（新增 build_report_async(precomputed_metrics)；同步包装器 build_report() 先获取实时指标后再运行异步聚合；main() 输出 JSON 与摘要）
- 测试：backend/tests/scripts/test_warmup_report.py（异步用例；使用唯一社区名避免 PK 冲突；预计算实时指标传入 async 构建器；落盘校验）
- 报告产物：reports/warmup-report.json（由脚本生成）

## 验证记录
1) 类型检查（严格模式）
   - 命令：mypy --strict --follow-imports=skip scripts/generate_warmup_report.py
   - 结果：0 issues
2) 单元/脚本测试
   - 命令：pytest tests/scripts/test_warmup_report.py -q --tb=short
   - 结果：1 passed
3) CLI 自检
   - 命令：python scripts/generate_warmup_report.py
   - 结果：控制台打印摘要，并成功写入 reports/warmup-report.json

## 四问自检
1. 通过深度分析发现了什么问题？根因是什么？
   - 问题A：测试在异步上下文中调用的同步构建器内部使用 asyncio.run，触发 “asyncio.run() cannot be called from a running event loop”。
   - 根因A：异步/同步边界处理不当；在 event loop 已运行时再次创建事件循环。
   - 问题B：测试插入的 CommunityCache 社区名与其他用例可能重复，触发主键冲突。
   - 根因B：测试隔离不足；现有 conftest 未对该表统一清理。

2. 是否已经精确定位到问题？
   - 是。定位到 build_report() 与 build_report_async() 的调用时序，以及 monitoring_task.* 中内部使用 asyncio.run 的位置；同时定位到测试数据的主键冲突点。

3. 精确修复问题的方法是什么？
   - 构建器分层：
     - 新增 async 构建器 build_report_async(precomputed_metrics: Optional[dict])，仅负责 DB 异步聚合与拼装；不在其中调用任何会再次创建事件循环的任务函数。
     - 同步包装器 build_report() 先调用 monitor_warmup_metrics() 计算实时指标（该函数内部可能使用 asyncio.run），随后以 asyncio.run 执行 build_report_async(...)，避免嵌套事件循环。
   - 测试修复：
     - 在测试内预计算实时指标，作为参数传入 build_report_async(...)，规避在异步上下文中再次触发 asyncio.run。
     - 采用唯一社区名（uuid 后缀）避免与其他测试的 PK 冲突。

4. 下一步的事项要完成什么？
   - 若进入生产，建议补充 Alembic 迁移（Phase 9 中新增的 beta_feedback 表等）。
   - 将报告生成器纳入定时任务或发布流程的验收步骤，并将生成的报告同步到可视化面板或存档目录。
   - 针对实时指标来源（Redis/监控任务）补充更多容错与回退逻辑（例如连接失败时降级为 0 值）。

## 验收标准对照
- [x] 能成功生成报告
- [x] 指标字段齐全且类型正确（包含 warmup_period、community_pool、cache_metrics、api_usage、user_testing、system_performance）
- [x] 保存到 reports/warmup-report.json
- [x] 控制台打印人类可读摘要

## 附：关键接口摘录
- 异步构建器（只读概要）：
  - build_report_async(precomputed_metrics: Optional[dict]) -> dict
- 同步包装器（CLI）：
  - build_report() -> dict
  - main() -> int（打印摘要并写入 JSON）

---
完成。
