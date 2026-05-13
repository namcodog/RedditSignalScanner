# Phase 296 - 社区治理模块第二轮第一刀：治理结果合同正式建模

> 时间：2026-03-15
> 模块：社区治理模块
> 范围：`community_governance_service`、admin 控制面治理接口、治理快照/清理结果合同
> 当前状态：已完成第二轮第一刀

---

## 1. 发现了什么？

第二轮回到社区治理模块后，最深的问题不再是“分类真相源说没说清”，而是：

- 治理服务虽然已经开始说真话
- 但 `build_snapshot()` 和 `cleanup_dev()` 仍然在返回大块原始 `dict`
- admin 路由再直接吃这些 `dict`，前后端靠字段约定俗成协作

这会带来一个很典型的漂移风险：

1. 文档里说治理口径已经统一
2. 服务层也开始有稳定字段
3. 但接口没有正式建模，后面人和 AI 还是可能“想到什么塞什么”

一句大白话：

- **第一轮把社区治理模块的真相说清楚了，第二轮这一刀开始把“真相怎么正式输出”也收成稳定合同。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这轮做的是结构性收口，不是治理规则改版。

---

## 3. 精确修复方法？

### 3.1 新增正式治理 schema

新增：

- `backend/app/schemas/community_governance.py`

把原来散在服务层 raw dict 里的治理结果，正式收成了模型：

- `GovernanceSnapshot`
- `GovernanceSummary`
- `GovernancePoolCommunityItem`
- `GovernanceHistoricalShellItem`
- `GovernanceDiscoveredCommunityItem`
- `GovernanceCleanupResult`
- 以及对应的删除计数 / 阻塞项 / 目标清单模型

现在社区治理模块不再是：

- 服务层拼大 dict
- 路由层再猜字段

而是：

- **服务层先产出正式治理结果对象**
- **路由层只负责序列化和返回**

### 3.2 `community_governance_service.py` 收成正式结果输出层

修改：

- `backend/app/services/community/community_governance_service.py`

这次把：

- `build_snapshot()`
- `cleanup_dev()`

从“返回原始 dict”收成了“返回正式 schema 对象”。

同时保留并稳定了第一轮已经收住的核心合同：

- `normalized_categories`
- `category_source`
- `category_breakdown`
- `historical_shells`

一句大白话：

- **治理服务现在更像真正的治理结果提供者，而不是随手拼 JSON 的工具函数。**

### 3.3 admin 路由退成薄序列化层

修改：

- `backend/app/api/routes/admin_community_pool.py`

现在 admin 控制面治理接口统一改成：

1. 调服务拿正式结果对象
2. `model_dump(mode=\"json\")`
3. 交给统一响应壳

也就是说：

- **admin 控制面不再继续直接依赖治理服务的内部 dict 结构。**

### 3.4 用测试把治理合同锁住

修改：

- `backend/tests/services/community/test_community_governance_service.py`
- `backend/tests/api/test_admin_community_pool.py`

测试现在不再按“老 dict 世界”断言，而是对齐当前真实合同：

- 服务层断言模型属性
- API 层断言序列化后的 JSON 结构

这样后面再有人改治理返回值，不会无声漂移。

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“多了几个 schema 文件”，而是：

- 把社区治理模块从“真相开始清楚，但接口还靠约定”继续推进到
- **真相和接口一起正式化**

这更符合第二轮目标：

- 职责更单一
- 接口更稳
- 高耦合点继续打薄

一句大白话：

- **这刀把社区治理模块最容易漂移的“服务结果合同”先钉死了，后面继续拆快照和动作边界会更稳。**

---

## 5. 验证结果

### 定向回归

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

### 语法自检

```bash
python -m py_compile \
  backend/app/schemas/community_governance.py \
  backend/app/services/community/community_governance_service.py \
  backend/app/api/routes/admin_community_pool.py \
  backend/tests/services/community/test_community_governance_service.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

社区治理模块第二轮这一刀之后，还剩几个更大的结构问题没有做：

1. 快照服务和清理动作仍然还在同一个 service 里
2. `historical_shells` 的长期隔离合同还能继续变硬
3. admin 控制面和治理服务之间，还能进一步继续收薄

所以这轮的正确定位是：

- **第二轮第一刀已经值回票价**
- 但不是社区治理模块第二轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第二轮既定顺序，下一步进入：

- **语义 / 标签模块** 的第二轮结构性收口

重点会从第一轮的“状态说真话、任务合同统一”，继续推进到：

- 子链职责继续拆清
- provider / task / prefilter 边界继续收口
- 标签价值链继续朝“可长期稳定发挥作用”推进

一句话：

- **社区治理模块这刀先收到这里，下一步回到理解层继续拆耦合。**
