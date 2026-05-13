# phase1098

## 这轮达到的目的

把 Reddit Community Intelligence 的 R7-R9 落地到离线推荐预览：推荐理由证据化、标签-社区审核表、语义证据密度补强。

## 当前状态变化

- 社区推荐代码已从 865 行大文件拆成 `community_recommendation_*` 小模块；推荐文案、审核文案和证据摘要模板由配置承载，触碰的生产代码文件都控制在 200 行以内。
- `preview.md/json` 已重生成：`tags=6 / recommendations=55 / ready_count=26 / acceptance_passed=true`。
- 新增 `reports/community-recommendation/audit.md` 和 `audit.json`，按 `推荐通过 / 限额参考 / 复核匹配 / 补证据` 给出审核表。
- 用户可见推荐理由现在包含近期讨论数、主题证据、高价值信号数和代表讨论，不再只输出模板句；公共区不暴露内部系统词或后台分类词。
- 加载层已读取 `content_labels / content_entities` 的标签和实体词，补到推荐语义证据里。

## 还没完成什么

- `ready` 仍主要依赖 Hotpost 近期探测；Dev `posts_hot` 的真实 15D 活跃探测和深层 `semantic_observation / semantic_terms` 还要继续补。

## 下一步做什么

用户先验收 `preview.md` 和 `audit.md`；下一轮按审核表处理 `复核匹配 / 补证据` 社区，不进入 API / 前端。
