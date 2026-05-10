# Phase 546 - 社区运营写入口统一到 truth-source

## 本轮目标

把社区的新增、删减、调整，从“旧表各写各的”收成“先写 truth-source，再同步 projection”的单一入口。

## 发现了什么？

上一轮 DB 审计已经确认：

- Dev DB 的正式运行盘已经对齐
- 但社区运营动作仍然分散在旧入口
- 典型问题是：
  - admin approve / disable / batch update
  - Excel 导入
  - discovery evaluator 自动批准

这些入口如果继续直写旧表，就会造成：

- truth-source 和 projection 再次脱节
- 新增/禁用社区后，planner/readiness/report 不一定按同一套口径生效

## 是否需要修复？

需要，而且这是当前社区层收尾的关键一步。

如果不把“运营写入口”统一，前面做好的 DB 真相源、读路径切换、物理压缩，后面还会继续被旧写法污染。

## 精确修复方法

### 1. 社区写入口统一到 `CommunityMutationService`

本轮把以下业务动作接到同一条正式写链：

1. 管理后台批准社区
2. 管理后台禁用社区
3. 管理后台批量更新 `tier / priority / is_active`
4. Excel 导入社区
5. discovery evaluator 自动批准社区

### 2. truth-source 先写，再同步 projection

统一顺序：

1. `community_registry`
2. `community_domain_membership`
3. `community_governance_decision`
4. `community_runtime_state`
5. `community_pool / community_cache / community_category_map`

### 3. 杜绝旧脏分类混进真相源

这轮补了一刀关键约束：

- 类别解析只能保留 `business_categories` 中 active 的 canonical key
- 旧脏值如 `topic / general / ml` 不再允许进入 truth-source
- `approved` 场景下如果没有合法 canonical category，直接暴露真实错误，不兜底

### 4. 继续保留 archive 的历史证据原则

- `archive` 表达“退出正式抓取盘”
- 不做物理删除
- 历史帖子与证据继续保留

## 本轮代码变更

### 新增

- `backend/app/services/community/community_mutation_state.py`
- `backend/app/services/community/community_mutation_projection.py`
- `backend/app/services/community/community_mutation_truth.py`
- `docs/sop/2026-03-28-社区真相源与运营写入口统一口径.md`

### 主要修改

- `backend/app/services/community/community_mutation_service.py`
- `backend/app/services/community/truth_source_sync_service.py`
- `backend/app/api/routes/admin_community_pool.py`
- `backend/app/services/community/community_import_service.py`
- `backend/app/services/discovery/evaluator_service.py`

### 测试修改 / 补充

- `backend/tests/services/community/test_community_mutation_service.py`
- `backend/tests/services/community/test_community_import.py`
- `backend/tests/services/community/test_evaluator_service.py`
- `backend/tests/api/test_admin_community_pool_unit.py`
- `backend/tests/api/test_admin_community_pool.py`

## 验证

执行：

```bash
pytest backend/tests/services/community/test_community_mutation_service.py \
  backend/tests/services/community/test_community_import.py \
  backend/tests/services/community/test_evaluator_service.py \
  backend/tests/api/test_admin_community_pool_unit.py \
  backend/tests/api/test_admin_community_pool.py -q
```

结果：

- `24 passed`

## 下一步系统性的计划是什么？

1. 继续扫剩余 `reports / API / worker` 里是否还有旧表直写入口
2. 继续把正式判断链收口到 truth-source
3. 持续维护社区层运行口径文档，避免旧文档继续误导

## 这次执行的价值是什么？达到了什么目的？

这轮的价值不是“又加了一个 service”，而是：

- 社区层终于不只是“读真相源”，也开始“写真相源”
- 新增、禁用、导入、自动批准这几条运营动作，开始统一口径
- Dev DB 后面不会因为旧入口继续回流脏状态

一句话总结：

社区层现在已经从“库结构基本干净”推进到“运营写入口开始统一”，这一步是让整个系统长期稳固的关键。
