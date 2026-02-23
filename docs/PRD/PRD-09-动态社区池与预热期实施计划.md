# PRD-09: 动态社区池与预热期实施计划（后端现状对齐版）

## 1. 概述

系统已实现“社区池 → 发现 → 验毒 → 评估 → 入池”的闭环，所有记录以数据库为准，Admin/前端已同步对应入口。  
抓取执行口径与落表细节以 `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md` 为准。

## 2. 核心数据结构（已落地）

### 2.1 community_pool（主池）
- 关键字段：`tier`, `priority`, `health_status`, `is_blacklisted`, `downrank_factor`, `semantic_quality_score`
- 说明：分析引擎与爬虫均以此为主入口。

### 2.2 discovered_communities（候选池）
- 状态：`pending → approved → rejected/blacklisted`
- 记录字段：`discovered_from_keywords`, `metrics`, `tags`, `rejection_count`, `cooldown_until`

### 2.3 evidence_posts（证据帖审计）
- 由 probe 产出，作为发现证据资产。

### 2.4 tier_suggestions（调级建议）
- 每日生成建议，记录理由/置信度，供运营审核或自动应用。
- 可选：生成 DecisionUnit（ops 信号），用于平台级反馈闭环。

---

## 3. 发现与评估流程（已落地）

### 3.1 发现入口
- 来源：`semantic_rules` 里的 pain 关键词
- 任务：`tasks.discovery.discover_new_communities_weekly`
- 开关：`CRON_DISCOVERY_ENABLED=1`

### 3.2 验毒回填（candidate vetting）
- 开关：`DISCOVERY_CANDIDATE_VETTING_ENABLED=1`
- 默认窗口：30 天 / 7 天切片 / 总预算 300 帖
- 目的：先补样本，再评估，避免误判

### 3.3 评估与入池
- 任务：`tasks.discovery.run_community_evaluation`
- 评估器：`CommunityEvaluator(sample_size=50)`
- 结果：approved 写入 `community_pool`，rejected/blacklisted 进入冷却

### 3.4 自动回填
- `DISCOVERY_AUTO_BACKFILL_ENABLED=1` 时，对 approved 社区触发 30 天回填

---

## 4. 探针补充（已落地）

### 4.1 probe_search / probe_hot
- 输出：`evidence_posts` + `discovered_communities`
- 只负责“发现”，不直接入池

### 4.2 自动触发评估（可选）
- `PROBE_AUTO_EVALUATE_ENABLED=1` 时，可在 probe 完成后触发评估

---

## 5. 预热期与监控（已落地）
- `monitor_warmup_metrics`：监控缓存与社区池健康
- `monitor_cache_health` / `monitor_crawler_health`：监控抓取稳定性

---

## 6. Admin/前端说明
- Admin 操作界面已对齐（见 `PRD-07`），Excel 导入见 `PRD-10`。

---

**文档状态**：已按本地实现对齐（backend）。
