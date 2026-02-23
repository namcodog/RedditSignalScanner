# Phase1 DB Audit（只读，未改库）

## 已生成
- Schema 快照：reports/local-acceptance/db-schema-snapshot.md

## 缺口/风险（现状）
- 长窗趋势无预聚合：>90d 查询存在超时风险，需月度 MV/velocity 预聚合。
- 无噪声标签表：仅 spam_category/is_duplicate，缺 employee_rant/resale/bot/automod/template 等噪声标注。
- 质量/配置追溯缺失：quality 仅存于 facts JSON，缺 run/config/hash 的持久化审计表。
- 标签双轨：content_labels/MV 与 post_semantic_labels 需对齐/去重策略。
- 社区降权支撑不足：除 community_pool 的 blacklist/降权字段外，无系统化噪声/降权结构。

## 草案文件
- docs/db-design/trend_mv.sql
- docs/db-design/facts_quality_audit.sql
- docs/db-design/noise_labels.sql
- docs/db-design/community_audit.sql

## 声明
- 未执行任何数据库变更/清理，本次仅读取元数据并编写草案。
