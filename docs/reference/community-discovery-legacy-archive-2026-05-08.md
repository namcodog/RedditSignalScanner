# Community Discovery Legacy Archive

日期：2026-05-08
状态：历史实现归档口径

## 归档结论

旧社区发现 / 社区池治理链已经退役为历史治理工具。

它不是错误实现；它服务的是旧目标：扩大社区覆盖、治理 `community_pool`、为数据采集和社区资产建设做准备。

当前产品目标已经切到：

已有数据 + 语义库 + 活跃证据 -> 系统生成用户可选标签 -> 推荐社区 + 理由 + 证据。

因此旧实现不能再作为当前产品推荐主判断链。

## 归档范围

以下入口只保留为历史审计、数据准备、Dev 写入追溯和 rollback 参考：

- `backend/scripts/community/community_governance_audit.py`
- `backend/app/services/community/community_pool_phase1_planner.py`
- `backend/scripts/community/community_pool_phase1_dry_run.py`
- `backend/app/services/community/community_pool_phase2_dev_writer.py`
- `backend/scripts/community/community_pool_phase2_dev_write.py`
- `reports/community-governance/phase0-*`
- `reports/community-governance/phase1-*`
- `reports/community-governance/phase2-*`
- `docs/reference/community-governance-rules-2026-05-07.md`

这些文件不物理移动，避免破坏历史报告、测试、Dev 写入说明和 rollback 链路。

## 仍然有效的部分

DB 8 大领域仍然有效。

它们是后台数据抓取、社区资产分桶和历史数据组织层，不是用户可见产品标签，也不是最终推荐理由。

允许用途：

- 采集范围组织
- 社区池资产分桶
- 历史数据解释
- 旧数据兼容
- Dev restore / category map 兼容

不允许用途：

- 直接展示给用户当兴趣标签
- 单独决定某社区应该被推荐
- 替代语义证据、活跃度、代表帖子和推荐理由

## 当前主链

当前社区推荐主链只看以下入口：

- `backend/config/community_interest_tags.json`
- `backend/config/community_business_categories.json`
- `backend/app/services/community/community_recommendation_*`
- `backend/scripts/community/community_recommendation_preview.py`
- `reports/community-recommendation/preview.md`
- `reports/community-recommendation/audit.md`

推荐判断必须满足：

- 命中用户可选标签配置
- 有标签相关关键词或语义证据
- 有 Hotpost / 旧 DB / 近期活跃 / 代表帖子等可解释证据
- 长尾优先，泛社区限额参考

`community_pool.categories` 只能辅助粗筛，不能单独推荐。

## 不在范围

- 不删除 `community_pool.categories`
- 不删除 DB 8 大领域
- 不删除历史报告
- 不回滚 Phase 2 Dev 写入
- 不把旧实现改造成新推荐系统
