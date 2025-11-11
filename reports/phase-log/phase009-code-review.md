# Phase 009 · 代码审查与差距清单（Spec 009 对齐）

更新时间: 2025-11-11

## 摘要
- 本次聚焦 Spec 009「通用主题分析能力升级蓝图」的落地对齐度审查，覆盖后端抓取/冷热分层、治理与配置、实体识别与语义集成、报告产出与门禁、前端输入引导与样例，以及 Make 命令入口完整性。
- 发现多数核心骨架已具备：社区池与合并策略、增量水位线、冷热双写（DB+Redis）、Tier 调度与 crawler.yml、实体词典与语义集工具链、报告 overview 字段与内容门禁等。
- 关键差距集中在抓取回退策略自动化、跨境基线数据质量与版本标注、前端样例的跨境化、以及 Make 命令与文档一致性。

## 统一反馈四问（实际为五点）

1) 发现了什么问题/根因？
- 抓取回退策略（空集 → 放宽/回退“不过滤全集”）配置已存在但未在运行流程生效：
  - 配置位置: backend/config/crawler.yml:29-48（fallback_thresholds 与各 tier fallback）。
  - 运行路径实际未应用：增量抓取与旧版抓取均未根据空集/失败计数自动调整 time_filter/sort（见 backend/app/services/incremental_crawler.py 与 backend/app/tasks/crawler_task.py）。
