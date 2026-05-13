# Phase 530 - Hotpost 算法优化系统方案收口

## 背景

- Phase 529 的冷 `opportunity` live 已把问题进一步收窄：
  - `top_quotes` 算法方向对
  - `market_opportunity` 投影方向对
  - 但结果仍不够硬
- 当前主问题不是架构，也不是模型，而是**召回精度**

## 集中判断

当前 Hotpost 需要停止“继续打零散 patch”，改成围绕 4 层做系统收口：

1. `Query Intent / Planning`
2. `Source Quality / Retrieval Precision`
3. `Evidence Packaging`
4. `Output Projection`

其中真正需要优先重做的是第 2 层，不是第 4 层。

## 根因拆解

### 1. Query Planner 还不够语义化

- 现在 `query_planner.py` 主要产出：
  - `core_terms`
  - `expanded_terms`
  - `candidate_subreddits`
- 但还缺：
  - 正向语义约束
  - 错误上下文约束
  - product-seeking vs generic-discussion 的区分

### 2. Retrieval 还停留在“词命中优先”

- `evidence_collection_workflow.py` 对 `opportunity` 的过滤仍偏粗：
  - 主要还是看关键词是否命中正文
- 这会让：
  - `eductionalpartner`
  - `mathshelper`
  - `OnlineHESIExam`
  这类垃圾/错误社区有机会混入候选池

### 3. Report 层现在是在替前面擦屁股

- `report_workflow.py` 已经做了 direct-hit 排序、评论去噪、payload 裁剪
- 但它发生得太后
- 前面 evidence pack 一旦脏了，后面再怎么润色也只能做保守输出

## 系统方案

### Step 1：先做 Source Quality / Retrieval Precision

新增轻量 source-quality 层，但保持配置驱动、不过度工程化：

- `subreddit quality profile`
  - trusted
  - suspicious
  - unknown
- `retrieval precision score`
  - query term direct hit
  - subreddit fit
  - content shape
  - signal pattern
- 处理原则：
  - trusted：正常进入
  - suspicious：直接挡掉
  - unknown：允许进入，但降权

### Step 2：补 Query Planner 语义约束

`query_planner` 只做轻增强，不重写：

- 新增输出：
  - `positive_intent_terms`
  - `forbidden_context_terms`
  - `domain_terms`
- 明确区分：
  - product-seeking query
  - generic discussion query

### Step 3：保持 Evidence / Output 轻量

- `report_workflow`
  - 继续保留当前轻裁剪
  - 不继续堆复杂逻辑
- `quality_contract / enrichment`
  - 保持现状
  - 只做小的合同修正，不再作为主战场

## 执行顺序

1. 先做 source quality 配置和 retrieval precision score
2. 再补 query planner 的语义输出
3. 最后只跑最小 live matrix 验证：
   - 3 条关键词以内
   - 不扩大 Reddit 调用

## 结论

### 1. 发现了什么？

- Hotpost 当前的主问题已经不是架构问题
- 也不是输出层先坏
- 而是“召回精度不够，导致后续层被迫保守”

### 2. 是否需要继续修复？

- 需要
- 但必须从“系统方案”收，而不是继续零散 patch

### 3. 下一步系统性计划

- 直接进入 `Phase 102`
- 主题固定为：
  - `source quality`
  - `retrieval precision`
  - `query planner semantic constraints`

### 4. 这次执行的价值

- 把 Hotpost 下一段工作从“哪里都想修”收成了一个清晰方向：
  - **先修召回精度，再谈结果硬度**
