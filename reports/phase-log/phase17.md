# Phase 17 - 后端全链路“体检式”梳理（抓取→清洗→入库→语义→分析→报告→监控）

日期：2025-12-16

## 一句话结论

当前后端已经跑通“社区池→增量抓取→冷热双存→评论/语义→分析→报告/导出→监控”的闭环，但要做到“稳、不翻车、可追溯、可复现”，还需要把 **数据血缘**、**配置校验**、**质量门禁与告警的闭环** 三件套补齐。

## 本次检索证据（以代码为准）

### 入口与任务编排

- API 入口：`backend/app/main.py:create_application`
- v1 路由聚合：`backend/app/api/v1/api.py:api_router`
- 分析任务创建与调度：`backend/app/api/v1/endpoints/analyze.py:create_analysis_task`、`_schedule_analysis`
- Celery 配置/队列/beat：`backend/app/core/celery_app.py:_build_conf`、`beat_schedule`
- 分析任务执行链：`backend/app/tasks/analysis_task.py:run_analysis_task`、`execute_analysis_pipeline`
- 抓取任务执行链：`backend/app/tasks/crawler_task.py`、`backend/app/services/incremental_crawler.py:IncrementalCrawler`

### 多路由/重复实现（瘦身前必须先核对的“旧路”证据）

- `/api` 下同时挂载 v1 与 legacy：`backend/app/main.py:create_application`（`app.include_router(v1_api_router, prefix="/api")` + `legacy_router = APIRouter(prefix="/api")`）
- “v1 目录 ≠ /v1 门牌”：`backend/app/api/v1/api.py:api_router` 当前未加 `/v1` 前缀；但 `backend/app/main.py:create_application` 的兼容提示写着 “use /api/v1/...”
- 两套 Reddit client 并存：`backend/app/clients/reddit_client.py` 与 `backend/app/services/reddit_client.py`（当前多处任务引用 `app.services.reddit_client:RedditAPIClient`）

### 数据模型与可追溯关键表

- 任务与状态：`backend/app/models/task.py:Task`
- 分析与报告：`backend/app/models/analysis.py:Analysis`、`backend/app/models/report.py:Report`
- 冷热存储：`backend/app/models/posts_storage.py:PostRaw/PostHot`
- 评论与语义：`backend/app/models/comment.py:Comment/ContentLabel/ContentEntity`、`backend/app/models/post_semantic_label.py:PostSemanticLabel`
- 社区池与发现池：`backend/app/models/community_pool.py:CommunityPool`、`backend/app/models/discovered_community.py:DiscoveredCommunity`
- 缓存/水位线：`backend/app/models/community_cache.py:CommunityCache`

### 质量门禁与监控

- 样本门禁：`backend/app/services/analysis/sample_guard.py:check_sample_size`
- FactsV2 质量门禁：`backend/app/services/facts_v2/quality.py:quality_check_facts_v2`
- 运行监控任务：`backend/app/tasks/monitoring_task.py`

## 端到端链路（文字箭头图）

社区池(community_pool/discovered_communities)
→ 调度(celery beat + tier 配置 crawler.yml)
→ 增量抓取(限流/重试/水位线)
→ 冷热双存(posts_raw/posts_hot) + 评论(comments)
→ 语义打标(content_labels/content_entities/post_semantic_labels)
→ 分析引擎(run_analysis)
→ 结果入库(analyses/reports/insight_cards/evidences)
→ 对外接口(REST 报告/导出 + SSE 状态)
→ 监控(监控任务 + 指标落库/Redis 看板)

## 发现的问题/缺口（按“容易翻车点”排序）

1) Serena MCP 工具此前固定绑定到另一个仓库（`/Users/hujia/Desktop/最小化Navigator`），会导致本仓库用 Serena 检索“仓库外路径”报错；现已改配置指向 `RedditSignalScanner`（见文末补充），待重启 Codex 生效后即可恢复“先证据后结论”的标准流程。

2) 数据血缘还不够“硬”：虽然 `Analysis.sources`/`InsightCard+Evidence` 能给出一定证据，但缺少统一、稳定、结构化的 “本次任务用到哪些 post_id/comment_id、样本范围、去重率、缺口是多少” 的落库记录，导致回放/审计/复现不够一键。

3) 配置治理分散：ENV + YAML 同时存在（如 `backend/app/core/config.py` + `backend/app/services/crawler_config.py`），但启动时缺少统一的“配置校验/版本标记/变更审计”入口，容易出现“线上跑的配置和你以为的不一样”。