- 跨境 Top-1000 基线文件存在但内容偏通用，未体现“跨境优先”数据治理约束：backend/data/top1000_subreddits.json 包含 r/funny 等泛社区。
- 报告头部缺少“跨境主题/词库版本号”标注：目前仅有 analysis_version（见 backend/app/services/report_service.py:980-1019 生成的 ReportMetadata），未写入 lexicon/crossborder 版本。
- Make 命令与 Spec 文案存在不一致：Spec 中列举的 discover-crossborder/score-batched/pool-clear-and-freeze/crawl-crossborder/pool-stats 部分缺失对应的 Make 入口（脚本与能力分散在 scripts/ 与 makefiles/* 中，但未统一到根 Makefile）。
- 前端“样例提示”未聚焦跨境卖家场景：frontend/src/pages/InputPage.tsx 的 SAMPLE_PROMPTS 偏通用 SaaS/移动应用。
- Serena MCP 项目根目录指向“../最小化Navigator”，导致对本仓库的 serena 操作不可用（需修正工具配置）。

2) 是否已精确定位？
- 是。已逐一定位到文件与函数：
  - 回退未生效：crawler.yml 与 incremental_crawler/crawler_task 之间缺少驱动逻辑。
  - 版本标注缺失：report_service._build_metadata/_build_overview 未注入 lexicon 版本字段。
  - Make 入口缺失：根 Makefile 缺少若干 wrapper 目标，工具散落在 makefiles/*.mk 与 backend/scripts/*。
  - 样例不聚焦：SAMPLE_PROMPTS 定义位置与可替换文案已定位。
  - Serena 配置：serena 工具指向错误 project_root。

3) 精确修复方法？
- 抓取回退策略（建议最小可行修复，分层实现）：
  - 在 backend/app/tasks/crawler_task.py 的 _crawl_single/_crawl_seeds_impl 中引入按 tier 的回退流程：
    1) 首次按 tier 默认策略抓取；若 posts_count==0 → 记录 empty_hit。
    2) 若连续空集达到 global.fallback_thresholds.empty_to_widen：将 time_filter 扩至 fallback.widen_time_filter_to，并按 fallback.relax_sort_mix 选择主排序再重试一次。
    3) 若依然为空，且 allow_unfiltered_on_exhausted=true 或达 empty_to_unfiltered：改用 time_filter=“all”、sort=“top”，post_limit 提升 1.2×（上限 120）。
    4) 记录采取的回退策略到 CommunityCache（如 recovery_strategy 字段或 tier_assignments 附注）与 CrawlMetrics。
  - 补充单元测试：模拟 RedditAPIClient 返回空列表，断言回退顺序与最终参数。
- 跨境基线数据（不改接口，替换数据源/合并策略）：
  - 提供 backend/data/top1000_subreddits.json 的跨境版（保持同字段：name/tags/quality_score/default_weight/domain_label）。
  - 在 CommunityPoolLoader 合并时优先跨境白名单（config/community_whitelist.yaml，可选），并对非跨境条目赋较低 default_weight 与 priority。
- 报告版本标注：
  - 在 ReportOverview 或 ReportMetadata 中增加 lexicon_version（如从 backend/config/semantic_sets/crossborder*.yml 文件名或 YAML 内 version 字段解析）。
  - 后端环境变量允许覆盖：SEMANTIC_LEXICON_PATH 与 SEMANTIC_LEXICON_VERSION。
- Make 命令对齐：
  - 为已存在的脚本新增 wrapper：
    - discover-crossborder（若无脚本，先用 score_crossborder.py 的名字列表作为临时代替）。
    - score-batched（封装 backend/scripts/score_batched.sh）。
    - pool-clear-and-freeze（封装 backend/scripts/pool_clear.py 并输出 freeze 快照）。
    - crawl-crossborder（封装 crawler_task 旧版 Redis 热缓存路径）。
    - pool-stats（封装 backend/scripts/pool_stats.py）。
- 前端样例聚焦跨境：
  - 用亚马逊/Etsy/Shopify/TikTok Shop、物流（DHL/3PL）、合规（侵权/关税/VAT）等场景替换 SAMPLE_PROMPTS 文案（不改组件）。
- Serena MCP 修正：
  - 将 serena 的 project_root 指向当前仓库（RedditSignalScanner），并在 reports/ 记录自检通过截图/日志。

4) 下一步做什么？
- 优先实现抓取回退策略与单元测试，确保“空集不沉默”。
- 报告注入 lexicon_version 并在导出/下载接口校验存在性。
- 增加缺失的 Make 入口（不破坏现有 makefiles/*）。
- 更新前端样例提示为跨境卖家用语。
- 修正 Serena 配置并在 reports/ 记录 12s 内自检结果。

5) 这次修复的效果是什么？达到了什么结果？
- 抓取层：空集场景自动回退，冷热协同更稳健，Redis 命中率提升，crawl_metrics 中 empty_crawls 下降。
- 报告层：overview/metadata 可追溯词库/主题版本，便于质量门禁与回归。
- 工具层：一键命令与文档一致，减少操作偏差；前端样例更贴合跨境卖家场景，提高试用转化。

## 证据与对齐核查（关键文件与定位）
- 回退配置存在：backend/config/crawler.yml:29-48；运行未应用：
  - backend/app/services/incremental_crawler.py（无回退逻辑，遇空集直接返回）
  - backend/app/tasks/crawler_task.py（旧版抓取亦未按空集阈值回退，仅记录 empty/failed）
- 水位线与冷热双写：
  - 水位线：CommunityCache.last_seen_created_at（见 incremental_crawler._get_watermark/_update_watermark）
  - 热缓存（Redis）：backend/app/services/cache_manager.py（键：`reddit:posts:<subreddit>`，TTL 可配）
  - 热库（DB）：posts_hot（expires_at 字段）
- Tier 与治理：
  - 调度：backend/app/services/tiered_scheduler.py（crawler.yml 生效，黑名单过滤）
  - 黑名单：config/community_blacklist.yaml + backend/app/services/blacklist_loader.py
- 语义与实体：
  - 实体词典与管线：backend/config/entity_dictionary/* + app/services/analysis/entity_pipeline.py
  - 语义集工具链与门禁：Makefile + makefiles/tools.mk（semantic-*、stage2-metrics、semantic-acceptance）
- 报告 overview 字段：backend/app/services/report_service.py:_build_overview（total_communities/top_n/seed_source 已有）
- 前端样例：frontend/src/pages/InputPage.tsx:SAMPLE_PROMPTS（需跨境化）

## 工具与过程记录
- Serena MCP：当前 project_root 指向 ../最小化Navigator，无法直接读取本仓库；已停止进一步使用并改用 ripgrep 与本地审查。建议尽快修正并在 reports/ 补自检证据。

—— 以上为本次 Spec 009 代码审查结果与修复建议 ——

