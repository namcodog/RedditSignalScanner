# Phase 10 — Spec 010 缺口补齐（门禁 + 机会量化参数化 + 诊断脚本）

日期：$DATE

## 1）发现了什么问题/根因？
- 门禁缺失 Spec010 的三条硬约束：pain_clusters ≥ 2、competitor_layers ≥ 2、opportunities[*].potential_users_est > 0。
- 机会量化采用启发式常数，未参数化，难以调参与复现；且仅输出字符串，不利于门禁断言。
- 缺少 clusters-smoke / competitors-smoke 诊断命令与 Make 目标。

## 2）是否已精确定位？
- content_acceptance.py 仅做统计一致性、证据密度、Top 社区、洞察丰富度等检查，未覆盖三条硬门禁。
- signal_extraction.py 在行 605 附近以固定系数计算 potential_users。
- analysis_engine.py 仅下发了字符串 potential_users，未同时输出数值字段。

## 3）精确修复方法（已实现）
- 门禁补齐（Spec010）：
  - backend/scripts/content_acceptance.py 增加 clusters_ok / competitor_layers_ok / opportunity_users_ok，并纳入 passed 计算。
- 机会量化参数化：
  - backend/config/scoring_rules.yaml 新增 opportunity_estimator 参数块（base/freq_weight/avg_score_weight/keyword_weight/theme_relevance/intent_factor/participation_rate）。
  - backend/app/services/analysis/scoring_rules.py 新增 OpportunityEstimatorConfig 并由 Loader 解析；保持向后兼容。
  - backend/app/services/analysis/signal_extraction.py 改为读取上面的参数，并使用 multiplier（主题相关性 + 意愿强度）调整；保证最小/最大边界。
  - backend/app/services/analysis_engine.py 在机会项中附带 potential_users_est 数值，同时保留原字符串字段。
  - backend/app/schemas/analysis.py 为 OpportunitySignal 增加可选的 potential_users_est: int 字段（兼容旧数据）。
- 诊断脚本与 Make 目标：
  - 新增 backend/scripts/cluster_smoke.py 与 competitor_smoke.py：读取任务并输出 clusters / competitor_layers_summary JSON。
  - Makefile 增加 clusters-smoke / competitors-smoke 目标，输出落盘到 backend/reports/local-acceptance/。

## LLM 接入（新增）

- OpenAI 客户端接通（模块化）：
  - 客户端：backend/app/services/llm/clients/openai_client.py（读取 OPENAI_API_KEY / LLM_MODEL_NAME）
  - Summarizer（要点句）：优先 OpenAI，失败回退本地提取式（LocalExtractiveSummarizer）
  - Normalizer（基础本地）：LocalDeterministicNormalizer（为后续 OpenAI Normalizer 预留位）
  - 标题/Slogan：TitleSloganGenerator（OpenAI，失败回退跳过，不阻断）
  - 集成：ReportService 在组装 action_items 时生成要点句与标题/Slogan；metadata 写入 llm_used/model
  - 门禁：content_acceptance 增加 llm_coverage（≥0.6 必须）

## 机会人数校准（新增）

- 在 ReportService 汇总阶段加入“社群规模乘子”（scale_weight 参数化），对 potential_users_est 做二次校准并同步字符串展示。


## 4）下一步做什么？
- 回收现有样本任务，运行 clusters-smoke 与 competitors-smoke，确认典型任务的门禁覆盖达标。
- 视需要在 opportunity_report 中优先使用 potential_users_est 计算 product_fit（当前保持兼容逻辑）。
- 与前端对齐：若前端需要展示数值估计，则按字段名 potential_users_est 读取。

## 5）这次修复的效果是什么？达到了什么结果？
- content_acceptance 增加三条硬门禁后，报告“样本级可用”可被自动化严格卡住，减少人工验收负担。
- 机会量化参数化，后续可在 YAML 中快速调参并复现，且提供稳定的数值断言位 potential_users_est。
- 诊断脚本补齐，降低排障与人工验证的成本；Make 目标一键落盘，便于归档与比对。

## 变更清单
- tests: backend/tests/scripts/test_content_acceptance_spec010.py
- scripts: backend/scripts/content_acceptance.py（新增断言）
- config: backend/config/scoring_rules.yaml（新增 opportunity_estimator）
- core: backend/app/services/analysis/scoring_rules.py（Loader 扩展）
- core: backend/app/services/analysis/signal_extraction.py（参数化估计）
- core: backend/app/services/analysis_engine.py（opportunities 输出 potential_users_est）
- schema: backend/app/schemas/analysis.py（机会数值位）
- tools: backend/scripts/cluster_smoke.py、backend/scripts/competitor_smoke.py
- Make: 新增 clusters-smoke、competitors-smoke 目标；help 菜单增加指引

---

## 结构优化记录（2025-11-03）

1）**发现了什么问题/根因？**
- README 与文档阅读指南指向的 `2025-10-10-*` 文档仍假设文件在仓库根目录，导致新人照做会报 "No such file"。
- 根目录堆积 GitHub 提交流程、蓝图、报告样本、MCP 指南、测试报告等历史文件，没有分类也没有版本标签，难以判断最新基线。
- `reports/` 中缺少统一的测试进度目录，4 份测试报告散落在根目录，CI 无法自动引用。
- `backend/backend/` 遗留一份旧的配置/数据副本，`entity_stopwords.yaml` 仅存在于该目录，脚本默认路径 `backend/config/*` 会读不到；同时 pip 安装日志 `backend/=1.1.0` / `=7.7.0` 误导为包目录。

