# Phase 263 - Round 4 深度审计（爆帖 + LLM + 基础设施）

## 目的
- 对 Round 4 范围做一次只读深审，先把“子系统层还会怎么说假话”查清楚
- 不急着修功能，先把爆帖链路、LLM 链路、基础设施链路里的假健康、假成功、来源混淆统一成一套口径

## 审计范围
- `backend/app/services/hotpost/`：13 文件 / 3,354 行
- `backend/app/services/llm/`：15 文件 / 2,284 行
- `backend/app/services/infrastructure/`：13 文件 / 2,597 行
- `backend/app/tasks/llm_label_task.py`：1,014 行
- `backend/app/tasks/monitoring_task.py`：836 行
- 合计：**43 文件 / 10,085 行**

## 方法
- `Serena`：做符号级定位，先确认关键入口和高风险函数
- `Sequential Thinking`：把“哪些是真问题、哪些只是代码味道”收敛成几条主风险链
- `Exa Code`：对照外部最佳实践，校准“失败语义、降级状态、可观测性”口径
- 定量扫描：统计 `except`、`type: ignore`、`NOW()`、`return_exceptions=True`

## 定量扫描结果
- `except`：**74**
- `type: ignore`：**22**
- `NOW()`：**13**
- `return_exceptions=True`：**2**

## Round 4 的统一口径
- Round 4 真正要解决的是：
  - **爆帖层会把真实结果、缓存结果、兜底结果混着说**
  - **LLM 层会把失败压成空结果或模糊成功**
  - **基础设施和监控层会表面健康，实际已经降级**
- 用大白话说：
  - Round 1 修的是“采集层不骗人”
  - Round 2 修的是“加工层不变味”
  - Round 3 修的是“社区治理和语义层不静默放错源”
  - **Round 4 要修的是“子系统层不再假健康、不再假成功、不再把兜底冒充正式结果”**

## 发现的核心问题

| 风险 | 模块 | 问题 | 说明 |
|------|------|------|------|
| 🔴 | `monitoring_task.py` + `infrastructure/*` | 监控和基础设施会“假健康” | `monitor_cache_health()` 自己的实体率计算、维护任务失败后只打 warning，最后仍返回正常 payload；`monitor_contract_health()` 告警审计写库失败会直接吞掉；Round 4 范围内仍有 **13 处 `NOW()`**，说明这层的时间口径和确定性协议还没完全收口 |
| 🔴 | `llm/clients/openai_client.py` + `llm_label_task.py` | LLM 会“假成功” | `OpenAIChatClient` SDK 失败后直接退 raw HTTP，再失败就返回空字符串；`llm_label_task` 批量标签里大量 `except Exception -> rollback -> continue`，但最终仍统一返回 `{\"status\": \"ok\"}`，外面看不出这次是完整成功还是部分失败 |
| 🔴 | `hotpost/service.py` + `hotpost/query_resolver.py` + `hotpost/report_llm.py` | 爆帖结果“来源混了” | 中文 query 翻译失败会直接回原词；LLM summary/LLM report 失败会退 fallback 或 `None`；最后 `search()` 仍然返回 `status=\"success\"`，并把实时结果、缓存结果、LLM 注解、规则兜底混到同一份 payload 里 |
| 🟡 | `reddit_client.py` | 外部源失败语义不统一 | 有的地方 `gather(return_exceptions=True)` 后再整体抛错，有的地方按 slice 吞掉单段失败继续返回部分结果，有的地方解析失败只记日志；调用方很难统一知道“这次是全成功、部分成功还是降级成功” |
| 🟡 | `scheduler_service.py` + `subreddit_snapshot.py` + `llm_label_task.py` | 时间和状态协议还散 | `scheduler_service.py`、`subreddit_snapshot.py`、`llm_label_task.py` 仍直接用 `NOW()`；说明 Round 4 子系统层里还存在“当前时间 SQL”“成功状态”和“来源状态”各写各的情况 |

## 证据摘要
- `backend/app/tasks/monitoring_task.py`
  - `monitor_cache_health()` 里仍有 `NOW() - INTERVAL '60 minutes'`
  - 监控子步骤失败后只留 warning，不把 `degraded` 明确带回结果
- `backend/app/tasks/llm_label_task.py`
  - `_label_posts_batch()` / `_label_comments_batch()` 的单项失败会被吞掉
  - 包装任务 `label_posts_batch()` / `label_comments_batch()` 只记 `processed`，不记失败数和降级状态
- `backend/app/services/llm/clients/openai_client.py`
  - 用 `print(...)` 代替结构化日志
  - Provider 失败直接返回空字符串，调用方拿不到错误类别
- `backend/app/services/hotpost/query_resolver.py`
  - query 翻译失败直接退 `source=\"fallback\"`
- `backend/app/services/hotpost/service.py`
  - LLM summary / LLM report 失败后静默退回
  - 最终仍统一返回 `status=\"success\"`
- `backend/app/services/infrastructure/reddit_client.py`
  - 同一个客户端内部同时存在“整体抛错”和“吞局部失败继续返回”的两种协议

## 下一步修复顺序（Round 4 深修）
1. **先修基础设施和监控**
   - 目标：监控不能再假健康，基础设施不能再“坏了也像没坏”
   - 优先文件：`monitoring_task.py`、`reddit_client.py`
2. **再修 LLM 客户端和标签任务**
   - 目标：LLM 失败不能再压成空字符串或 `status=ok`
   - 优先文件：`llm/clients/openai_client.py`、`llm_label_task.py`
3. **最后修 hotpost**
   - 目标：把“真实结果 / 缓存结果 / fallback / LLM 注解”分层说清楚
   - 优先文件：`hotpost/service.py`、`hotpost/query_resolver.py`、`hotpost/report_llm.py`

## 这轮审计的工程价值
- 这轮不是多找几个 `except`，而是把 Round 4 的问题统一成了一句能说人话的结论：
  - **子系统层还会表面正常、实际已降级**
- 后续深修的目标也已经清楚了：
  - 成功就是真成功
  - 降级就明确写成降级
  - 失败不能再伪装成空结果或绿色状态

## 结论
- Round 4 审计已完成
- 当前状态应定义为：**“已审计，待深修”**
- 下一步直接进入 Round 4 深修实现即可
