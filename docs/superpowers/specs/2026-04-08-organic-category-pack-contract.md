# Organic + Category Pack Contract
Date: 2026-04-08

## 目标

这轮只做两条 pack：

1. `organic-discovery`
2. `category-winds`

顺序固定：

1. 先做 `organic-discovery`
2. 再做 `category-winds`

## 范围

复制的是已经跑通的方法：

- `eval`
- `judge`
- `canary`
- `promote`

不复制具体文案。

## 实施顺序

### Phase 1：organic-discovery

先判断当前状态属于哪一类：

- 供给问题
- readiness 问题
- 已经可以开 canary

然后只按当前真实状态推进，不硬跳步骤。

### Phase 2：category-winds

在 `organic-discovery` 得出阶段结论后，再按同样方法推进。

## 边界

- 不同时推进两个 pack 的 prompt 实验
- 不因为范围扩大重新碰 `tools-efficiency`
- 不为了补全 pack 数量降低 `signal input quality gate`
- 不把这轮范围扩成新一轮 breakdown 优化

## 完成标准

### organic-discovery

至少达到下面两种结果之一：

- 跑出 pack 级 `keep`
- 或明确验证“不值得继续投入”，并说清原因

### category-winds

同上。

## 最终目标

不是“把 pack 数量做多”，而是：

- 再做出 1-2 条真正成熟的 pack
- 或明确证明哪些 pack 现在还不值得做
