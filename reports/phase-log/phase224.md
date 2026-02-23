# Phase 224

## 目标
- KAG P0：混合检索、向量去重、结构化知识骨架进入主链路。
- P1：Makefile/SOP/PRD 口径同步。

## 完成内容
- 新增混合检索模块（关键词 + 向量召回，pgvector）并接入分析主链路。
- 向量相似度去重：在文本去重后追加 embedding 去重，避免重复内容污染报告。
- 结构化知识骨架：输出 `knowledge_graph`（社区→痛点→证据→场景/驱动力），写入 `facts_slice` + `sources`。
- 新增配置开关与参数：混合检索、向量去重阈值、召回权重等。
- Makefile 增补 KAG 流水线目标（data-embeddings / data-pipeline-kag）。
- PRD-03 / PRD-02 / 清洗SOP 更新口径。
- 新增 KAG 验收脚本：`backend/scripts/kag_acceptance.py` 并固化到 `make kag-acceptance`。

## 测试
- `pytest -q backend/tests/services/test_deduplicator_vector.py backend/tests/services/test_hybrid_retriever.py backend/tests/services/test_analysis_engine_hybrid_merge.py`
- 备注：pytest 有 `pkg_resources` 弃用警告（非功能性）。

## 结论
- KAG P0 已落地，主链路具备混合检索 + 向量去重 + 知识骨架输出。
- P1 文档与 Makefile 已同步，端到端验收脚本后续补齐。
