# Phase 458 - 项目架构全面评估：保留底座，重整分析中段主链

## 发现了什么？

这轮不是继续修某个 bug，而是重新判断：当前项目架构还适不适合稳定产出你要的 `Full A` 报告。

结论很清楚：

- **不是整个项目都不合理**
- **但现在的分析中段主链已经不合理**

### 仍然合理、应该保留的部分

1. **数据底座是有价值的**
   - `community_pool / community_cache / posts_raw / comments / post_scores` 这些核心数据资产和冷热分层没有方向性错误。
   - DB Atlas、三库规则、控制塔模式都属于对的底座。

2. **产品主链的大框架是对的**
   - `API -> task -> analysis -> report -> frontend`
   - 这条链的业务概念没有问题。

3. **交付真相源方向是对的**
   - `canonical_report_json` 作为唯一交付真相源，这个方向是对的，也应该继续保留。

### 已经不合理、必须重整的部分

1. **分析主链边界脏了**
   - `analysis_engine.py` 已经接近 God Object：
     - 做路由
     - 做社区筛选
     - 做证据过滤
     - 做洞察组织
     - 做补量和部分事实组织

2. **兼容层已经膨胀成第二套分析引擎**
   - `analysis_payload_loader.py`
   - `structured_report_fallback.py`
   - 这两层原本应该只是兼容/兜底。
   - 但现在已经在补 pain、补机会、补证据、补业务话术。
   - 这意味着系统不是“分析成功 -> 报告装配”，而是“分析不够 -> 后面继续补”。

3. **报告装配层仍在补洞**
   - `report_assembly_workflow.py` 逻辑上应该只装配。
   - 现实里它还在承接 structured / narrative / controlled markdown 等多条补偿分支。
   - 这会继续掩盖上游问题。

4. **worker 执行合同不干净**
   - inline fallback
   - Celery 正式 worker
   - auto rerun
   - 手工 live worker
   - 这几套模式并存，已经出现过旧 shell 拉起重复 worker、live 结果被环境污染的问题。

5. **数据库读取方式不聪明**
   - 不是 DB 没信息，而是现在没有一层“面向报告的证据账本”。
   - 每一层都在自己重取数据、重猜语义、重补缺口。
   - 所以后面越来越像在拼 JSON 补丁，不像在稳定地产生洞察。

## 是否需要修复？

需要，而且不是继续修补同一套中段。

这轮的明确判断是：

- **不需要重做整个产品**
- **也不建议整仓重写**
- **但必须重整分析中段主链**

## 精确修复方法？

### 新主链边界

应该拆成下面 5 段：

1. `Topic Routing`
   - 只负责把问题路由到正确 warzone / 社区宇宙
   - 不负责生成 pain / opportunity

2. `Evidence Selection / Evidence Ledger`
   - 只负责从 DB/缓存里选出和当前问题真正相关的帖子/评论
   - 输出一份可审计、可回指的 evidence ledger
   - 没选到合格证据，就显式失败，不进入下一步

3. `Insight Synthesis`
   - 只从 evidence ledger 里生成 pain / driver / opportunity
   - 不能从产品描述里反推“看起来合理的痛点”

4. `Canonical Report Assembly`
   - 只把已经成立的洞察装成 `canonical_report_json`
   - 不再补 pain、补证据、补战场

5. `Worker / State Orchestration`
   - 统一 queue、worker、auto-rerun 和状态机
   - 一条任务只能有一套执行合同

### 对旧代码的处理原则

- `analysis_payload_loader.py`
  - 降级成 legacy adapter
  - 不再继续扩张领域硬编码
- `structured_report_fallback.py`
  - 降级成 legacy compatibility layer
  - 不再承担正向分析职责
- `analysis_engine.py`
  - 逐步瘦身，把 routing / evidence selection 拆出去

## 下一步系统性的计划是什么？

### 第 1 阶段：冻结补丁扩张

- 停止继续往 `analysis_payload_loader.py` / `structured_report_fallback.py` 塞更多领域规则
- 停止继续用报告层补洞来掩盖上游问题

### 第 2 阶段：重整执行合同

- 固定 live worker 启停 SOP
- 固定 queue 与 worker 对应关系
- 先解决“环境污染”和“代码问题”混在一起的问题

### 第 3 阶段：重做 Evidence Selection

- 建一层通用 evidence ledger
- 让所有后续 pain / opportunity / evidence_chain 都从这份 ledger 来

### 第 4 阶段：重做 Insight Synthesis

- 只允许从证据簇里产 pain / driver / opportunity
- 没证据就不能产“像结果的结果”

### 第 5 阶段：切回 Full A 主链

- 把新的 insight 输出接回 `canonical_report_json`
- 再接 narrative 长报告
- 最后才回到前端验收

## 这次执行的价值是什么？

这轮最大的价值，不是又修好了一条题目。

而是把整个问题看清楚了：

- 不是“项目没救了”
- 不是“必须推倒重来”
- 也不是“再补几个规则就会自然变好”

更准确的结论是：

- **底座值得保留**
- **中段必须重整**
- **外部交付标准不变，内部生产流水线重做**

这意味着后面终于可以从“边修边猜”切到“按边界重构”了。
