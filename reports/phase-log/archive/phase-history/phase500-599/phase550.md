# Phase 550 - AIGC 运行时复核与小程序旧结果澄清

## 时间
- 2026-03-28

## 发现了什么
1. 用户在小程序里看到的 `AIGC` 页面仍是 `0 条相关证据`，但这不是当前后端的真实结果。
2. 运行时重新拉起唯一后端实例后，直接复跑 `AIGC`，后端立即返回了完整结果：
   - `status = completed`
   - `evidence_count = 30`
   - `confidence = high`
   - `communities = ["generativeAI", "aivideo"]`
3. 这次真实结果已经证明：
   - `AIGC` 不是真的没数据
   - alias 口径已经生效
   - 首轮实际 query part 已变成 `generative ai`
4. 因此，用户看到的 `0 条证据` 页面，本质上是旧 query 对应的旧结果，不是当前逻辑的新结果。

## 是否需要修复
- 后端检索口径这一层，当前不需要再修。
- 当前需要做的是让用户重新触发一次新的 `AIGC` 查询，拿到新 query 对应的新结果。

## 精确核实结果
- 复跑请求：
  - `POST /api/v1/hotpost/search`
  - `query = AIGC`
  - `mode = trending`
- 终态结果：
  - `query_id = b0925918-ed27-4a5d-a52a-f476f106fc71`
  - `status = completed`
  - `summary = 当前最明确的信号是AI生成内容（尤其是虚拟人/视频）的“真实感”挑战与成本限制，社区讨论集中且有分歧。`
  - `debug_info.query_parts = ["generative ai"]`
  - `debug_info.expanded_terms = ["generative ai", "ai-generated content", "gen ai", "trend", "discussion", "adoption"]`
  - `debug_info.time_filter = "month"`
  - `debug_info.final_report_layer = "reasoning"`

## 验证
- 重新启动单一后端实例
- 直接通过 API 复跑 `AIGC`
- 轮询终态结果，确认命中：
  - 30 条证据
  - 近 30 天
  - reasoning 层完整输出

## 这次执行的价值
- 把 `AIGC` 这条彻底钉死了：
  - 不是 Reddit 没数据
  - 不是 alias 修复无效
  - 是用户端还停留在旧结果画面
- 这一步把“算法口径问题”和“旧结果展示问题”分开了，避免后面继续误判。
