# Phase 526 - Hotpost rant 结果硬度轻增强

## 背景

- Phase 525 已把 `rant` 的快层时延从约 `41.5s` 收到约 `23.6s`
- 但结果还不够硬，仍会混进泛客服抱怨和 moderator 噪音
- 这轮目标不是再扩架构，而是继续把 `fast` 拉回“结构化证据整理层”

## 本轮执行

### 1. 让 report payload 更偏 query 相关证据

- `backend/app/services/hotpost/report_workflow.py`
  - 新增 `_query_terms()` / `_text_hit_count()`
  - `rant` 帖子不再只按原顺序进模型，而是先按 query 相关性重排
  - 相关性主要看：
    - `title`
    - `why_relevant`
    - `body_preview`
    - `signals`

### 2. 把 moderator / 太短评论挡在模型外面

- `backend/app/services/hotpost/report_workflow.py`
  - 新增 `_comment_is_noise()`
  - 过滤：
    - `AutoModerator / mod / moderator`
    - 太短评论
    - 常见版规提醒文本
  - `post.key_quote` 也沿用同一套过滤，避免拿版规提醒当“代表原话”

### 3. 测试

- `backend/tests/services/hotpost/test_hotpost_report_workflow.py`
  - 扩展 `_build_post()`，支持自定义 `id/title`
  - 新增：
    - `test_hotpost_report_workflow_prioritizes_query_relevant_evidence`
  - 现有 compact context 测试也补了 moderator 评论场景

- 回归：
  - `backend/tests/services/hotpost/test_hotpost_report_workflow.py`
  - `backend/tests/services/hotpost/test_hotpost_search_workflow.py`

## 验证

### 定向测试

- `pytest backend/tests/services/hotpost/test_hotpost_report_workflow.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
  - `14 passed`

### 最小 live 对照

- 查询：`shopify chargeback dispute complaints`
- 结果：
  - `query_id = c19fb4dc-dd6b-4f02-9f7e-e3d79b841f53`
  - `status = completed`
  - `confidence = medium`
  - `report_source = llm`
  - `final_report_layer = fast`
- 阶段耗时：
  - `evidence_collection_ms = 3464`
  - `summary_ms = 5046`
  - `fast_report_ms = 15620`
  - `total_workflow_ms = 24187`
- 结果信号：
  - 前 3 个 pain 已集中到：
    - `Chargeback欺诈`
    - `纠纷败诉不公`
    - `财务巨额损失`
  - 不再像之前那样把“客服慢”放到最前面

## 结论

### 1. 发现了什么？

- 这轮不是继续救 Reddit，也不是继续救代理
- 真正有效的是：把 `fast` 喂得更像“代表性证据包”
- 一旦输入包收干净，`fast` 已经能直接产出可用的 `rant` 结果

### 2. 是否需要继续修复？

- 需要，但方向已经更窄了
- 当前剩余最明显的脏点，是 `migration_intent.key_quote` 还可能混进版规提醒
- 这轮已经在输入层补了过滤，但为了保护 Reddit API，没有再追加第二次 live 重跑

### 3. 下一步系统性计划

1. 先继续收 `rant / opportunity` 的结果硬度，不再扩架构
2. 优先把：
   - 代表性原话
   - 下一步动作建议
   - 噪音迁移意向
   再收干净一层
3. 只有当输出层继续进入低收益区，才考虑再碰 prompt 合同

### 4. 这次执行的价值

- `fast` 开始更像“结构化整理层”，不再只是一个容易跑偏的首版报告器
- `rant` 已经从“容易拖进 reasoning 兜底”变成“多数场景可直接 fast 完成”
- 这条线符合 Hotpost 当前约束：
  - 轻量
  - 不过度工程化
  - 不继续加大 Reddit API 风险
