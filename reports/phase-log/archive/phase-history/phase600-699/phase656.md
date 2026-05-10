# Phase 656 - Signal Eval Set V1 合同

## 结果

`signal eval set v1` 已完成正式合同设计。

这意味着：

- `card skill optimization` 不再停留在抽象方向
- 第一块真正可执行的地基已经锁定

正式文档：

- `docs/superpowers/specs/2026-04-07-signal-eval-set-v1-contract.md`

## 核心判断

这次最关键的决定有 4 条：

1. `signal eval set v1` 只服务于 `validate`
2. eval unit 必须是：
   - 输入 bundle
   - 输出卡片
   - 人工标注
3. 样本来源走 `mixed real-first`
   - 真实样本为主
   - synthetic 只补边
4. V1 不上复杂量表，只做：
   - 字段级 pass/fail
   - 整卡级 pass/fail

## 当前合同

V1 目标量：

- `48` 条

来源结构：

- `36` 条真实样本
- `12` 条 synthetic 边角样本

覆盖维度：

- `source_scope`
- `topic_pack`
- `signal_level`
- `intent heat`
- `evidence strength`
- `case polarity`

## 当前判断

这轮之后，下一步就不该再讨论“eval set 大概要怎么做”，而是可以直接开始拉样本。

也就是说：

**现在已经到了可以进入 `signal_eval_set_v1` 真实构建阶段的时候。**
