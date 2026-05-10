# Phase 294 - facts/报告模块第二轮第一刀：受控渲染组装层收口

> 时间：2026-03-15
> 模块：facts / 报告模块
> 范围：`report_service`、受控 markdown/html 渲染、metrics summary 组装
> 当前状态：已完成第二轮第一刀

---

## 1. 发现了什么？

第二轮进入 facts / 报告模块后，这一刀没有继续补字段，而是先盯 `ReportService.get_report()` 里最缠的一层：

1. **同一个 `get_report()` 同时背了太多事**
   - 受控 markdown 生成
   - community market fallback
   - `market_enhancements` 注入
   - `metrics_summary` 组装
   - markdown → html 渲染
   - 最终 `ReportPayload` 组装

2. **渲染细节和最终 payload 输出还没有正式分层**
   - 第一轮已经把 `sources` 真相链打通了
   - 但“怎么把 controlled markdown 变成最终可输出的渲染结果”这层，仍然散在 `get_report()` 里

一句大白话：

- **第一轮让报告链开始说真话，第二轮这一刀开始把“渲染怎么拼”和“最终 payload 怎么出”拆开。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这轮做的是结构性收口，不是报告内容改版。

---

## 3. 精确修复方法？

### 3.1 抽出正式渲染结果对象

新增：

- `backend/app/services/report/render_bundle.py`

新增正式中间合同：

- `ControlledMarkdownResult`
- `ReportRenderBundle`

同时把原来散在 `get_report()` 里的纯组装逻辑收成统一 helper：

- `build_metrics_summary(...)`
- `build_report_render_bundle(...)`

这样现在 report 层不再是：

- 哪段逻辑想到什么就往局部变量里塞什么

而是：

- 先得到正式的 controlled result
- 再统一变成 report render bundle
- 最后才组装 `ReportPayload`

### 3.2 `ReportService` 主链少背一层渲染细节

修改：

- `backend/app/services/report/report_service.py`

这次把 `_build_controlled_report_markdown(...)` 从返回 tuple：

- `tuple[str | None, dict[str, Any], bool, str | None]`

收成返回：

- `ControlledMarkdownResult`

然后 `get_report()` 改成：

1. 先拿 `ControlledMarkdownResult`
2. 再调用 `build_report_render_bundle(...)`
3. 再把 bundle 的结果写进：
   - `metadata.market_enhancements`
   - `metadata.llm_used`
   - `report_html`
   - `metrics_summary`

一句大白话：

- **主服务现在更像编排层，不再继续自己手搓“markdown/html/metrics/market mode”这一大坨细节。**

### 3.3 顺手把两条旧测试拉回当前真实合同

这轮定向回归里冒出了两条旧测试漂移，不是这次 bundle 拆分打坏的，而是旧夹具没跟上当前真实 schema / layering 口径：

- `test_version_migration_preserves_existing_data`
- `test_report_service_adds_competitor_layers_summary`

处理方式不是改主逻辑回旧世界，而是：

- 把 fixture 补齐到当前 `AnalysisRead` schema
- 把竞争层断言改成对齐当前真实 layer contract，不再写死旧的 `workspace / analytics / summary`

这一步的意义是：

- **测试重新验证“现在真实怎么工作”，而不是继续拖着历史断言。**

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“报告内容更多了”，而是：

- 继续把 report service 从大杂烩往编排层方向收
- 让受控渲染组装层先独立成正式中间合同

这更符合第二轮目标：

- 职责更单一
- 接口更稳
- 高耦合点继续打薄

一句大白话：

- **这刀把报告链里最缠的“受控渲染组装层”先抽出来了，后面继续拆 facts 整理和输出壳会更顺。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_render_bundle.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_service_phase1_integration.py \
  tests/services/report/test_report_service_phase2_integration.py -q
```

结果：

- `24 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/report/report_service.py \
  backend/app/services/report/render_bundle.py \
  backend/tests/services/report/test_render_bundle.py \
  backend/tests/services/report/test_report_service.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

facts / 报告模块第二轮这一刀之后，还剩几个更大的结构问题没有做：

1. `ReportService` 本体仍然偏大
2. `market_enhancements` 仍然还挂在主服务里
3. facts 整理和最终输出壳之间，还能继续拆出更清楚的边界

所以这轮的正确定位是：

- **第二轮第一刀已经值回票价**
- 但不是 facts / 报告模块第二轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第二轮既定顺序，下一步进入：

- **数据采集模块** 的第二轮结构性收口

重点从第一轮的“状态说真话”，继续推进到：

- 调度 / 派发 / 执行 / 入库边界进一步拆清
- 大任务文件继续瘦身
- 状态协议从习惯写法继续收成稳定合同

一句话：

- **facts / 报告模块这刀先收到这里，下一步回到上游链路继续拆耦合。**
