# Phase 74 - 清洗/去重默认优化

时间：2025-12-23

## 目标
- 点3：避免清洗/去重把信号密度打散

## 结论（简版）
- 评论回填默认开启（smart_shallow/limit=50/depth=2 保持原默认）
- 内容重复不再直接丢弃，改为“保留并打标”

## 变更点
- 默认开启评论回填：`backend/app/core/config.py`
- 新增去重模式开关（默认 tag）：`backend/app/core/config.py`
- 重复内容保留并打标：`backend/app/services/incremental_crawler.py`
- 示例环境变量补充：`backend/.env.example`

## 测试
- python -m pytest backend/tests/services/test_incremental_crawler_dedup.py backend/tests/config/test_default_flags.py

## 影响/注意
- 重复内容会入库，但会在 metadata 里标 `duplicate_of`/`is_duplicate`，统计仍计入 duplicates
- 评论回填默认开启，增加评论侧信号密度
