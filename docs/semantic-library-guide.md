# 语义库统一使用指南（Unified Lexicon）

本指南说明如何使用统一语义库（SSOT），如何提取候选词、评分比对与迁移。

## 开关与路径
- 环境变量：
  - `ENABLE_UNIFIED_LEXICON=true` 打开统一词典接入
  - `SEMANTIC_LEXICON_PATH=backend/config/semantic_sets/unified_lexicon.yml`
- 默认词典：`backend/config/semantic_sets/unified_lexicon.yml`（SSOT）。

## 统一入口
- 代码侧：
  - `UnifiedLexicon`（加载/查询）
  - `SemanticScorer`（分层权重评分，旧算法兼容开关）
  - `CandidateExtractor`（从 posts_hot 自动发现候选）
- 脚本侧：
  - `backend/scripts/score_with_semantic.py`（评分，`--enable-layered`）
  - `backend/scripts/compare_scoring_algorithms.py`（新旧算法对比，输出相关性）
  - `backend/scripts/semantic_extract_candidates.py`（导出候选CSV）

## 常用命令
- 评分：`make semantic-score`
- 对比：`make semantic-compare`
- 候选：`make semantic-candidates-extract`
- 迁移（干跑）：`make semantic-migrate`

## 候选词提取与晋升
1. 运行：
   ```bash
   make semantic-candidates-extract LOOKBACK=30 MINFREQ=5 OUTPUT=backend/reports/semantic-candidates/candidates.csv
   ```
2. 人工审核 CSV（canonical/aliases/confidence/frequency/suggested_layer/evidence）
3. 晋升（建议后续提供 CLI `--promote`，当前手工编辑 unified_lexicon.yml 并发起 PR）

## 评分比对与监控
- 新旧算法对比：
  ```bash
  make semantic-compare
  ```
  输出 `backend/data/semantic_compare.csv`，控制台打印每主题相关性；异常波动＜=10% 为宜。

## 迁移策略
- 干跑迁移：
  ```bash
  make semantic-migrate
  ```
  打印新增项差异；`--apply` 会备份后写入 `themes.migration`，可安全回滚。

## 注意事项
- 统一词典的主题键为 `themes`，每个主题下 `brands/features/pain_points/aliases/exclude/weights`。
- 代码默认大小写不敏感匹配；导出/展示时保持 canonical 原大小写。
- 性能建议：词典冷启动 < 500ms；单次评分 < 50ms；批量不超过 30s（基于设计文档目标）。
