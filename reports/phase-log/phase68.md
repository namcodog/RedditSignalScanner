# Phase 68 - 评论回填 smart_shallow 默认与护栏

时间：2025-12-22

## 目标
- 将“聪明地浅”设为评论回填全局默认
- 加入三条硬护栏（不足全量、去重补齐、爆帖加料）

## 变更
- comments_parser: 支持 reply_top_limit + 补齐逻辑 + 自适应缩放
- reddit_client: smart_shallow 双排序抓取，按总量与护栏做选择
- execute_plan: backfill_comments 默认 smart_shallow + 爆帖自动加料
- comments_task: 默认 mode=smart_shallow，内置默认 smart_* 配置

## 验证
- pytest backend/tests/services/test_comments_parser_smart_shallow.py backend/tests/services/test_backfill_comments_executor.py -v

## 说明
- 爆帖规则：num_comments>=300 或 score>=500 → 目标150、depth>=3
- 不足/去重补齐：优先用顶层最新评论补齐
