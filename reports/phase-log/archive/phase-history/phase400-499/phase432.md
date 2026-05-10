# Phase 432 - Full A 统一产品合同与系统合同固化

## 本轮目标
- 不再靠聊天维持共识，而是把 Full A 的最终产品合同写成正式 SOP。
- 把“分析真相源”和“交付真相源”彻底分开，避免后续实现继续漂。
- 简洁同步到 `key-os`，让后续所有运行时都能接上同一口径。

## 本轮结论

### 1. 两层真相源正式分开
- 分析真相源：`insights + facts_v2/facts_slice`
- 交付真相源：`canonical_report_json`

### 2. 主链正式写死
- `真实数据 -> insights + facts_v2/facts_slice -> LLM 固定结构生成 canonical_report_json -> 卡片视图 / 完整报告视图`

### 3. 双视图合同正式写死
- 卡片页和完整 Markdown/HTML 必须来自同一份 `canonical_report_json`
- 两边语义一致，只允许展示密度不同
- 前端不能自己再编一套解释

### 4. topic_profile 合同正式写死
- 首页标准卡 = 固定 canonical snapshot report
- 实时重跑 = 单独动作
- 不能再把 live 任务冒充标准展示结果

## 新增文档
- [docs/sop/2026-03-20-Full-A-统一产品合同与系统合同.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2026-03-20-Full-A-统一产品合同与系统合同.md)

## 四问收口
1. 发现了什么？
- 之前最大问题不是方向错，而是合同没写死，导致 `facts -> JSON -> 前端 -> markdown` 四层各自长语义。

2. 是否需要修复？
- 需要，而且这次先修合同，再修实现。

3. 精确修复方法？
- 先把 `analysis truth source / delivery truth source / dual-view rendering / topic_profile snapshot` 写成正式 SOP，再让后续主链改造全部对齐这份合同。

4. 下一步系统性的计划是什么？
- 进入下一阶段主链改造：
  - `facts` 层继续做真相源
  - `canonical_report_json` 升成正式交付骨架
  - 前端卡片和完整报告都改为只消费这份骨架

5. 这次执行的价值是什么？
- 把“我们脑子里知道要什么”变成“仓库里有正式合同、后续实现必须服从”的状态。
