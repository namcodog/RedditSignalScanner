# Reddit Signal Scanner: Analysis Engine SOP (v2.0)

> **生效日期**: 2025-11-28
> **适用范围**: 生产环境 T1 价值报告生成
> **维护责任人**: Data Gold Miner (AI Agent)

---

## 1. 核心架构 (The Architecture)

本系统采用 **"SQL-First Mining, Python-Logic Assembly"** 的混合架构。

*   **L1 数据层 (Postgres)**:
    *   `posts_hot` (JSONB): 存储原始爬取数据。
    *   **`mv_analysis_labels` (View)**: 核心资产。将 JSONB 拍平为关系型表，用于高频查询痛点。
    *   `mv_analysis_entities` (View): 用于竞品分析。
*   **L2 逻辑层 (Python)**:
    *   `analysis_engine.py`: 负责从视图提取数据，计算 P/S 比率，推导驱动力。
    *   `offline_label_fix.py`: 负责清洗存量脏数据，补充标签。
*   **L3 表现层 (LLM 报告)**:
    *   固定结构 prompt（T1 报告骨架），LLM 只做表达。

---

## 2. 离线数据修复 (Data Hygiene)

**场景**: 当发现 `content_labels` 为空，或需要应用新的痛点字典(`pain_dictionary.yaml`)时。

1.  **更新字典**: 修改 `backend/config/pain_dictionary.yaml`。
2.  **运行修复脚本**:
    ```bash
    python scripts/offline_label_fix.py
    ```
    *   *注意*: 该脚本会全量扫描 `posts_hot` 并原地更新 JSONB 字段。建议在低峰期运行。
3.  **刷新视图**:
    ```sql
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analysis_labels;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_analysis_entities;
    ```

---

## 3. 报告生成流程 (Production Workflow)

**场景**: 用户请求生成某赛道（如 "Dropshipping"）的洞察报告。

1.  **调用引擎**:
    使用 `app.services.analysis_engine.run_analysis`。
    ```python
    task = TaskSummary(product_description="dropshipping payment", keywords=["dropshipping", "stripe"])
    result = await run_analysis(task)
    ```
2.  **引擎内部逻辑**:
    *   **Scope**: 自动圈定相关社区 (Subreddits)。
    *   **Extract**: 从 `mv_analysis_labels` 提取 `category='pain'` 和 `category='intent'` 的数据。
    *   **Calculate**: 计算 P/S Ratio = `Pain / (Solution + Intent)`。
    *   **Derive**: 生成趋势/饱和度/战场画像/驱动力等完整结论字段。
    *   **Render**: LLM 按固定结构输出报告（insights 主线 + facts_slice 证据）。
3.  **获取产物**:
    *   `result.report_html`: 最终报告内容。
    *   `result.confidence_score`: 若低于 0.6，建议提示用户由人工复核。

---

## 4. 关键指标解读 (Metric Guide)

| 指标 | 正常范围 | 异常解读 | 行动建议 |
| :--- | :--- | :--- | :--- |
| **P/S Ratio** | 0.5 - 2.0 | > 5.0 | 市场极度不满，或 Solution 关键词漏配。 |
| **P/S Ratio** | 0.5 - 2.0 | < 0.2 | 市场已饱和，或全是软文。 |
| **Confidence** | > 0.7 | < 0.4 | 数据量不足 (<100贴)，结论不可信。 |
| **Pain Density** | 30% - 60% | > 80% | 强信号战场，立即切入。 |

---

## 5. 扩展开发指南 (Dev Guide)

*   **添加新驱动力**: 修改 `analysis_engine.py` 中的 `_derive_driver` 函数。
*   **添加新机会类型**: 修改 `_extract_business_signals_from_labels`，增加对 `category='gap'` 的处理。
*   **修改报告模板**: 复用 T1 固定结构 prompt（报告骨架与模块顺序保持不变）。

---

**End of SOP**
