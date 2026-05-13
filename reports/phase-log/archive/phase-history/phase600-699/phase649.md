# Phase 649 - Breakdown Supply 合同锁定

## 结果

“拆解为什么少”这件事已经从感受问题，收成了正式产品/工程合同。

本轮锁定的不是 prompt 文案，而是拆解供给机制：

- `📡 信号` = 日报产品
- `🔍 拆解` = 近 `48h - 7d` 的滚动聚合产品

## 核心决策

### 1. 自动化边界

V1 只自动做到：

```text
collect -> signal candidates -> breakdown suggestions
```

不自动 publish。

人工保留在：

```text
suggestion -> seed-group -> draft -> review -> publish
```

### 2. 触发门槛

拆解 suggestion 需要同时满足：

- 同一个 `source_scope_id`
- 同一个 `topic_pack_id`
- 至少 `2` 条 candidate
- 至少 `2` 个帖子
- 至少 `2` 条非重复 quote
- 能写出一句“误判纠正句”

### 3. 明确禁止

- 单帖升拆解
- 跨 scope 组卡
- 跨 topic-pack 组卡
- 用 prompt 把单帖硬写成深度卡
- 自动生成后直接自动上线

## 前端口径

前端不新增标签，只解释 `🔍 拆解`：

- 首页：`拆解：基于近几天多条相关讨论提炼，不是单帖总结。`
- 详情页：`这张拆解卡来自多条相关讨论的合并判断，用来帮助你看清同一个问题的更深层卡点。`

## 文档落点

正式合同已写入：

- [2026-04-07-breakdown-supply-contract.md](../../docs/superpowers/specs/2026-04-07-breakdown-supply-contract.md)
