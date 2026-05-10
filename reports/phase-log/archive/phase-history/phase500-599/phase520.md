# Phase 520 - DB / 语义真相源重构升级为当前 P0

时间：2026-03-27

## 本轮决定

这件事不再定义为“后续要考虑的重构”。

从现在开始，它就是：

## 当前项目收尾前置条件

也就是说：

- 在 `community_pool / community_cache / category_map / 语义库` 失配没有收口前
- 不继续扩大 live 验收
- 不把当前单题 `A_full` 当最终产品能力

## 为什么必须现在做

因为如果不现在处理，项目会永远停在这种状态：

1. 单题偶尔能跑通
2. 横向一扩就飘
3. 数据真相、社区真相、语义真相各说各话
4. 每次都怀疑题干、怀疑 prompt、怀疑 live

这不是收尾，而是拖延。

## 当前新的项目顺序

1. 先做 DB + 语义真相源重构
2. 再做 readiness scan
3. 再做 analysis/backfill/warmup 主链适配
4. 最后恢复矩阵验收和一键收口

## 当前最小闭环目标

不是一步到位重做所有数据库。

而是先做这四件事：

### 1. 真相源矩阵冻结

明确：

- 内容真相
- 社区真相
- 语义真相

分别是谁。

### 2. 社区层新真相源落地

先让以下结构成为可运行真相源：

- `community_registry`
- `community_domain_membership`
- `community_governance_decision`
- `community_runtime_state`

### 3. 语义层新真相源落地

保留：

- `semantic_terms`
- `semantic_concepts`

并新增统一语义观测账本。

### 4. 主链切适配层

让：

- analysis route
- backfill
- warmup
- readiness
- evidence ledger

开始优先读新真相源。

## 当前停止线

在这四步没站住之前：

- 不再扩大 8 领域 live 验收
- 不再靠“换题干”去试系统
- 不再把局部 `A_full` 当成最终收尾证明

## 价值

这一步的意义是把项目从：

> 一边修结果，一边猜底层

改成：

> 先把底层真相源立住，再谈结果是否稳固

这才是真正的收尾路线。
