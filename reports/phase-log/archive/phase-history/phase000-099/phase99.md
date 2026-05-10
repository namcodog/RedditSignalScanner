# Phase 99 - PRD 后端同步（现状对齐）

日期：2025-12-25

## 目标
将 PRD 中后端相关内容同步到本地实现，前端/Admin 文档不动。

## 已同步文档
- `docs/PRD/PRD-INDEX.md`
- `docs/PRD/ARCHITECTURE.md`
- `docs/PRD/PRD-01-数据模型.md`
- `docs/PRD/PRD-02-API设计.md`
- `docs/PRD/PRD-03-分析引擎.md`
- `docs/PRD/PRD-04-任务系统.md`
- `docs/PRD/PRD-06-用户认证.md`
- `docs/PRD/PRD-09-动态社区池与预热期实施计划.md`

## 主要差异（旧 PRD vs 现状）
- 从“四表架构”升级为“多域数据模型”（抓取/清洗/评分/事实/报告）。
- API 从“4 个端点”升级为“核心 4 + 扩展导出/实体/社区接口”。
- 任务系统从“单队列”升级为“多队列 + Beat + 可靠性参数”。
- 社区池从“静态四层”升级为“发现+验毒+评估+入池闭环”。
- 分析引擎增加 facts_v2 门禁与降级输出。

## 边界说明
- 前端与 Admin 文档按要求未更新。

## 验证
- 对照 `backend/app/*` 与 `current_schema.sql` 进行口径校验。
