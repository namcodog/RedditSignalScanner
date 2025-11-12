# Implementation Plan: Legacy Quality Gap Remediation (Spec 013)

**Branch**: `013-legacy-quality-gap` | **Date**: 2025-11-12 | **Spec**: *(pending spec.md refresh – this plan captures the actionable backlog for Spec 013)*

## Summary

Spec 013 focuses on收尾目前遗留的三个“看得见的坑”——(1) 洞察卡片证据仍有占位内容、(2) 情感/中性统计不够真实、(3) 竞品分层数据来源单一。目标是在不破坏现有验收通过状态的前提下，把这些“兜底逻辑”升级成可验证的正式能力：真实 Reddit 证据链、可校验的情感分布、可配额/可扩展的竞品层级，并把新版门禁纳入 Spec010/Spec012。计划拆成四个阶段：研究与埋点、真实证据管线、情感&分层治理、全链路验收&回归。

## Technical Context

**Language/Version**: Python 3.11 (FastAPI + Celery)，TypeScript 5.x (Vite + React)
**Primary Dependencies**: FastAPI, SQLAlchemy, Redis, PostgreSQL, Celery worker, React 18
**Storage**: PostgreSQL (tasks/analysis/insights)，Redis (缓存 & 队列)，MinIO/S3 *(可选：用于归档证据)*
**Testing**: pytest、Playwright、Vitest、内容门禁脚本 (content/local/final acceptance)
**Target Platform**: Linux 服务 + 现代浏览器
**Performance Goals**: 端到端 ≤5min，Redis 命中率 ≥70%，证据采集+规范化单批 ≤60s
**Constraints**: 不能丢失现有验收能力；兜底逻辑需可观测 + 可回滚；LLM 增益保持可选
**Scale/Scope**: 200 社区池，日均 1.5k 帖子，需支撑 3-5 同时分析任务

## Constitution Check

| Gate | Status | 说明 |
|------|--------|------|
| 单一职责 | ✅ | 新增采集/规范化服务均以 service 模式注入，API 不暴露新端点 |
| 依赖倒置 | ✅ | 真实证据抽象成 `EvidenceSourceProvider`，可换抓取策略 |
| 复杂度控制 | ⚠️ | 情感/分层的回放作业增加批处理复杂度，需批量脚本+重试策略 |
| 质量门禁 | ⚠️ | Content acceptance 新增子项（真实证据/neutral coverage），需同步更新脚本 |
| 数据合规 | 🟡 | 真实证据引用 Reddit 链接需遵守 TOS，默认仅内部测试账号可见 |

## Project Structure

### Documentation
```
.specify/specs/013-legacy-quality-gap/
├── plan.md              # 本文档
├── spec.md              # (待补) 需求规格
├── research.md          # 真实证据抓取/匿名化调研
├── data-model.md        # 新增 evidence_source / sentiment_snapshot 表结构
├── quickstart.md        # 如何在本地启用真实证据模式
└── contracts/
    └── content-qa-checklist.md  # 更新后的验收门禁
```

### Source Code Touchpoints
```
backend/
├── app/services/evidence/
│   ├── reddit_client.py         # 新：真实证据抓取
│   ├── normalizer.py            # 新：文本规范化/去敏
│   └── provider.py              # 抽象层
├── app/services/analysis/
│   ├── sentiment.py             # 新：中性区间调优
│   └── competitor_layering.py   # 扩展：多源/统计聚合
├── app/services/report_service.py      # 接线 & 门禁
├── app/api/routes/insights.py          # 新增真实证据分页参数
├── app/models/
│   ├── evidence_source.py       # 新表
│   └── sentiment_snapshot.py    # 新表
├── scripts/
│   ├── backfill_real_evidence.py
│   └── sentiment_replay.py
└── tests/
    ├── unit/services/evidence/
    ├── integration/report/
    └── acceptance/content/
```

**Structure Decision**: 延续现有 backend/frontend 双体结构，仅在 backend 增加 `app/services/evidence` 与脚本目录，不拆新项目。

## Implementation Strategy

