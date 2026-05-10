# Phase 644 - Hotpost Mini Topic-Pack 合同锁定

## 结果

`hotpost-mini` 的内容口径合同已经锁定：

- 前端不变
  - 继续保持 `📡 信号 / 🔍 拆解`
- 后端重排供给
  - 不改 `source_scope`
  - 在每个 `source_scope` 下面增加 `topic-pack` 路由

## 核心决策

### 1. 电商

电商不再以：

- 运费
- 仲裁
- 成本
- 单位经济
- 平台问题

作为主供给。

改成：

- `selection-signals` 60%
- `category-winds` 25%
- `kill-signals` 15%

其中：

- `selection-signals` 是主供给
- `kill-signals` 只保留少量否决信号，不再主导电商 feed

电商选品信号的主覆盖方向锁定为：

- 宠物
- 咖啡
- 户外
- EDC
- 家居
- 3C（暂不单独升成新 scope）

### 2. AI

AI 卡改成 3 个 topic-pack：

- `upstream-winds`
- `tools-efficiency`
- `agent-builder`

### 3. 增长运营

增长卡改成 3 个 topic-pack：

- `paid-economics`
- `organic-discovery`
- `funnel-conversion`

## 边界

- 不新增前端“选品信号”标签
- 不新增新的 source scope
- 不复用主系统 warzones 数据链
- 不把“选品信号”做成“爆品推荐”

## 文档落点

正式合同已写入：

- [2026-04-07-hotpost-topic-pack-contract.md](../../docs/superpowers/specs/2026-04-07-hotpost-topic-pack-contract.md)

## 当前判断

这轮已经把“范围讨论”收成了可执行合同。
下一步不再讨论前台标签，而是可以直接进入：

- `source_scope_catalog`
- `reddit_search_spec_builder`
- 电商社区与关键词重排
