# Phase 293 - 分析模块第二轮第一刀：检索计划收口 + 发现社区副作用隔离

> 时间：2026-03-15
> 模块：分析模块
> 范围：`analysis_engine`、`hybrid_retriever`、`t1_stats`、分析副作用服务
> 当前状态：已完成第二轮第一刀

---

## 1. 发现了什么？

第二轮进入分析模块后，这一刀没有继续补状态字段，而是先盯两个真正会继续缠住分析核心的深层点：

1. **检索计划还在多处自己拼**
   - `hybrid_retriever` 一套
   - `t1_stats` 又一套
   - 而且旧逻辑直接拼 `to_tsquery(...)`
   - 碰到空格短语、标点、脏 token，就会自己把自己打成降级

2. **发现社区写库副作用还挂在分析主流程里**
   - `run_analysis()` 在主链里直接写 `discovered_communities`
   - 这会把：
     - FK 约束
     - 临时 task context
     - 写库动作
     混进分析核心

一句大白话：

- **第一轮让分析模块开始说真话，第二轮这一刀开始把“检索怎么拼”和“副作用怎么写”从分析核心里拆开。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这轮做的是结构性收口，不是业务逻辑扩张。

---

## 3. 精确修复方法？

### 3.1 检索计划收口成共享合同

新增：

- `backend/app/services/analysis/search_query.py`

统一提供：

- `build_websearch_query(...)`
- `clean_search_term(...)`

然后把两条原来各拼各的链收进同一个口径：

- `backend/app/services/analysis/hybrid_retriever.py`
- `backend/app/services/analysis/t1_stats.py`

这次同时做了两件关键收口：

1. 不再自己拼危险的 `to_tsquery(...)`
2. 改成统一走：
   - `websearch_to_tsquery(...)`
   - 共享 query builder

另外，`hybrid_retriever` 也从“只回 posts list”升级成了更明确的内部合同：

- `HybridRetrievalPlan`
- `HybridRetrievalResult`

这样分析核心拿到的，不再只是“帖子列表”，而是：

- 这次检索是 `completed / skipped / degraded`
- 原因是什么
- 实际用了什么搜索查询

### 3.2 发现社区副作用从分析主流程里隔出去

新增：

- `backend/app/services/analysis/analysis_side_effects.py`

新增正式副作用结果：

- `DiscoveredCommunityRecordResult`

并把“发现社区写库”收成独立 side-effect service：

- `record_discovered_communities_for_task(...)`

新的护栏很明确：

- 没收集到社区：跳过
- `TaskSummary.user_id` 缺失：跳过
- task 根本没持久化：跳过

也就是说：

- **分析核心仍然可以“发现社区”**
- 但“能不能写 discovered_communities”现在变成了独立判断，不再默认裹着分析主链一起跑

### 3.3 `analysis_engine` 主链继续说真话，但少背两类杂事

修改：

- `backend/app/services/analysis/analysis_engine.py`

现在分析主链：

- 混合检索不再自己拼搜索语句
- 发现社区写库不再自己承担写库细节
- 即使测试里 monkeypatch `_record_discovered_communities = None`，主链也不会被这种兼容桩带崩

一句大白话：

- **分析核心开始更像分析核心，而不是继续把“检索拼装”和“数据库副作用”都自己背着。**

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“分析更聪明了”，而是：

- 进一步拆掉分析模块内部的混层
- 让检索计划和副作用合同各回各位

这更符合第二轮的目标：

- 职责更单一
- 接口更稳
- 高耦合点继续打薄

一句大白话：

- **这刀把分析模块里最容易继续缠住核心的两根线，先拆开了。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/analysis/test_analysis_side_effects.py \
  tests/services/semantic/test_hybrid_retriever.py \
  tests/services/community/test_discovered_communities_pool_pollution.py \
  tests/services/analysis/test_analysis_engine.py \
  tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py -q
```

结果：

- `39 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 6. 这轮之后还剩什么？

分析模块第二轮这一刀之后，还剩下更大的结构性问题没有做：

1. `analysis_engine.py` 本体仍然偏大
2. facts/facts_slice/structured render 之间还有继续拆边界的空间
3. 发现社区副作用虽然已经隔出去，但分析模块和发现链的长期边界还可以继续收

所以这轮的正确定位是：

- **第二轮第一刀已经值回票价**
- 但不是分析模块第二轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第二轮既定顺序，下一步进入：

- **facts / 报告模块**

重点不再是补字段，而是继续收：

- facts 整理
- 报告组装
- 渲染边界
- 兼容壳退出

一句话：

- **分析模块这刀先收到这里，下一步继续往表达层走。**