### Phase 0 – 研究 & 埋点 (1-2 天)
1. **抓取合规性**：确认 Reddit API/TOS（仅内部测试、速率限制、缓存写入）。
2. **数据埋点**：在现有 `analysis_pipeline` 写入原始帖子 ID/URL/社区/情感打分（存入 `analysis.sources.raw_posts`）。
3. **监控基线**：扩展 `reports/local-acceptance/content-acceptance-*.json`，记录 `neutral_pct`、`evidence_chain_real` 等指标，为后续对比做基线快照。

### Phase 1 – 真实证据管线 (3-4 天)
1. **EvidenceSourceProvider**：
   - 定义接口 (`fetch_posts(task_id, filters) -> List[Evidence]`)，默认实现调用 Reddit API + 备份 JSON。
   - 支持“只缓存、不对外展示”的安全模式。
2. **匿名化/规范化**：可选 LLM or 规则 pipeline，确保不泄露敏感字段；写入 `evidence_source.
normalized_excerpt`。
3. **报告注入**：`report_service` 优先使用真实证据，保留兜底逻辑；content-acceptance 统计真实证据比例。
4. **回填脚本**：`scripts/backfill_real_evidence.py TASK_ID=...`，可对历史任务补录证据。

### Phase 2 – 情感与中性区间修复 (2-3 天)
1. **Sentiment Snapshot 表**：记录每次分析的 `positive/neutral/negative` 计数，支持回放。
2. **算法调优**：
   - 基于关键词+上下文窗口判断“弱情绪”→ 中性。
   - 提供阈值配置 `sentiment_config.yml`，content-acceptance 校验 `neutral_pct ∈ [10,40]` 前先看 snapshot。
3. **测试**：pytest 单测 + 采样 20 份真实报告，确认中性占比不为 0。

### Phase 3 – 竞品分层治理 (3 天)
1. **多源数据**：支持从 `entity_dictionary/competitor_layers.yml` + `reports/metrics/*.csv` 汇总层级标签。
2. **自动补层**：若真实数据不足 2 层，使用统计结果自动生成“行业默认层”并标注来源。
3. **可配置门禁**：`scoring_rules.yaml` 新增 `min_competitor_layers` 与 `allow_fallback_layer`。
4. **前端展示**：在报告执行摘要/竞品块展示“真实 vs 兜底”标记。

### Phase 4 – 验收 & 文档 (2 天)
1. **更新 content/local/final acceptance**：
   - 记录真实证据覆盖率、neutral pct、中层补齐结果。
   - Archive 自动保存在 `reports/local-acceptance/archive/`（已完成）并新增 `spec013-verification.md`。
2. **回归测试**：
   - `make content-acceptance`, `make local-acceptance`, `make final-acceptance` 连续 2 次均需通过。
   - 补充 playwright 场景（洞察卡片显示真实链接、执行摘要展示 neutral 指标）。
3. **文档**：`spec013/quickstart.md` 说明如何开启/关闭真实证据模式；`contracts/content-qa-checklist.md` 更新门禁条目。

## Observability & QA Strategy
- **Logging**：新增 `EvidenceSourceProvider` 日志，含 Reddit API 状态、证据数量。
- **Metrics**：Prometheus counter `report_real_evidence_ratio`、`sentiment_neutral_pct`。
- **Playbook**：`scripts/run_spec013_smoke.sh` 自动串联抓取 → 分析 → content acceptance。
- **Backout**：配置 `REAL_EVIDENCE_ENABLED=0` 即可回退到占位逻辑；neutral/分层也有开关防止阻塞分析。

## Success Criteria
1. `content-acceptance` 中 `insight_cards_ok`、`competitor_layers_ok`、`neutral_range_ok` 全部为 true，score ≥ 90。
2. 每张洞察卡片平均真实证据 ≥2 条，且 95% 的链接可直接访问（自动探活）。
3. 中性占比在 80% 的任务中落在 [10%, 40%] 范围。
4. 新增指标/脚本完整记录在 `reports/local-acceptance/archive/`，可追溯。

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| 额外数据表 (evidence_source/sentiment_snapshot) | 需要历史回放与合规追踪 | 直接存在 JSON 中无法支持版本化/回放，多团队共享困难 |
| 多阶段批处理 | 需对历史任务回填情感/证据 | 在线实时改写风险大，批处理更安全且可暂停 |

---

**Next Steps**: 完成 `spec013/spec.md`（/speckit.specify）并为每个 Phase 衍生任务 `/speckit.tasks`，随后安排冲刺。EOF
