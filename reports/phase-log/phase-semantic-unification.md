# Phase – Semantic Library Unification（Week 1-2 基础层）

## 今日产出（测试优先）
- 新增核心类与测试：
  - UnifiedLexicon：`backend/app/services/semantic/unified_lexicon.py`
  - SemanticScorer：`backend/app/services/semantic/semantic_scorer.py`
  - 测试：
    - `backend/tests/services/semantic/test_unified_lexicon.py`
    - `backend/tests/services/semantic/test_semantic_scorer.py`
- 迁移脚本：
  - `backend/scripts/migrate_to_unified_lexicon.py`（支持 dry-run / --apply，解析 text_classifier/BRAND_PATTERNS，追加到 unified_lexicon.yml 的 migration 主题，备份原件）

## Week 4 – 自动发现（NLP 基础版）
- 候选词提取：`backend/app/services/semantic/candidate_extractor.py`
  - `CandidateExtractor.extract_from_db()`：正则短语抽取（2-3词、首字母大写/驼峰/全大写），过滤词典既有项与停用词，频次+大写一致性置信度，功能词共现推断层级（有FBA/PPC/SEO→L1）
  - `export_to_csv()`：导出审核用CSV
- 单测：`backend/tests/services/semantic/test_candidate_extractor.py`
  - Temu/TikTok Shop 命中，The Product 排除；Amazon（已在词典）被过滤；TEMU 全大写高置信；Temu+FBA→建议L1；CSV格式校验

## Week 3 – 算法优化
- 重构脚本：`backend/scripts/score_with_semantic.py`
  - 改为使用 `UnifiedLexicon + SemanticScorer`，保留原CLI与输出列（semantic_score_*, coverage_*, density_*, purity_*）
  - 新增 `--enable-layered` 开关（默认开启）
- 对比工具：`backend/scripts/compare_scoring_algorithms.py`
  - 同一批文本对新旧算法打分，输出 `backend/data/semantic_compare.csv`，控制台打印相关性

## 统一反馈四问
1) 发现了什么问题/根因？
- 词典分散（硬编码 + 多个 YAML 版本），调用方获取入口不统一；评分算法仅有 v0（coverage×density×purity），缺层级权重。

2) 是否已精确定位？
- SSOT 入口：`UnifiedLexicon`（含查询接口、模式编译复用）；
- 评分：`SemanticScorer`（分层权重 + 旧算法兼容开关）；
- 迁移：脚本从现有硬编码提取补充到统一词典（dry-run 默认安全）。

3) 精确修复方法？
- 统一词典：YAML safe_load + 旧格式兼容，layer 默认 L2；
- 查询：get_brands/features/pain_points/theme_terms/patterns；
- 评分：L1-4 覆盖率加权（0.4/0.3/0.2/0.1），L1<0.3 罚分×0.7，结合加权密度+纯度；
- 迁移：diff 非重复词并可 --apply 追加到 `themes.migration`；回退通过备份。

4) 下一步做什么？
- （可选）读取 `layer_definitions.yml` 与 `layer_mapping.csv`，完善 layer 赋值；
- （可选）提供 CLI：--validate/--stats/--promote；
- （可选）在现有分类/实体抽取处注入 UnifiedLexicon（灰度开关）。

5) 本次效果/结果？
- Week1-2 基础层四项任务（1.1/1.2/1.4/3.1）按“不过度开发”完成，测试通过可运行；
- 不破坏现有路径（默认回退到 crossborder_v2.2_calibrated.yml，特性可渐进开启）。
