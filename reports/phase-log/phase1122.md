# Phase 1122 - Brand Intelligence R15.0 Dry-run

## 这轮达到的目的

- 建好主系统品牌收录的第一个后端底座：从已发布 Hotpost 卡里抽取语义库已知品牌，并生成 dry-run 报告。

## 当前状态变化

- 新增 `brand_intelligence` 只读服务和 CLI：默认只读 `load_published_cards()`，不写 DB、不改小程序、不改发布链。
- 产物为 `reports/brand-intelligence/brand-digest-2026-05-12.md/json`：扫描 `847` 张已发布卡，识别 `3` 个已知品牌、`94` 条证据，`db_writes=false`。

## 还没完成什么

- 现在只识别语义库已知品牌；还没有做新品牌发现、人工审核状态、Dev DB `brand_registry / brand_mentions` 写入。

## 下一步做什么

- 进入 R15.1：补候选 / verified / rejected 质量合同和噪音审计；通过后再做 R15.2 Dev DB 注册表。
