# Phase 614 - Hotpost 小程序架构复评与快速上线方案

## 时间
- 2026-03-30

## 目标
- 重新审视 `hotpost` 整体架构是否还符合“小程序快速上线”的目标
- 明确：
  - 哪些设计合理
  - 哪些是被 `rant` 架构持续带偏后的复杂度
  - 最短上线版应该如何收边界

## 发现了什么？

### 1. 方向本身没有错
- `共享底座 + 三个强模式（trending / rant / opportunity）` 这个方向是对的。
- 统一入口、统一缓存、统一结果外壳，也都是对的。

### 2. 现在真正的问题不是“没架构”，而是“架构边界被拖重了”
- 原始产品文档给 `hotpost` 的定位很清楚：
  - 轻量检索入口
  - 报告阅读器
  - 独立小程序
- 但当前真实实现已经变成一条很长的流水线：
  - `query_resolver`
  - `problem_frame`
  - `query_planner`
  - `evidence_collection`
  - `remediation`
  - `report_workflow`
  - `response_bundle`
  - `quality_contract`
  - `mode_contract`
  - `preview_projection`

### 3. 被带偏的主要不是全系统，而是 `rant`
- 从 `phase560 / phase565 / phase613` 可以看到：
  - `rant` 已经从一个模式，逐渐被推进成一套 family/stage 问题引擎
  - 复杂度持续前移到：
    - query family
    - retrieval hypotheses
    - stage hypotheses
    - reasoning trigger
    - remediation rounds
- 这条线对算法研究有价值，但对“小程序快速上线”不友好。

### 4. 小程序真正需要的东西其实很轻
- 小程序端实际只依赖：
  - `POST /api/v1/hotpost/search`
  - `GET /api/v1/hotpost/result/:query_id`
  - 本地 `history/detail snapshot`
- 它真正需要的是：
  - 搜索稳定
  - 结果稳定
  - 页面结构直接可读
- 它不需要把算法内部状态一路暴露到产品层。

### 5. 反而有个好消息
- 当前 `hotpost` 结果持久化主要还是 Redis 缓存。
- 没有深度绑进主链完整分析闭环。
- 说明它现在还有机会快速收成一个更独立、更轻的产品面。

## 是否需要修复？
- 需要。
- 但不是“大重构推翻重来”。
- 正确做法是：
  - 收边界
  - 冻结实验层
  - 把 `hotpost` 拉回“轻产品”而不是“研究引擎”

## 精确修复方法

### 一、重新定义 Hotpost V1 的结构
- `hotpost` V1 只保留 5 层：
  1. API facade
  2. shared core
  3. three mode skills
  4. direct UI contract
  5. cache/history

### 二、哪些保留
- 保留：
  - `/search` + `/result`
  - Redis 结果缓存
  - 小程序本地 history/detail snapshot
  - 三模式统一入口
  - mode contract 这种模式边界层

### 三、哪些降级到实验层
- 暂时不要继续让这些内容污染 V1 主链：
  - `rant` family/stage hypothesis 持续前移
  - 自动补证回合
  - 重模型二次重跑默认开启
  - 过重 debug contract
  - 前端再做一层代表帖子/迁移摘要/解释投影

### 四、后端结果要直接对齐小程序页面
- 当前小程序端还在自己推导：
  - representative posts
  - migration summary
  - followup queries
  - 某些解释文案
- V1 更合理的做法是：
  - 后端直接返回页面 section 数据
  - 前端只做展示，不再做“半分析”

### 五、和主链路的关系
- `hotpost` 不应和当前主链路混成一体。
- 正确关系是：
  - 借基础设施
  - 不绑业务链
- 可以借的：
  - Reddit client
  - 限流策略
  - 通用词库
  - 社区发现经验
  - 证据数据结构
- 不该共享的：
  - 主链复杂分析目标
  - 主链结果口径
  - 为主链服务的过重流程

## 下一步系统性计划

1. 先定义一版 `hotpost` 小程序专用 response contract
   - 直接按页面 section 返回
2. 再把前端当前的二次推导尽量收回后端
3. 把 `rant` 近几轮实验逻辑标成实验层或 feature flag
4. 用三条真实 query 做 V1 验收：
   - `trending`
   - `rant`
   - `opportunity`
5. 验收标准从“算法多聪明”改成：
   - 能不能稳定出结果
   - 用户能不能一眼看懂
   - 小程序能不能快速上线

## 这次执行的价值是什么？
- 这次复评把问题从“某个 rant 还不够准”拉回成了“这个产品到底该长什么样”。
- 最大价值不是再修一条 query，而是把：
  - `hotpost` 应该服务于产品
  - 不是产品服务于 `rant` 实验
 这个边界重新立住。
