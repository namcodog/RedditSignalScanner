# Phase 307 - 第三轮下一刀：facts/报告模块最终 payload 组装独立

> 时间：2026-03-16  
> 模块：facts / 报告模块  
> 范围：`ReportService`、最终报告 payload 组装、overview/metadata/summary/builders  
> 当前状态：已完成第三轮这一刀

---

## 1. 发现了什么？

第三轮继续回到 facts / 报告模块后，这一刀没有再去拆 market workflow，而是继续盯 `ReportService` 里剩下最重的那坨：

1. **analysis payload 已经验证完了，但最终报告对象仍然由 `ReportService.get_report()` 自己一路手工拼出来**
   - stats
   - overview
   - executive summary
   - market health
   - metadata
   - entity leaderboard
   - recovery 标记
   - 最终 `ReportPayload`

2. **主服务还在同时背编排和 payload 组装**
   - 前面已经把市场工作流拆掉了
   - 但最终“把分析结果变成正式报告对象”这件事，仍然缠在主服务里

一句大白话：

- **前两刀把报告链里最重的市场工作流拆开了，这一刀继续把“最终报告怎么装出来”从主服务里抽出去。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。  
这轮做的是结构性收口，不是报告内容降级。

---

## 3. 精确修复方法？

### 3.1 新增正式 payload builder 层

新增：

- `backend/app/services/report/report_payload_builder.py`

这层正式接管了原来挂在 `ReportService` 里的最终报告组装职责：

- `ReportPayloadBuildInput`
- `build_report_payload(...)`
- `build_report_stats(...)`
- `build_report_overview(...)`
- `build_report_summary(...)`
- `build_market_health(...)`
- `build_report_metadata(...)`
- `build_entity_leaderboard(...)`

也就是说，现在不是：

- `ReportService` 既查任务、又做编排、又自己拼完整 payload

而是：

- **主服务继续做编排**
- **payload builder 专门负责把 analysis 结果整理成最终报告对象**

### 3.2 `ReportService` 收成更薄的 orchestration 层

修改：

- `backend/app/services/report/report_service.py`

这轮之后：

- `get_report()` 不再自己手工拼：
  - stats / overview / summary / market_health / metadata / payload
- 而是改成：
  1. 继续处理 task / analysis / 质量闸门 / LLM 增益 / controlled markdown
  2. 把最终对象组装委托给 `build_report_payload(...)`

同时，原本暴露给测试和少量调用点的这些 helper 仍然保留为**薄委托**：

- `_build_stats(...)`
- `_build_overview(...)`
- `_build_summary(...)`
- `_build_market_health(...)`
- `_build_metadata(...)`

这样做的目的不是继续养双份逻辑，而是：

- **先把主服务瘦下来**
- **同时保住旧 seam，不让这一刀把现有测试和兼容链路打碎**

### 3.3 新增 builder 测试，并顺手修掉一组老测试噪音

新增：

- `backend/tests/services/report/test_report_payload_builder.py`

专门锁住：

- builder 会正确吃 `render_bundle`
- 会正确把 `market_enhancements / llm_used / top_communities.members` 带进最终 payload

另外还顺手修了一组老测试：

- `backend/tests/services/report/test_report_service_member_count.py`

这组测试之前的社区名写死成固定值，后来我额外跑时暴露出两个老问题：

1. 容易和已有测试/库数据撞唯一键
2. 新生成的临时名用了 `-`，又会撞 `community_cache` 的名字格式约束

这轮把它改成了：

- 每次生成合法、唯一的临时社区名

一句大白话：

- **这轮不只是拆了主服务，还顺手把一组容易“环境一脏就红”的老测试收稳了。**

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“报告更花”或者“字段更多”，而是：

- `ReportService` 继续往真正的编排层收
- 最终 payload 组装开始有自己的正式边界
- 后面继续拆 facts 整理、兼容壳、输出壳，会顺很多

一句大白话：

- **这刀把“最终报告对象怎么装出来”从主服务里抽成了独立齿轮。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_payload_builder.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_render_bundle.py \
  tests/services/report/test_market_workflow.py \
  tests/services/report/test_report_service_t1_market_md.py \
  tests/services/report/test_report_service_market_mode.py -q
```

结果：

- `25 passed`

### 兼容测试

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_service_member_count.py -q
```

结果：

- `7 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/report/report_payload_builder.py \
  backend/app/services/report/report_service.py \
  backend/tests/services/report/test_report_payload_builder.py \
  backend/tests/services/report/test_report_service_member_count.py
```

结果：

- 通过

---

## 6. 结构结果

这一刀之后，最直观的变化是：

- `backend/app/services/report/report_service.py`
  - 从 `1766` 行（第三轮前）继续降到 `1428` 行
- 新增：
  - `backend/app/services/report/report_payload_builder.py`
  - `533` 行，专门承接最终 payload 组装层

也就是说：

- **主服务继续变薄**
- **最终报告组装开始独立**

---

## 7. 这轮之后还剩什么？

facts / 报告模块第三轮这一刀之后，还剩几个继续值得打磨的点：

1. `ReportService` 仍然整体偏大
2. 结构化 markdown / controlled html / audit 写盘这几块后面还能继续拆
3. 兼容入口还在，但已经越来越薄

所以这轮的正确定位是：

- **第三轮这一刀已经把最终 payload 组装拆出来了**
- 但不是 facts / 报告模块第三轮全部完成

---

## 8. 下一步系统性的计划是什么？

按第三轮当前节奏，下一步继续打最重的剩余耦合点：

- 数据采集模块
- 语义 / 标签模块
- 或 facts / 报告模块下一刀（structured markdown / audit / controlled html 编排）

优先原则不变：

- 继续打最重的几组齿轮
- 继续把“主服务既编排又亲手组装”的地方拆成单一职责
- 继续把整机往 `95+` 的产品级稳定状态推进

一句话：

- **这刀先把最终报告 payload 组装拆出来了，后面继续按同样节奏稳稳打磨。**
