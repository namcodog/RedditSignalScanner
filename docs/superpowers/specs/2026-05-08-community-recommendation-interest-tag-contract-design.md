# 社区推荐具像化兴趣标签合同

日期：2026-05-08
状态：当前补充硬合同

本文件用于锁定 Reddit Community Intelligence 的用户可见标签和社区推荐口径。若旧计划、旧 preview 或旧测试与本文件冲突，以本文件为准。

## 1. 问题定义

当前产品不是让用户输入空白检索词，也不是只生成几个后台分类名。用户应该先看到一组具体、可点击的兴趣标签，然后获得对应的 Reddit 社区推荐、推荐理由和证据摘要。

核心要求：
- 用户看见的是具体兴趣标签，不是后台系统名。
- 每个标签和推荐理由都必须能回到后台证据。
- 推荐可以先简单，但不能靠写死标签、社区名单、关键词包或文案完成。

## 2. 需要纠正的漂移

1. `CAPABILITY_SEEDS` 是业务硬编码。
   - 它把产品标签、关键词和业务范围写进 Python。
   - 不允许继续扩展；后续应被替换。

2. 抽象标签不够。
   - `AI 与自动化`、`电商与卖家` 这类可以作为后台分组，但不能直接当作主要用户标签。
   - 用户标签应更像兴趣选择，例如 AI 工作流、Agent 工具、宠物选品、EDC、SEO/GEO、投放技巧、众筹类商品、平台规则。
   - 上面只是说明标签颗粒度，不是生产枚举。

3. 内部证据不是用户文案。
   - 用户不应看到 `Hotpost`、`community_pool`、`semantic_observation`、`semantic ledger` 等系统词。
   - 这些词只允许出现在 debug、审计报告或测试证据里。

4. 推荐不是简单过滤。
   - 推荐至少要解释主题相关性、近期活跃、证据质量、相似社区关系、长尾 / 泛社区控制。
   - 第一版可以是可解释的轻量规则，但不能是假装算法的硬编码列表。

## 3. 方案取舍

| 方案 | 内容 | 结论 |
|---|---|---|
| A. 继续补 `CAPABILITY_SEEDS` | 直接往代码里加标签、关键词和社区 | 拒绝，违反无硬编码规则 |
| B. 数据驱动兴趣标签目录 | 从领域树、语义库、社区证据生成或校验标签，配置只负责展示文案和分组 | 采用 |
| C. 完整用户行为推荐 | 基于点击、收藏、共访做协同推荐 | 暂缓，当前没有足够用户行为数据 |

## 4. 固定合同

1. 禁止业务硬编码
   - 生产 Python / TypeScript 不能固定写产品标签列表、社区白名单、关键词包、排序权重或推荐文案。
   - 允许来源：DB、现有领域树配置、语义表、显式 YAML / JSON 配置、合同文档。
   - 测试可以有 fixture，但 fixture 不能变成生产行为。

2. 用户标签必须具像化
   - 标签是用户能理解的兴趣选择，不是内部数据表名或工程 slice。
   - 宽泛分组可以存在，但只能用于组织标签，不能替代最终推荐标签。

3. 标签必须可追溯
   - 每个可见标签至少映射到一种后台证据：领域树节点、语义词 / 实体 / 观察、社区证据、近期活跃证据。
   - 没有证据映射的标签不能标记为 `ready`。

4. 用户文案和内部证据分离
   - 用户文案解释“为什么这个社区值得看”。
   - debug 证据解释“系统为什么这样判”。
   - 内部系统词不得出现在用户推荐理由里。

5. 推荐必须可解释
   - 第一版评分维度固定为：主题相关性、近期活跃、证据质量、相似社区关系、多样性 / 长尾控制。
   - 权重来自配置或命名策略，不允许藏在服务代码常量里。

6. `community_pool` 不是结果页
   - `community_pool` 是干净社区总池。
   - 推荐层必须基于用户标签、活跃度、证据和多样性再筛一层。

7. Hotpost 是内部信号源
   - Hotpost 可以提供证据和新社区发现信号。
   - Hotpost 不能作为用户可见推荐理由里的词。

## 5. 输出合同

用户可见兴趣标签：

```text
id
display_name
short_description
group
status
available_community_count
```

用户可见社区推荐：

```text
community
reason
best_for
activity_label
related_to
evidence_teaser
```

用户文案风格示例：

```text
最近有不少真实用户在这里讨论 AI 编程工具的日常使用问题。
这个社区更适合看宠物用品的购买反馈和反复抱怨点。
这里常出现投放成本、归因和平台规则变化的实战讨论。
```

这些只是文案风格示例，不是生产常量。

## 6. 内部调试合同

内部 debug 可以包含：

```text
source_scope_id
topic_pack_id
topic_cluster_id
semantic_terms
semantic_observation_count
content_label_count
content_entity_count
hotpost_card_count
recent_posts_15d
latest_activity_at
score_breakdown
```

这些字段只服务报告、测试和工程审计。

## 7. 防漂移测试

后续实现必须补测试，确保：

1. 生产代码里不存在 `CAPABILITY_SEEDS` 或等价业务种子常量。
2. 用户推荐理由不包含 `Hotpost`、`community_pool`、`semantic_observation`、`semantic ledger` 或表名。
3. 可见标签没有后台映射时不能输出为 `ready`。
4. 每条社区推荐必须有用户可读理由。
5. 有 debug 证据但没有用户价值解释时，推荐不合格。

## 8. 最小实现边界

第一轮只允许改社区推荐 preview 后端：

```text
backend/app/services/community/community_recommendation_service.py
backend/app/services/community/community_recommendation_preview.py
backend/scripts/community/community_recommendation_preview.py
backend/tests/services/community/test_community_recommendation_preview.py
backend/tests/scripts/community/test_community_recommendation_preview.py
reports/community-recommendation/*
```

如果需要共享 loader / service，只新增职责单一的小文件。不要新建第二套分类系统。CLI、后续 API 和前端适配层必须共用 service 入口。

## 9. 验收标准

合同满足条件：
- 用户可见 preview 输出具像化兴趣标签。
- 生产代码不包含产品标签列表。
- 每个可见标签都有后台映射证据。
- 每条社区推荐都有用户理由和内部 debug 证据。
- 用户输出不暴露后台系统词。
- Hotpost 日运营和小程序 snapshot 链不受影响。

## 10. 暂不做

- 不做前端。
- 不做 API。
- 不做用户行为追踪。
- 不做实时 Reddit 抓取。
- 不写 Gold DB。
- 不新增推荐结果表。
- 第一版不做 ML 协同过滤。
- 不改 Hotpost 日常产卡和小程序发布链。

## 11. 下一步

先用测试替换旧 preview 合同，再做最小实现。实现目标是把硬编码标签源替换为数据驱动标签目录，并保证用户文案与内部证据分离。
