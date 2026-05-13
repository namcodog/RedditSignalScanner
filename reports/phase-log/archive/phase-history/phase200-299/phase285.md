# Phase 285 - 分析模块第一轮整治：结构化 LLM 状态显式化 + 旧测试对齐当前合同

> 时间：2026-03-15
> 模块：分析模块
> 范围：`analysis_engine` 结构化报告子链 + 分析模块旧测试合同对齐
> 当前状态：已完成第一轮

---

## 1. 发现了什么？

这轮先没有去拆整个 `analysis_engine.py`，因为那会把范围炸开。
第一刀盯的是分析模块里最影响闭环可信度的点：

- 结构化报告 LLM 子链以前会把很多完全不同的情况，都压成一个 `None`
- 下游最后只能看到：
  - `llm_used = False`
  - `llm_model = None`
  - `llm_rounds = 0`

这会导致外层完全分不清：

- 是故意跳过了结构化 LLM
- 还是缺 key
- 还是 facts 不够
- 还是 LLM 真的炸了
- 还是返回了坏 JSON

一句大白话：

- **以前这条子链没产出时，只会告诉你“没结果”，不会告诉你“为什么没结果”。**

另外，这轮还顺手照出了 3 条旧测试漂移：

1. 两条测试还拿旧的 `analysis_duration_seconds < 200` 当硬断言
   但当前实现里这是合成估算值，而且上限已经明确 clamp 到 `260`
2. 一个优先级排序测试写死了社区名，碰到脏 DB 会撞唯一键
3. 两条“无外部依赖”测试没有屏蔽 `discovered_communities` 副作用，容易混入与测试目标无关的写库噪音

也就是说，这轮真正的问题分成两层：

- **代码层：结构化 LLM 状态说得不够真**
- **测试层：旧测试还停在旧世界**

---

## 2. 是否需要修复？

需要，而且这轮已经修完第一刀。

这次没有改数据库 schema，也没有新增 migration。
做的是两件事：

1. 把结构化报告 LLM 子链改成显式状态合同
2. 把 3 条旧测试对齐到当前真实合同，不再把主逻辑往旧世界拉回去

---

## 3. 精确修复方法？

### 3.1 结构化报告 LLM 子链显式化

修改：

- `backend/app/services/analysis/analysis_engine.py`

新增：

- `StructuredReportRenderResult`
- `_structured_llm_skipped(...)`

把 `_render_structured_report_with_llm(...)` 从“返回 `dict | None`”改成“返回结构化结果对象”。

统一后的状态口径是：

- `completed`
- `skipped`
- `failed`

同时明确补出：

- `reason`
- `model`
- `rounds`

现在这些情况终于能分开说了：

- `tier_skipped`
- `llm_summary_disabled`
- `local_extractive_mode`
- `missing_api_key`
- `missing_facts_slice`
- `llm_generate_failed`
- `invalid_json_payload`

也就是说：

- **这条子链不再只会说“没结果”，而是会明确说“为什么没结果”。**

### 3.2 `run_analysis(...)` 的来源字段同步收口

现在 `sources` 里会明确补出：

- `structured_llm_status`
- `structured_llm_reason`
- `llm_used`
- `llm_model`
- `llm_rounds`

并且在不足样本的 early return 分支里，也会显式写：

- `structured_llm_status = skipped`
- `structured_llm_reason = insufficient_samples`

这样 facts / report / 外层调用方，不会再把“样本不够所以没走 LLM”和“LLM 自己失败”混成一类。

### 3.3 旧测试对齐当前真实合同

修改：

- `backend/tests/services/analysis/test_analysis_engine.py`
- `backend/tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py`

这轮测试收口的原则不是“把测试改绿就算了”，而是：

- 让测试回到**当前真实模块合同**
- 不把主逻辑硬拽回旧口径

具体做了三件事：

1. 两条耗时断言改成当前真实合同：
   - `0 < analysis_duration_seconds <= 260`
2. “无外部依赖/快速 mock” 场景显式 monkeypatch：
   - `_record_discovered_communities`
   - `_check_trend_views_freshness`
   避免把无关副作用混进测试目标
3. 优先级排序测试改用唯一社区名 + 限定查询范围
   - 不再依赖当前 DB 恰好干净

---

## 4. 这轮结果是什么？

这轮的本质不是“分析结果更聪明了”，而是：

- **结构化报告 LLM 子链终于开始说真话**
- **分析模块旧测试也重新对齐到当前真实合同**

现在外层终于能区分：

- 是完整跑成了
- 是故意跳过了
- 还是 LLM 真失败了

这更符合系统总整治的准则：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

---

## 5. 验证结果

### 定向 3 条旧失败用例

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/analysis/test_analysis_engine.py::test_run_analysis_fast_with_mocked_database \
  tests/services/analysis/test_analysis_engine.py::test_priority_order_prefers_high_over_medium_low \
  tests/services/analysis/test_analysis_engine.py::test_run_analysis_produces_signals_without_external_services -q
```

结果：

- `3 passed`

### 分析模块整组回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/analysis/test_analysis_engine.py \
  tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py -q
```

结果：

- `33 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 6. 这轮还暴露了什么残留点？

这轮虽然已经把第一刀收住，但我顺手又抓到了分析模块下一轮该看的两个真实点：

1. `discovered_communities` 在“瞬时 TaskSummary / 非持久化 task id”场景下还会打 FK 警告
   - 这不影响主链结果
   - 但说明“分析任务上下文”和“发现社区副作用”之间还存在合同不够干净的地方

2. 语义检索 / hybrid retrieval 里，`tsquery` 拼接还可能因为带空格短语和标点，自己把自己打成降级
   - 这不是测试夹具问题
   - 是分析模块下一刀值得优先处理的真实问题

一句话：

- **这轮先把“结构化 LLM 状态说不清”收住了，下一轮该看“发现社区副作用”和“tsquery 自降级”这两个深层点。**

---

## 7. 下一步系统性的计划是什么？

按总整治节奏，分析模块这一轮先到这里。

下一步有两种走法：

1. 继续留在分析模块，做第二刀
   - 优先收 `tsquery` 自降级
   - 再看 `discovered_communities` 副作用合同

2. 按整机节奏先推进下一个模块
   - 先让整机第一轮都到位
   - 后面再回头做分析模块第二轮降耦合

当前更稳的做法是：

- **先记账这两个残留点，继续按整机节奏推进下一个模块**
