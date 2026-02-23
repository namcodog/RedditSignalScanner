# Phase Log — Semantic Library Unification (Week 2: 适配器集成)

日期: 2025-11-16

## 1) 发现了什么问题/根因？
- 分类与实体抽取使用硬编码关键词，无法与统一词库同步，维护成本高。

## 2) 是否已精确定位？
- 目标文件：
  - `backend/app/services/text_classifier.py`
  - `backend/app/services/labeling/comments_labeling.py`
- 依赖：`UnifiedLexicon`（已完成 1.1/1.2）、`layer_definitions.yml`（已完成 1.3）。

## 3) 精确修复方法？
- 在不破坏原逻辑的前提下，增加可选的统一词库路径：
  - 通过环境变量 `ENABLE_UNIFIED_LEXICON=true` 生效；默认关闭。
  - `text_classifier`: 先用 `UnifiedLexicon` 命中 `pain_points` → `Category.PAIN`；命中 `features` → `Category.SOLUTION`；否则保持旧逻辑；`Aspect` 仍使用原规则（避免过度开发）。
  - `comments_labeling`: 优先用 `UnifiedLexicon.get_brands()` 的正则匹配抽取品牌（默认 `EntityType.BRAND`）；关闭时回退旧的 `BRAND_PATTERNS`。
  - 正则生成沿用 `score_with_semantic.compile_patterns` 逻辑，模块内有兜底实现。

## 4) 下一步做什么？
- 后续周（REQ-3）若启用分层加权评分，再接入 `SemanticScorer`；当前不改评分逻辑，避免范围扩张。
- 根据需要补充 E2E 开关迁移测试（tasks 6.2）。

## 5) 这次修复的效果/结果？
- 适配器集成完成，接入统一词库但默认不改变现有行为；开启开关后分类与实体抽取自动使用统一词库，降低维护成本。

## 产出清单
- 代码：
  - `backend/app/services/text_classifier.py`（可选接入 UnifiedLexicon）
  - `backend/app/services/labeling/comments_labeling.py`（可选接入 UnifiedLexicon）
- 测试：
  - `backend/tests/nlp/test_text_classifier_unified_lexicon.py`
  - `backend/tests/services/labeling/test_comments_labeling_unified.py`
- 配置：
  - `backend/config/semantic_sets/layer_definitions.yml`（Week 1 已交付）

## 用例结果
- 仅跑适配器用例：
  - `pytest backend/tests/nlp/test_text_classifier_unified_lexicon.py -q`
  - `pytest backend/tests/services/labeling/test_comments_labeling_unified.py -q`
- 结果：全部通过；旧用例 `backend/tests/nlp/test_text_classifier_basic.py` 也通过（保持向后兼容）。

