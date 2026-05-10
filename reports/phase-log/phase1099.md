# phase1099 - 社区推荐标签合同配置化收口

这轮目的：把用户可选标签从旧抽象标签纠正为 9 个具像化业务标签，并消除 Python 里的业务标签硬编码。

当前状态变化：
- 9 个用户可选标签已由 `backend/config/community_interest_tags.json` 承载。
- 旧业务分类目录、别名和 Phase 2 分类推断已由 `backend/config/community_business_categories.json` 承载。
- 旧社区发现 / 社区池治理链已归档为历史实现：`docs/reference/community-discovery-legacy-archive-2026-05-08.md`。
- 推荐匹配新增护栏：旧 `community_pool.categories` 不能单独构成推荐证据。
- 预览已重跑：`tags=9 / recommendations=59 / ready_count=27 / acceptance_passed=true`。

还没完成：
- 用户还未验收 `reports/community-recommendation/preview.md` 和 `audit.md` 的推荐质量。
- `platform_policy_trends` 当前还是 `watching=0`，需要后续补数据或映射。

下一步：
- 先做用户审核，再决定是否进入 API / 前端。
- 根据审核结果继续收紧标签映射和语义证据，不回到开放搜索框。
