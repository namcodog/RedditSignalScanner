# Phase 282 - 社区治理模块第一轮整治：分类契约收口

> 时间：2026-03-15
> 模块：社区治理模块
> 范围：`community_governance_service` + `admin_community_pool`
> 当前状态：已完成

---

## 1. 发现了什么？

社区治理这块虽然已经把：

- 生效社区
- 候选社区
- 普通垃圾
- historical shells

分开了，但还留着一个会继续让后面口径漂移的问题：

- 顶层虽然已经有 `data_source_contract.category_source`
- 但每条社区记录里的 `categories` 还是原始形态
- 当前仓库里既有：
  - `dict`
  - `list`
  - 空值
- 这意味着：
  - 人看会猜
  - AI 看也会猜
  - 后面 API / 前端 / 审计继续容易在“分类到底是什么格式”上漂移

一句话说：

- **真相源写在顶层了，但分类契约还没有真正写进每条记录和 summary。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，也没有新增 migration。
做的是社区治理模块内部的**分类契约收口**：

- 把原始 `categories` 保留
- 同时新增稳定的 `normalized_categories`
- 明确每条社区记录的 `category_source`
- 在 `summary` 里新增当前生效社区的领域分布汇总

---

## 3. 精确修复方法？

### 3.1 治理服务

修改：

- `backend/app/services/community/community_governance_service.py`

新增/调整：

1. 新增 `_normalize_categories`
   - 把 `dict / list / 单值 / 空值` 收成统一的 `list[str]`
   - 做去重

2. 新增 `_build_category_breakdown`
   - 只基于 `effective_communities` 汇总
   - 输出当前真正生效社区的分类分布
   - 没分类的统一记为 `unclassified`

3. `effective_communities / garbage_pool / historical_shells`
   - 每条记录现在都带：
     - `normalized_categories`
     - `category_source = "community_pool.categories"`

4. `candidate_communities / discovered`
   - 统一带：
     - `normalized_categories = []`
     - `category_source = null`

5. `summary`
   - 新增：
     - `category_breakdown`
     - `effective_unclassified_count`

### 3.2 API 验证

修改：

- `backend/tests/api/test_admin_community_pool.py`

现在 `/api/admin/communities/governance/summary` 和 `/governance/effective` 也会一起验证：

- `category_source`
- `normalized_categories`
- `category_breakdown`

---

## 4. 验证结果

### 定向测试

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/community/test_community_governance_service.py \
  tests/api/test_admin_community_pool.py -q
```

结果：

- `16 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 5. 这次执行的价值是什么？达到了什么目的？

这一步的价值，不是多加了几个字段，而是把社区治理模块真正收成了**可作为全系统真相入口**的一层。

现在这块终于能稳定回答：

- 当前真正生效的社区有哪些
- 每个社区分类的稳定格式是什么
- 分类来自哪里
- 当前生效社区按领域怎么分布

一句大白话收口：

- **这一步把社区治理模块从“顶层说得清、明细还容易让人猜”，修成了“顶层和明细都说同一种话”。**

---

## 6. 下一步系统性的计划是什么？

按总整治执行计划，下一步继续推进同一组的第二个模块：

- **数据采集模块**

目标不变：

- 继续沿着“模块为主 + 链路补充”的方式
- 先把系统源头这组模块收成真正稳定可控的一层
