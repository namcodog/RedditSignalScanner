# Phase 67 - smart_shallow 评论回填策略

时间：2025-12-22

## 目标
- 把“Top + 最新 + 浅回复”的 smart_shallow 策略集成进评论回填执行链路

## 变更
- comments_parser 新增：smart_shallow 选取与限额缩放逻辑
- reddit_client 支持 mode=smart_shallow（双排序抓取 + 合并筛选）
- execute_plan 在 backfill_comments 下传 smart_config

## 验证
- pytest backend/tests/services/test_comments_parser_smart_shallow.py -v

## MCP 自检/验证
- Chrome DevTools MCP: 发现已有浏览器实例，未能接管（已记录）

## 风险/说明
- smart_shallow 通过 total_limit 自动缩放 top/new 数量，确保不超上限
- 默认 top/new/reply 比例为 30/20/1，可通过 plan.meta 覆盖
