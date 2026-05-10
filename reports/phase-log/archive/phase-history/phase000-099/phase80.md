# phase80

日期: 2025-12-25

目标:
- 用 DB 实况生成全库表/字段/外键快照
- 将快照写入 v2 与 Atlas，确保两份文档覆盖全库

已完成:
- 从生产库生成全库结构快照（表/字段/视图/物化视图/外键）
- 追加到 `docs/sop/数据库使用规范_v2_全景版.md`
- 追加到 `docs/sop/2025-12-14-database-architecture-atlas.md`

未完成:
- 无

下一步:
- 视需要同步 `business_categories` 到 8 类并回填 `community_category_map`
