# Phase 556 - Mini Hotpost 记录页真历史与指定社区对齐

## 1. 发现了什么？
- 小程序 `history` 页还是纯 mock，用户看不到自己真实扫过的话题。
- 首页“指定社区”虽然已经透传后端，但后端首轮默认只收前 2 个社区，和前端“最多 5 个”口径不一致。
- 当前没有登录体系，直接做“本机真实分析记录”比新增后端历史接口更轻、更顺。

## 2. 是否需要修复？
- 需要。
- 这轮已完成：
  - `history` 页改成读本机真实分析记录
  - 指定社区改成“用户手动选几个，就按几个搜”

## 3. 精确修复方法
- 新增本机历史存储：
  - `hotpost-mini/hotpost-mini-app/src/services/hotpost-history.ts`
  - 负责保存最近 20 条分析记录，并保留一份轻量详情快照，方便之后从记录页重新打开
- `loading` 页在拿到终态后：
  - 同时写详情快照
  - 同时写历史记录
- `history` 页改成真实列表：
  - 读取本机历史
  - 展示真实关键词、模式、相对时间、信号数、主要社区
  - 当前只有 `trending` 详情页已接通，非 `trending` 记录点击会提示“还在联调”
- 后端 Hotpost 搜索工作流收口：
  - 如果用户手动指定社区，首轮和补证都按用户给的社区范围执行
  - 只有系统自己猜社区时，才继续走保守的 2 个社区限制

## 4. 验证
- 后端：
  - `pytest backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
  - `10 passed`
- 小程序：
  - `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - `Compiled successfully`

## 5. 这次执行的价值是什么？
- 记录页终于不再是样板图，而是用户这台设备上真实扫过的话题列表。
- 首页“指定社区”的承诺和实际执行口径对齐了：
  - 不填时，系统自己找相关社区
  - 手动填了几个，就按这几个社区优先搜
- 这为后面做 `rant / opportunity` 详情页接通提供了统一入口。
