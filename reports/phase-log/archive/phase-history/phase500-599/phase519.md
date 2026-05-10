# Phase 519 - 语义库必须并入主数据库架构

时间：2026-03-27

## 本轮目标

确认一个关键问题：

> 我们的“语义库”在新架构里到底是什么位置？

## 结论先说

语义库不是附属层。

它和：

- 原始内容层
- 社区/领域层

一样，都是主系统的真相源之一。

如果后续只重构社区池，不把语义库一起纳入设计，主链还是会缺半条腿。

## 当前仓库里语义库的真实落点

### 1. 语义知识层

- `semantic_terms`
- `semantic_concepts`

它们更像：

- 术语词典
- 概念字典
- 规范化语义 SSOT

### 2. 语义观测层

- `post_semantic_labels`
- `post_llm_labels`
- `comment_llm_labels`
- `content_labels`
- `content_entities`
- `post_embeddings`

它们更像：

- 某条帖子/评论在某个版本下被打出来的语义观测结果

## 当前真正的问题

不是没有语义库，而是：

### 语义库还没被收进主链架构

现在它更像一堆“侧边能力”：

- 打标签
- 做 embedding
- 帮分析

但还没有成为真正的系统合同。

这就带来三个问题：

1. query expansion 用一套语义
2. readiness 判断用另一套统计
3. 报告输出又用另一套业务翻译

最后系统虽然“有语义能力”，但没有统一语义真相。

## 正确的架构位置

后续系统应该变成三大真相源：

### 一、内容真相

- `posts_raw`
- `comments`

回答：

> Reddit 上真实发生了什么？

### 二、社区/领域真相

- `community_registry`
- `community_domain_membership`
- `community_governance_decision`
- `community_runtime_state`

回答：

> 这些内容属于哪些社区，这些社区属于哪些领域，现在该抓哪里？

### 三、语义真相

- `semantic_concepts`
- `semantic_terms`
- 统一的 `semantic_observation / semantic_label_run`

回答：

> 这些内容在业务语义上分别代表什么？

## 语义库应该服务哪三件事

### 1. 服务检索

让系统知道：

- 同义词
- 变体词
- 近义问题
- 该扩什么 query

### 2. 服务 readiness

让系统知道：

- 这个领域是不是已经有足够多的痛点语义
- 有没有解决方案语义
- 有没有可执行机会语义

也就是说，readiness 不该只看帖子数，还要看：

- 语义密度
- 语义覆盖
- 语义重复度

### 3. 服务报告

让系统知道：

- 哪些碎片其实在说同一个痛点
- 哪些方案在语义上是一类
- 哪些机会只是标题像机会，实际上没有语义支撑

## 后续怎么设计

### 保留

- `semantic_terms`
- `semantic_concepts`

作为语义知识 SSOT。

### 收口

把现在分散的：

- `post_semantic_labels`
- `post_llm_labels`
- `comment_llm_labels`
- `content_labels`
- `content_entities`

逐步统一进一套“语义观测账本”。

这套账本至少要能回答：

- 这条语义是谁打出来的
- 用的哪版规则/模型/prompt
- 置信度是多少
- 最后是否被采纳为正式分析信号

## 一句话结论

后续数据库重构不能只是：

> 把 community_pool 修好

而必须升级成：

> 内容库 + 社区库 + 语义库 三位一体

这样它才配得上我们这个产品的目标：

不是“抓到帖子”，而是“稳定产出有价值的 Reddit 洞察”。
