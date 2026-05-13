# CEO Review: 主项目借鉴小程序机制瘦身
Date: 2026-05-07
Branch: feat/hotpost-cluster-aware-recall

## 方案愿景

不是把主项目做成小程序，也不是把完整分析降级成卡片流。

目标是把小程序已经证明有效的产品机制拿回来：真相源分层、gate、不可变发布资产、前台只读、派生产物不手修。用这些机制让主项目重采集路线变轻，让深分析只在证据就绪后发生。

```text
当前：输入后默认容易拉动重采集 + 大分析 + 大报告
  -> 本方案：先 readiness snapshot + decision gate，再决定是否深分析
  -> 理想：主项目保留深分析，但每一步都有可检查 artifact，重采集不再默认前置
```

## 前提挑战

1. 这是对的问题吗？
   是。主项目当前最重的不是报告服务，而是采集/分析前置链。审计已确认 `ReportService` 已解耦，继续盯它不是最优。

2. 有没有更简单方案？
   有：只做 `analysis_engine.py` 已有 support 模块的边界回收，不新增产品页、不新建表、不重写 crawler。

3. 如果什么都不做会怎样？
   主项目可以继续靠 smoke 测试证明“能跑”，但产品验收仍慢；后续 agent 很可能继续在 `analysis_engine.py` 里补逻辑，让文件更大、采集更重。

## 范围决策表

| 提案 | 工作量 | 决策 | 原因 |
| --- | ---: | --- | --- |
| 把主项目改成小程序式浅扫描 | M | 拒绝 | 用户已明确指出小程序分析浅，不能和主项目比。 |
| 借小程序发布机制做主项目瘦身 | M | 采用 | 借的是机制，不是分析深度；能解决重采集默认前置。 |
| 直接大拆 `analysis_engine.py` | L | 拒绝本轮 | 没有产品 gate 先行，容易变成无目标拆文件。 |
| 重做 `ReportService` 解耦 | M | 拒绝 | phase-log 和 Serena 已确认它基本完成解耦。 |
| 先收 readiness/remediation 单一真相源 | S/M | 采用 | 已有 support 模块和测试，是最小可逆第一刀。 |
| 同时清理脏仓 | XL | 拒绝 | 1474 条 dirty status 是独立治理问题。 |

## 已接受范围

- 建立主项目“产品机制瘦身”设计。
- 明确借鉴小程序的状态分层、gate、snapshot、只读前台。
- 第一刀只收 `analysis_engine.py` 中已有 support 模块能承接的逻辑：
  - readiness snapshot
  - insufficient sample artifacts
  - remediation / backfill scheduling
- 保留深分析、facts、canonical report。
- 保留旧私有函数名作为兼容 wrapper，避免旧测试和 monkeypatch 断裂。

## 延期内容

- 前端新增轻扫描或新页面。
- 新 DB 表。
- 重写 crawler。
- 大规模拆 `run_analysis`。
- 清理整个 dirty worktree。
- 任何 Hotpost / 小程序功能改动。

## 推荐模式

**SCOPE REDUCTION**。

先做一刀小而硬的工程动作：把已经存在的 support 模块变成真实单一真相源。等这刀通过测试，再讨论是否继续把 `run_analysis` 的深分析阶段分段。

## 成功标准

- 不降低主项目分析深度。
- `analysis_engine.py` 减少直接拥有的 readiness/remediation 细节。
- 后端主线 smoke 继续通过。
- 前端 report contract 继续通过。
- 小程序子仓保持干净。