2）**是否已精确定位？**
- 通过 `rg "backend/backend"` 确认没有代码引用旧路径，可以安全迁移。
- `backend/scripts/import_entities_from_csv.py` 默认写入 `backend/config/entity_stopwords.yaml`，因此直接缺文件就是根因。
- README 中的所有 `./2025-10-10-*` 链接均集中在文档导航与 Onboarding 两段，可一次性修复。

3）**精确修复方法？**
    - 新建 `docs/planning/`、`docs/reference/`、`docs/tools/mcp/`、`reports/test-progress/`，将对应蓝图/案例/工具/测试文档迁入并在 README + 文档阅读指南中新增分区导航。
    - 更新 README 中所有文档链接、命令示例路径；补充新的文档分组介绍 + MCP/测试档案引用。
    - 迁移 `词义库思路` 引用、`TEST_*` 报告之间的互链，使路径跟随新目录。
    - 将 `backend/backend/config` 中唯一仍需保留的 `entity_stopwords.yaml` 移到主配置目录，其余历史文件落盘到 `backend/config/entity_dictionary/legacy`、`backend/config/semantic_sets/versions/crossborder_v0.yml`、`backend/config/legacy/scoring_rules_v0.yaml`；旧数据与审核记录移动到 `backend/data/archive/` 与 `backend/reports/local-acceptance/archive/`，然后删除 `backend/backend/` 与 pip 日志文件。
    - 根目录脚本/诊断工具统一迁入 `scripts/`，VSCode 配置收拢到 `config/vscode/`，Redis dump/社区 Excel 则落在 `data/redis/`、`data/community/` 并在 Makefile、脚本、文档中更新引用路径。

4）**下一步做什么？**
- 后续若新增蓝图/方案，请直接放入 `docs/planning/` 并在 README 的分区内登记条目。
- 运行 `make test-backend` 前，如需更新 stopwords/dictionary，可统一从 `backend/config/` 读取，避免重新生成到 legacy 目录。
- 待下一轮测试前，将 `reports/test-progress` 作为固定产出目录纳入 CI 附件。

5）**这次修复的效果/结果？**
    - 文档链接全部指向实际存在的 `docs/` 路径，README 的导航一次到位，新人不再需要猜测位置。
    - 规划/参考/MCP/测试文档各有独立目录，查找时可按类型过滤；测试报告集中在 `reports/test-progress`，便于持续追踪通过率。
    - `backend/config/entity_stopwords.yaml` 回到主配置目录，相关脚本开箱即用；`backend/backend` 与 pip 日志被清理，避免双份配置或误导导入路径。
    - 根目录回归“只放核心文件”，常用脚本与数据都按 `scripts/`、`data/**` 归档，相关 Makefile/Spec/日志引用同步修复，可直接运行 `make week2-acceptance` / `make final-acceptance` / Excel 导入等流程。

## Spec012 实机验证记录（2025-11-12）

1）**执行内容**
- `make dev-golden-path` 启动 Redis/Celery/后端/前端，并用 `make semantic-build-L1`、`make semantic-metrics`、`make semantic-acceptance`、`make seed-json-from-excel FILE=data/community/社区筛选.xlsx`、`make seed-import-json`、`bash scripts/day13_quick_check.sh` 搭建基线。
- `make crawl-crossborder LIMIT=5` 实际抓取跨境社区（首轮耗时较长，二次执行得到 `status: completed` 汇总），随后 `make content-acceptance` 通过。
- Spec012 所需三套验收命令：`make local-acceptance`、`make week2-acceptance`、`make final-acceptance`，运行时统一通过 `NO_PROXY=localhost,127.0.0.1,::1` 关闭系统代理（否则 httpx 会走代理直接报 "Server disconnected"）。

2）**问题定位（历史）**
- **本地验收失败**：`reports/local-acceptance/local-acceptance-20251112-050242.md:5-33` 中 `fetch-report`/`download-report` 500，根因是 `insights.pain_clusters[1].negative_mean=-1.1` 违反 schema，且洞察证据/质量看板数据缺失。
- **Week2 验收**：脚本路径修复后已 PASS（Precision@50=0.64，行动位满足规范）。
- **最终验收失败**：PDF 导出依赖 WeasyPrint，缺包时降级为 JSON，被验收判定失败；质量看板读不到 CSV。

3）**结果复核（2025-11-12 13:40 UTC）**
- `reports/local-acceptance/local-acceptance-20251112-053958.md` ✅ 全 12 步通过。
- `make week2-acceptance` ✅ （最新任务 `32353728-b3ed-4a56-b0cb-beeaa53c0082`）。
- `make final-acceptance` ✅ （任务 `71f49094-6bf3-4ef0-90f2-02dd969157e5` 等多次），PDF 成功导出且 content-acceptance 紧随其后保持通过。

4）**下一步建议**
- 先修复分析结果的 JSON 结构（热修 `report_service`，确保 `negative_mean` 被 clamp 至 [-1,1]），再重跑 `make local-acceptance`、`make final-acceptance`，同时排查洞察证据和质量看板的种子数据是否缺失。
- 把 `NO_PROXY=localhost,127.0.0.1,::1` 写入开发/验收文档，或在脚本里显式 `trust_env=False`，避免下次又被系统代理截断本地请求。
