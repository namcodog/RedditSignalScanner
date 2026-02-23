# phase79

日期: 2025-12-23

目标:
- 以 v2 文档为主，更新为 DB 现状（8 类分类、实际字段与状态）
- 同步更新 Atlas 文档，补齐字段清单与分类信息

已完成:
- 更新 `docs/sop/数据库使用规范_v2_全景版.md`：
  - 分类扩展为 8 类（含 AI_Workflow，统一 Ecommerce_Business）
  - 补充 status/tier/blacklist/health_status 的现状与统计
  - 标注 community_category_map 为空、business_categories 现有 7 key
- 更新 `docs/sop/2025-12-14-database-architecture-atlas.md`：
  - 更新 Control Tower status 取值
  - 补齐 community_pool、community_cache、community_category_map、business_categories 字段清单
  - 补齐 posts_raw/comments/posts_quarantine/post_scores/post_semantic_labels/post_embeddings 字段清单
  - 补齐 mv_monthly_trend/posts_latest 字段清单
  - 明确 8 类分类规范

未完成:
- 无

下一步:
- 若需把 business_categories 对齐到 8 类，可安排同步迁移
