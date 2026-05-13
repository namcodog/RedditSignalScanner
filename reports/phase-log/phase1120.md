# Phase 1120 - Hotpost 探索回流编排入口落地

## 这轮达到的目的
- 已把探索社区从“手动记得跑”收成固定入口：pre 跑小配额 probe，post 跑社区审计和 R11.5 dry-run。

## 当前状态变化
- 新增 `run_community_exploration_loop.py`、编排服务、Makefile pre/post 入口和单元测试；SOP 已改成固定顺序。

## 还没完成什么
- pre 阶段未做 live probe smoke，避免本轮验证触发真实 Reddit 采集；后续日常运营时按当天方向执行。

## 下一步做什么
- 下一次出卡前用 `make hotpost-community-exploration-pre PROBE_ARGS='--probe scope:n:方向'`，发布后固定跑 `make hotpost-community-exploration-post`。
