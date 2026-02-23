# Phase 180 - 爆帖速递词库首版（英文、每类30条）

日期：2026-01-28

## 本阶段目标
- 为“爆帖速递”小模块创建独立词库（英文、每类30条），避免与主系统 semantic_rules 混用。

## 执行内容
- 新增词库文件：`backend/config/boom_post_keywords.yaml`
  - 覆盖：rant_signals / opportunity_signals / discovery_signals / intent_label / pain_categories
  - 每个子类 30 条英文关键词/短语
- 文档对齐：`docs/Reddit爆帖速递_产品模块文档.md`
  - 明确词库来源为配置文件
  - 示例缩略为结构示例，实际以配置文件为准

## 验证情况
- 未运行测试（配置文件与文档调整）。

## 风险与备注
- 当前词库为 V0 基础版，后续需结合真实数据做增删调优。

