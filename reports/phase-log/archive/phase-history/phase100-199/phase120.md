# Phase 120 - 旧口径/旧脚本归档清理（文档与脚本口径收口）

日期：2026-01-20

## 目标（说人话）
把旧版本SOP、历史说明、阶段性脚本从“主入口路径”里挪走，防止误读和口径混杂；保留追溯入口但不再作为现行标准。

## 已完成（归档清单）
### 1) 旧版 SOP 归档（docs/sop -> docs/archive/sop）
- 数据抓取系统SOP v1/v2/v3/v3.1
- 数据挖掘sop（无版本/ v3 / v4）
- SOP_Phase1/2/3（阶段性SOP）
- 数据库开发与使用规范-数据库sop（旧版）
- 2025-12-13-数据架构重构全记录（历史全记录）

### 2) 历史说明/方案归档（root -> docs/archive/reference）
- 有价值的信息11-26.md
- 分析引擎系统强化开发计划_v1.0.md
- 数据挖掘问题总结报告2025年11月29日.md
- 社区分级价值证明报告.md
- 次高价值社区_12个月数据抓取_执行指南.md
- 数据库优化执行指南.md

### 3) 旧脚本归档（scripts -> scripts/archive）
- day13/day14/day15 系列验收脚本
- phase4/6/7/8/9/10 阶段性修复脚本
- phase_c/phase_d 收尾脚本
- test_week2_acceptance.sh

### 4) 后端 legacy 脚本归档（backend/scripts -> backend/scripts/legacy）
- init_community_pool_82.py（旧的97社区CSV回填脚本）
- crawl_incremental_legacy.py
- crawl_comprehensive_legacy.py
- day14_diagnose.sh

## 结构性补充
- 新增 `scripts/archive/README.md` 说明归档脚本用途
- 更新 `backend/scripts/LEGACY.md`，补齐新增 legacy 清单
- 更新 `docs/archive/README.md`，登记新归档目录与文件

## 口径保留
- `scripts/phase106_rehearsal_matrix.py` 与样例文件仍保留在现役路径（PRD/演练矩阵引用中）

## 影响范围
- 仅移动/归档历史文档与脚本；未改动业务代码与数据库

## 待确认/可继续清理
- 是否继续归档“未被 Makefile/文档引用”的脚本（数量较多，需确认范围）
