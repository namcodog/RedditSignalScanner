# Semantic Lexicon Changelog

## [v1.1.0] - Semantic Library Unification
- Added: UnifiedLexicon (SSOT) with safe YAML loading and query APIs
- Added: SemanticScorer (layered scoring with legacy compatibility)
- Added: CandidateExtractor (auto-discovery from posts_hot, CSV export)
- Changed: score_with_semantic.py refactored to use UnifiedLexicon + SemanticScorer
- Added: compare_scoring_algorithms.py to benchmark new vs old scoring
- Tooling: Makefile targets semantic-score, semantic-compare, semantic-candidates-extract, semantic-migrate
- Migration: migrate_to_unified_lexicon.py (dry-run by default, --apply appends under themes.migration)

## [v2.1] - Stage 0 complete
- Built 500-term semantic_sets with L1–L4 layers
- Fixed brand misclassification via hard negatives + case-insensitive lookup
- Enhanced pain_points extraction with sentiment + pattern triggers
- Added make targets for entity dict and metrics

## [v2.0] - Initial layered draft
- Introduced four-layer structure and JSON-compatible YAML format
- Seeded minimal brands/features/pain_points

## [Calibration calib-20251110] - 2025-11-10
- add: 3
- blacklist: 20
