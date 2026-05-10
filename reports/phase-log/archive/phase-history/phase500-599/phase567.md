# Phase 567 - comment_label_planner 切到社区 truth-source

## 发现了什么？
- `backend/app/services/llm/comment_label_planner.py` 里还残留一条正式判断旧口径：
  - 领域权重
  - 激活候选数
  - 激活预过滤统计
  - 按领域抽取候选评论
- 这些逻辑之前还是直接读：
  - `community_pool.categories`
  - `community_pool.is_active`
  - `community_pool.is_blacklisted`
- 这会导致评论标注规划链虽然已经接了评论事实层，但社区归属和正式盘资格仍可能回漂到旧 projection。

## 是否需要修复？
- 需要。
- 这条链会直接影响评论标注的领域分配和激活样本，不改的话，后面的语义层仍然会吃到旧口径。

## 精确修复方法
### 1. comment_label_planner 正式改读 truth-source
- 更新：
  - `backend/app/services/llm/comment_label_planner.py`
- 改动：
  - 新增 `effective_communities / effective_community_domains` CTE
  - `_fetch_effective_domain_weights()` 改从：
    - `community_registry`
    - `community_runtime_state`
    - `community_domain_membership`
    - `community_governance_decision`
    - `business_categories`
    计算正式领域权重
  - `_fetch_activation_candidate_counts()` 改成只统计 truth-source 当前批准领域下的评论
  - `_fetch_activation_prefilter_stats()` 改成只统计 truth-source 正式社区下的未标注评论
  - `_fetch_domain_activation_candidates()` 改成按 truth-source 当前领域抽候选，不再依赖 `community_pool.categories`

### 2. 新增真实库约束回归
- 新增：
  - `backend/tests/services/llm/test_comment_label_planner_truth_source.py`
- 覆盖：
  - 只有 truth-source 启用社区会进入领域权重
  - orphan 社区即使还在 `community_pool`，其评论也不会进入激活预过滤统计

### 3. 按真实入库规则修正测试种子
- 这轮顺手暴露出两条真实数据库门槛：
  - `community_pool.semantic_quality_score` 为必填
  - `posts_raw` 会被触发器按正式规则隔离：
    - 未映射社区会隔离
    - 短标题/短正文会隔离
    - `community_id` 需要显式绑定正式社区
- 测试已经改成按正式规则建种子，不靠兜底绕过约束。

## 验证
- `pytest backend/tests/services/llm/test_comment_label_planner.py backend/tests/services/llm/test_comment_label_planner_truth_source.py -q`
  - `5 passed`

## 下一步系统性的计划
- 继续扫剩余 `worker / reports / API` 中的旧表正式判断点
- 优先处理仍直接依赖 `community_pool.categories / community_pool.is_active` 的链路
- 收尾标准保持不变：
  - 正式判断只认真相源
  - projection 只保留投影和兼容身份

## 这次执行的价值
- 社区层 truth-source 收口已经从：
  - 运营写入口
  - discovery
  - warmup
  - member sync
  - tier 调度
  扩展到了 **评论标注规划链**
- 这意味着后面的语义标注和评论激活样本，也开始按唯一正式社区盘和正式领域盘运行，不再偷吃旧 projection 口径。
