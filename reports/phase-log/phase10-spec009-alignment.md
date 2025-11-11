# Phase10 — Spec 009 对齐与落地建议

日期: 2025-10-30

## 摘要
- 已阅读 `.specify/specs/009-通用主题分析能力升级蓝图.md:1` 并完成差异对齐。
- 009 侧重“主题无关的分析骨架”：数据基线（Top1000）、抓取策略外置化（crawler.yml）、冷热库回退、实体识别（词典→规则→相似度→可选 LLM 校对）、自然语言结构化输入文案、内容质量门禁扩展。
- 与现状：报告头部 `overview.total_communities/top_n/seed_source` 已接通（backend/app/services/report_service.py:591、backend/app/schemas/report_payload.py:49），抓取“空集回退”已实现（backend/app/tasks/crawler_task.py:130、321）。尚缺 Top1000 清单、crawler.yml 策略读取、实体榜单模块与门禁的 neutral 区间/实体覆盖/社区纯度断言。

## 已具备（与 009 对齐）
- 报告头部统计：`seed_source/top_n/total_communities` 已写入并经导出端点透出（backend/app/api/routes/reports.py:254）。
- 抓取空集回退：当 tier 过滤后为空，回退到全集抓取并记录告警（backend/app/tasks/crawler_task.py:130、321）。
- 内容质量门禁基础版：`backend/scripts/content_acceptance.py:1` 覆盖统计一致/行动项/证据密度/Top 社区/丰富度（尚未含 neutral 区间与实体覆盖）。

## 缺口清单（009 → 当前）
1) 数据基线与治理
   - 缺 `backend/data/top1000_subreddits.json`（可拓展至2000，含 name/tags/quality_score/default_weight/domain_label）。
   - Pool 合并加权策略需落地（top1000 > pool > discovery），目前只基于 DB Pool。

2) 抓取策略外置化
   - 缺 `backend/config/crawler.yml` 及读取逻辑（concurrency/timeout/ttl_hours/backoff/tier 策略/混合排序/limit/重试），现逻辑以常量为主。

3) 实体识别与“实体榜单”
   - 仅有 `backend/config/entity_dictionary.yaml`（单文件）；缺 `backend/config/entity_dictionary/<domain>.yml` 结构与多阶段识别/聚合/评分输出。
   - 报告缺少“实体榜单”区块与导出。

4) LLM 增益与审计
   - 未记录 `metadata.llm_used/model/rounds` 与严格 RAG 证据绑定的审计字段。

5) 自然语言结构化输入文案（前端）
   - 仅需新增占位与示例文案；不涉及组件改造。

6) 内容质量门禁扩展
   - 缺 neutral 合理区间（10–40%）断言；
   - 缺“实体覆盖度（按域最少 K 个）”与“社区纯度（Top 的域内相关性≥80%）”。

## 验收映射（009 DoD）
- DoD-1：Top1000 + pool 合并 → 需新增 JSON 和合并逻辑；现有 `make db-cache-stats`/`make db-crawl-metrics-latest` 已可用。
- DoD-2：crawler.yml 生效与空集回退 → 回退已具备；策略外置需补。
- DoD-3：实体榜单（证据≥2）→ 缺实现与导出。
- DoD-4：LLM 审计 → 缺。
- DoD-5：输入文案 + content-acceptance 扩展 → 文案未加，门禁需扩展。

## 四问（统一反馈）
1) 发现了什么问题/根因？
- 数据基线不稳（缺 Top1000 与权重），抓取策略内嵌常量，不利于治理与调参；实体识别链路未成型，导致“可解释性与可操作性”不足；门禁未覆盖 neutral 区间/实体覆盖/社区纯度，质量波动无法被 gate 住。

2) 是否已精确定位？
- 是。上述对应文件与缺失点已经定位（见“缺口清单/验收映射”与代码路径）。

3) 精确修复方法？
- 新增 `backend/data/top1000_subreddits.json` 与合并加权逻辑（top1000 > pool > discovery）；
- 新增 `backend/config/crawler.yml` 并由抓取器读取（并发/限速/混排/重试/回退）；
- 引入 `backend/config/entity_dictionary/<domain>.yml` 与实体识别/聚合/评分，新增“实体榜单”模块（报告与导出）；
- LLM 增益可开关，输出审计入 `metadata.llm_used/*`；
- 前端仅加“自然语言结构化输入”占位与提示；
- 扩展 `backend/scripts/content_acceptance.py` 增加 neutral 区间、实体覆盖、社区纯度断言。

4) 下一步做什么？（建议顺序 = 009 的 M1→M2→M3）
- M1（1周）：
  - 提交 `top1000_subreddits.json` 与 `crawler.yml` 骨架 + 读取；
  - 完整写入 `seed_source/total_communities/top_n`（已完成核实）；
  - content-acceptance 扩展 neutral 区间/社区纯度；
  - 前端加“结构化输入”提示文案。
- M2（1–2周）：
  - 实体识别管线与“实体榜单”模块 + 导出；
  - content-acceptance 增加实体覆盖断言。
- M3（1周）：
  - LLM 增益（可开关）+ 审计；
  - golden-set 回归集（≥2个领域）。

## 建议新增命令（Makefile）
- `make crawler-dryrun`（读取并打印 crawler.yml 生效策略，不执行抓取）。
- `make entities-dictionary-check`（校验词典规范与覆盖）。

---

结论：Spec 009 与现有方向一致，重点是把“可治理的策略与数据基线”落地，并把“内容质量门禁”升级为硬门槛。建议先执行 M1 子集，确保可调参与质量稳定，再推进实体与 LLM 增益。

