# phase1092 - 社区发现推荐系统设计

这轮目的：把用户补充的三个关键点写进主项目设计：语义库必须进入主链；标签由系统根据已有数据生成；交付物是社区发现与推荐系统设计。

当前状态变化：新增 `docs/superpowers/specs/2026-05-08-community-discovery-recommendation-system-design.md`，明确链路为“已有数据 + 语义库 -> 系统生成可服务标签 -> 用户点击 -> 推荐社区 + 理由 + 证据”。`semantic_terms / content_labels / content_entities / semantic_observation / embedding` 被纳入设计主链。

还没完成：离线推荐预览还没有实现，`ready / historical_depth / watching` 标签状态还没有真实跑数。

下一步：先做离线预览脚本或服务，验证跨境电商、AI 工具、宠物 / 小商品三个切片能否输出可解释社区推荐。
