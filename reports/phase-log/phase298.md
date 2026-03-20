# Phase 298 - hotpost 模块第二轮第一刀：响应组装层服务化

> 时间：2026-03-15  
> 模块：hotpost 模块  
> 范围：响应组装边界、状态/调试信息合同、service 编排层瘦身  
> 当前状态：已完成第二轮第一刀

---

## 1. 发现了什么？

第二轮回到 hotpost 模块后，这一刀没有继续去调 query 解析，也没有去碰报告 prompt，而是先盯住了最重的一坨：

- `HotpostService.search()`

查下来它之前虽然已经比第一轮更诚实了，但还是把太多事缠在一起：

1. 查询解析后的状态判断
2. `debug_info` 组装
3. rant / opportunity 两种模式的结果补强
4. LLM report 合并
5. markdown 导出
6. 最终 `HotpostSearchResponse` 组装

一句大白话：

- **第一轮把 hotpost 开始收成“说真话”，第二轮这一刀开始把“怎么把真话装进正式响应”收成独立齿轮。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。  
这一刀做的是结构性收口，不是业务算法调整。

---

## 3. 精确修复方法？

### 3.1 新增正式响应组装层

新增：

- `backend/app/services/hotpost/response_bundle.py`

这层正式接管了 hotpost 的响应打包职责，新增了：

- `HotpostResponseBundleInput`
- `resolve_hotpost_response(...)`
- `build_hotpost_debug_info(...)`
- `build_hotpost_search_response(...)`

也就是说，现在不是：

- service 一边查数据，一边现场手拼一大坨响应字段

而是：

- **service 先拿数据**
- **response bundle 专门负责把结果组装成正式响应**

### 3.2 HotpostService 开始更像编排层

修改：

- `backend/app/services/hotpost/service.py`

这次把几个最缠的内部动作收回到 bundle 层：

1. 响应状态判断  
2. `debug_info` 组装  
3. rant / opportunity 模式补强  
4. LLM report 合并后落到最终响应  
5. markdown 导出后的响应回填

现在 `HotpostService.search()` 更像：

- 先做检索 / 评论 / 证据持久化
- 再把结果交给 bundle 层统一打包

一句大白话：

- **service 不再自己一边当司机，一边顺手现场焊车身。**

### 3.3 用新测试把 bundle 合同锁住

新增：

- `backend/tests/services/hotpost/test_hotpost_response_bundle.py`

这组测试锁住了三件事：

1. `disabled` report 不会把响应硬判成降级
2. rant 模式的正式响应仍然能组装成 typed schema
3. opportunity 模式的机会强度 / unmet needs 走当前真实合同，不再靠旧假设

同时，修正了我自己在新测试里写错的两处预期：

- `10` 条证据帖 + `me_too_count=5` 当前真实合同是 `medium`，不是 `strong`
- `market_opportunity` 不是机会模式保底字段，`unmet_needs` 才是当前保底合同

这一步很重要，因为它保证了：

- **不是为了让测试过，而是把测试重新拉回当前真实接口。**

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮的价值不是“hotpost 更聪明了”，而是：

- 把 hotpost 模块里最容易继续漂移的“响应组装层”正式抽成了独立边界
- 让 service 层更像编排层
- 让状态、来源、降级原因开始通过正式 bundle 合同往外走

这更符合第二轮目标：

- 职责更单一
- 接口更稳
- 高耦合点继续打薄

一句大白话：

- **这刀把 hotpost 里最容易越写越重的那层先拆开了，后面继续做缓存编排、输出壳收口时，会顺很多。**

---

## 5. 验证结果

### 定向合同回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/hotpost/test_hotpost_response_bundle.py \
  tests/services/hotpost/test_hotpost_summary.py \
  tests/services/hotpost/test_hotpost_schema.py \
  tests/api/test_hotpost.py -q
```

结果：

- `10 passed`

### hotpost 整组回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost -q
```

结果：

- `50 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/hotpost/response_bundle.py \
  backend/app/services/hotpost/service.py \
  backend/tests/services/hotpost/test_hotpost_response_bundle.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

hotpost 模块第二轮这一刀之后，还剩几个更大的结构问题没有做：

1. cache / live result / queue 之间的编排边界还能继续拆
2. `HotpostService.search()` 虽然已经变薄，但仍然背着不少取数和持久化细节
3. 用户侧输出壳和内部 bundle 之间还能继续做更清楚的合同分层

所以这轮的正确定位是：

- **第二轮第一刀已经值回票价**
- 但不是 hotpost 模块第二轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第二轮既定顺序，下一步进入：

- **基础设施 / 监控模块** 的第二轮结构性收口

