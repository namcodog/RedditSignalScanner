# Phase 139 - 旧文档与 legacy 脚本归档 + 记忆口径更新

日期：2026-01-21

## 目标
清理旧口径干扰：更新记忆口径、归档旧文档、归档 legacy 脚本。

## 执行内容
1) 更新记忆文件
- memory: workflow_actual 已替换为当前系统口径（SSOT + 简版主链路）。

2) 旧文档归档（统一 DEPRECATED 头）
- 从 docs 根目录移动到 docs/archive：
  - 2025-11-主业务线说明书.md
  - API-QUICK-REFERENCE.md
  - DATABASE_CONFIGURATION.md
  - MAKEFILE_GUIDE.md
  - MCP-SETUP-GUIDE.md
  - PR-WORKFLOW-CHEATSHEET.md
  - SQLALCHEMY_POOL_CONFIG.md
  - annotation-guide.md
  - dev_spec_ingest_jsonl.md
  - domain-goals.md
  - mcp_configuration_guide.md
  - scoring_protocol_v1.md
  - 分析算法设计详解.md
  - 测试账号.md
  - 语义库资产化执行方案.md
- docs/archive/README.md 已补充归档列表。

3) legacy 脚本归档
- backend/scripts/legacy -> docs/archive/root/scripts/legacy
- 新增清单：docs/archive/legacy-scripts-inventory.md
- backend/scripts/LEGACY.md 已更新归档路径说明。

## 影响与说明
- 仅文档与脚本归档，不影响运行链路。
- 归档文档不再作为当前口径，按 docs/2025-10-10-文档阅读指南.md 为准。

## 验证
- `rg -n "backend/scripts/legacy|scripts/legacy" docs backend README.md` 仅剩 archive 记录。

## 下一步
- 若有归档文档仍需作为现行口径，请显式加入 docs/2025-10-10-文档阅读指南.md。
