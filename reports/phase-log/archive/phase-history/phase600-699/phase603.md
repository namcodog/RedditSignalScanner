# Phase 603 - Hotpost core contract 偏移审计与系统性补全方向

## 目标

- 停止继续按单题 patch 推进，重新审视 `hotpost = 稳固底座 + 三个强 skills` 是否真正落地。
- 验证用户提出的几个核心问题：
  - 底层算法不稳
  - core 规则不清
  - prompt 约束弱
  - `fast LLM` 没边界
- 输出后续必须重构的系统化方向，而不是再补某条 query。

## 关键结论

### 1. 现在的问题不是某条 query，而是 core contract 没立住

当前真实状态不是“稳固底座 + 三个强 skills”，更像：

- 一个共享外壳
- 三个 mode 分支
- 再加一条过于脆弱的上游 query 解析链

也就是说，模式分支已经存在，但底座还没真正变成稳定 contract。

### 2. `fast LLM` 当前确实越权

`rant` 主报告已经不是 `fast` 在写，真正写主判断的是 reasoning model。
但 `fast` 仍然直接决定：

- `search_query`
- `keywords`
- `subreddits`

这意味着它不是单纯翻译器，而是在事实上决定检索边界。

### 3. prompt 不是没约束，而是约束放错层了

当前 `prompt_rant.py` 主要约束的是：

- 报告输出怎么写

没有真正约束：

- query framing
- retrieval hypothesis
- ranking contract

所以不是“没 prompt”，而是“入口 contract 还不够强”。

### 4. planner / retrieval 仍然围绕 LLM 输出工作

`query_planner` 现在仍主要吃：

- `resolution.search_query`
- `resolution.keywords`
- `resolution.subreddits`

`retrieval_precision` 也主要围绕：

- 直接命中
- focus hits
- 社区质量
- forbidden context

来筛候选。
所以只要入口解析偏了，后面整条链都会偏。

### 5. 旧 complaint taxonomy 还没有完全退场

虽然 `rant` 最近已经有了新的商业阻力标签，但底层仍然存在两套分类脑子并存：

- 旧的通用 pain / complaint 分类
- 新的 rant friction 分类

这说明方向开始变对了，但 core 还没有完全统一。

## 后续必须先补的 3 层

### 1. Query Frame

先把用户问题压成稳定结构，而不是直接压成一条搜索词。
这层至少要回答：

- 这是什么问题家族
- 主商业阻力是什么
- 次商业阻力是什么
- 哪些检索假设该保留
- 哪些方向不能乱缩窄

### 2. Evidence Contract

检索和排序不再只围绕关键词命中，而是围绕：

- 哪类证据最能解释阻力
- 哪类帖子只是泛讨论
- 哪类帖子虽然热，但不值放首屏

### 3. Output Contract

推理模型只负责：

- 把已经站住的证据讲清楚

不再负责：

- 替入口错误擦屁股
- 用语言把弱证据包装得像判断

## 明确不再继续做的事

- 不再接受一题一修
- 不再继续把核心约束堆进 report prompt
- 不再让 `fast` 直接决定唯一检索面
- 不再把 mode-specific 修补误当成 core 修补

## 下一步

1. 先定义 `hotpost core contract`
2. 再定义三个 mode 的 skill contract
3. 然后才进代码重构：
   - `query_resolver`
   - `query_planner`
   - `retrieval_precision`
   - `report / projection`

## 结论

这次用户的判断基本成立：

- 不是某一个 query 没写对
- 是 core 约束没有立起来
- `fast` 在入口越权
- prompt 的约束放在了太后面

所以现在最该做的，不是继续补一条 query，而是把：

- 稳固底座
- 三个 mode skill

这件事真正重新落成代码结构。
