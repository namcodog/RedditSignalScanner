# Phase 201 - KAG Step3 规则打分链路补齐（comments）

## 执行范围
- backend 数据清洗/打分链路
- Makefile data-score 入口

## 核心改动
- 新增 comments 的 rulebook_v1 打分任务（score_new_comments_v1）
- data-score 入口同时跑 posts + comments 规则打分

## 影响文件
- backend/app/tasks/scoring_task.py
- Makefile

## 备注
- comments 规则打分为 LLM 打标的候选筛选提供底座
