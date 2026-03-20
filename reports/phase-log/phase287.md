# Phase 287 - hotpost 模块第一轮整治：`debug_info` 正式类型化，来源/降级合同不再靠猜

> 时间：2026-03-15  
> 模块：hotpost / 爆帖速递模块  
> 范围：`hotpost` schema、`service.py`、hotpost 定向测试  
> 当前状态：已完成第一轮

---

## 1. 发现了什么？

这轮没有重复去修 Round 4 已经收过的点，而是继续往更深一层看：

- 现在 `status`、`query_source`、`summary_source`、`report_source` 这些语义已经开始说真话
- 但这些字段仍然被塞在一个裸 `debug_info: dict[str, Any]` 里
- 后端 schema 没有正式定义这层接口
- 前端却已经在 `hotpost.ts` 里自己手写了一份半结构化类型

这说明一件事：

- **hotpost 这条链虽然已经比以前诚实了，但接口真相源还没统一。**

一句大白话：

- **前端已经在按固定字段读，后端却还在把这层当“大字典”随手拼。**

这就是最容易继续漂移的地方：

- 人和 AI 看不到正式合同
- 后面再改字段，很容易一边改了，另一边没跟上

---

## 2. 是否需要修复？

需要，而且这轮已经修完第一刀。

这次没有改数据库 schema，也没有新增 migration。  
做的是两件事：

1. 把 hotpost 的 `debug_info` 从裸 dict 收成正式 schema
2. 把 `service.search()` 里散着拼字段的逻辑收成统一构造入口

---

## 3. 精确修复方法？

### 3.1 `debug_info` 正式进入 schema 合同

修改：

- `backend/app/schemas/hotpost.py`

新增：

- `HotpostDebugInfo`

字段固定为：

- `query_source`
- `query_degraded_reason`
- `search_query`
- `query_parts`
- `keywords`
- `time_filter`
- `sort`
- `subreddits`
- `raw_posts`
- `filtered_posts`
- `relevance_filtered`
- `response_source`
- `summary_source`
- `summary_degraded_reason`
- `report_source`
- `report_degraded_reason`
- `llm_report_applied`
- `degraded_reasons`

同时：

- `HotpostSearchResponse.debug_info`
  - 从 `dict[str, Any] | None`
  - 改成 `HotpostDebugInfo | None`

也就是说：

- **hotpost 结果里的“调试/来源信息”不再是靠约定俗成，而是正式进入后端接口合同。**

### 3.2 `service.search()` 改成统一构造 `debug_info`

修改：

- `backend/app/services/hotpost/service.py`

新增：

- `HotpostService._build_debug_info(...)`

现在 live 路径里的 `debug_info` 不再在 `search()` 中散着拼，而是统一从一个 helper 构造。

缓存命中路径也同步改成：

- 先补 `response_source = "cache"`
- 再转成 `HotpostDebugInfo`

这轮的重点不是多加字段，而是把这条合同从：

- “哪里要用哪里拼”

改成：

- “只有一个正式构造入口”

这更符合总整治的准则：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

### 3.3 测试门禁补齐

修改：

- `backend/tests/services/hotpost/test_hotpost_schema.py`
- `backend/tests/services/hotpost/test_hotpost_summary.py`

新增门禁测试：

1. `test_hotpost_response_debug_info_is_typed`
   - 验证 `HotpostSearchResponse` 接 dict 时会被收成正式 `HotpostDebugInfo`

2. `test_build_debug_info_returns_stable_contract`
   - 验证 `HotpostService._build_debug_info()` 产出的字段和当前合同一致

这意味着：

- 以后谁再把 `debug_info` 改回裸散字段
- 或随手加字段不对齐
- 测试会直接红

---

## 4. 这轮结果是什么？

这轮的本质不是“hotpost 更聪明了”，而是：

- **hotpost 的来源/降级信息终于不只是“说了”，而是“被正式建模了”。**

现在这条链更像一个稳定齿轮：

- query 解析的来源和降级原因
- summary 的来源和降级原因
- report 的来源和降级原因
- 最终响应来源

都进入了正式 schema，而不是继续散落在代码里。

一句大白话：

- **这轮把 hotpost 从“接口在说人话，但结构还靠猜”，收成了“接口说人话，结构也正式定下来了”。**

---

## 5. 验证结果

### 定向 hotpost 合同回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/hotpost/test_hotpost_schema.py \
  tests/services/hotpost/test_hotpost_summary.py \
  tests/services/hotpost/test_hotpost_query_resolver.py \
  tests/services/hotpost/test_hotpost_report_llm.py \
  tests/api/test_hotpost.py -q
```

结果：

- `15 passed`

### hotpost 服务整组回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost -q
```

结果：

- `47 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 6. 这轮还暴露了什么残留点？

这轮第一刀已经把最容易漂的接口层收住了，但 hotpost 模块还留着两个后续值得继续看的点：

1. `service.search()` 本体仍然偏大  
   - 虽然 `debug_info` 构造已收口
   - 但整条 `search()` 仍然知道太多事
   - 第二轮如果继续做，更适合往职责拆分走

2. `report_export.py` 仍然在按“兼容 dict / model_dump”两套方式读  
   - 这轮先保证不破兼容
   - 后面如果继续收结构，可以逐步去掉“兼容旧 dict”思路

一句话：

- **这轮先把 hotpost 最容易漂的接口合同锁住了；下一轮如果继续做，重点应该是结构降耦合，而不是再补字段。**

---