4) 质量门禁与告警闭环还可更紧：门禁逻辑存在（sample_guard、facts_v2 quality），但与 Task 的 failure_category、告警、以及报告层“缺口说明”还没形成强耦合闭环（失败能否明确告诉你是哪一段漏、漏了多少）。

5) “黄金路”门牌还没钉死：v1 代码在 `api/v1` 目录，但真实对外路径是 `/api/...`，同时 legacy 也挂在 `/api` 下（见上面证据）；这会让前端/调用方容易踩坑，也会让后端修 bug 时“不确定该改哪条路”。

6) 旧代码未统一归档：目前已看到重复实现（两套 reddit_client、两套路由聚合），但还没通过引用关系把“在用/不用”的边界画死；不先画边界就删，风险极高。

## 下一步建议（两档）

### 保守修补（先把系统变“可控”）

- 补血缘：落库一个 `pipeline_run`/`facts_snapshot` 级别记录（最少：社区列表、posts/comments 计数、去重率、样本短缺、门禁结果、配置版本哈希）。
- 补配置校验：启动时校验 crawler.yml/lexicon.yml/DB/Redis/Reddit 凭证，失败直接阻断或降级，并写告警。
- 打通门禁→失败归因→报告缺口说明：让“不足样本/话题不匹配/范围不一致”等门禁 flag 直接体现在 Task 状态与报告 metadata。
- 先钉死黄金门牌：短期先承诺 `/api` 为对外黄金路径（只做稳定与兼容），同时评估是否把同一套 v1 router 再挂一份到 `/api/v1` 作为“新门牌”（给迁移窗口，但不立刻强切）。

### 结构升级（把“可回放”做到极致）

- 引入“事实包 FactsPackage + 步骤运行 StepRun”两张核心表：分析只读事实包，报告只引用事实包；任何结论都可追溯到证据 id 列表。

## 验收方式（可量化）

- 任一 task_id 能一键查到：抓取社区数、posts_raw/posts_hot/comments 数、去重率、缓存命中率、门禁结果、证据引用列表。
- 同一输入 + 同一配置版本：重复运行报告关键字段一致（或差异在可解释范围内）。
- 失败时能明确归因：限流/数据不足/存储/语义/分析哪段出问题，且能量化“漏了多少”。

## 本次未做的事（刻意不越界）

- 未修改业务逻辑与数据库结构；本文件仅记录“现状证据 + 缺口 + 后续改造方向”。

## 重启 Codex 后 10 分钟续航清单（保证“先证据后结论”恢复）

1) 验证 Serena 已指向本仓库：用 Serena `list_dir` 看仓库根目录能正常列出（不再报“仓库外路径”）。
2) 用 Serena 抽查关键入口：`backend/app/main.py:create_application`、`backend/app/api/v1/endpoints/analyze.py:create_analysis_task` 能正常 `find_symbol`。
3) 画清“在用/不用”的边界（为后续归档做证据）：对 `backend/app/services/reddit_client.py:RedditAPIClient` 做 `find_referencing_symbols`，确认真实引用点；同时检查 `backend/app/clients/reddit_client.py` 是否完全无人引用。
4) 把验证结果补到下一期日志（建议 `reports/phase-log/phase18.md`）：明确“黄金路”的入口/路由/任务名/关键模块清单。

## 补充：Serena MCP 指向修复（根治“指错仓库”）

### 发现的问题/根因

- Codex 使用的全局 MCP 配置里，Serena 被固定写死为 `--project /Users/hujia/Desktop/最小化Navigator`，导致在 RedditSignalScanner 仓库里调用 Serena 工具会出现 “relative_path 指向仓库外” 的错误。

### 已做的修复

- 更新 Codex MCP 配置，将 Serena 的 `--project` 改为本仓库路径：
  - `/Users/hujia/.codex/config.toml`（`[mcp_servers.serena] args`）
- 修正本仓库 Serena 工程配置，避免语言服务器选错（后端为主）：
  - `.serena/project.yml`（`language: python`）

### 验证方式

- 检查配置文件中不再出现 `最小化Navigator`，且 `--project` 为 `RedditSignalScanner`。
- 重启 Codex CLI 后，调用 Serena 工具 `list_dir`/`find_symbol` 应能在本仓库根目录下正常工作（不会再报“仓库外路径”）。
