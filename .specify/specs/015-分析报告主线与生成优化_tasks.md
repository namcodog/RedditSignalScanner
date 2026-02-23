# Tasks: 分析报告主线与生成优化（Spec 015）

> 约定：任务编号以 `R015-Txx` 表示，便于在 PR / Commit 中引用。

---

## Phase 0: 主线确认与文档落地

- [x] **R015-T01** 主业务线梳理  
  - 汇总并确认以下文件为“官方主业务线”：  
    - `backend/app/api/v1/endpoints/analyze.py`  
    - `backend/app/tasks/analysis_task.py`  
    - `backend/app/services/analysis_engine.py`  
    - `backend/app/services/report_service.py`  
    - `backend/app/api/v1/endpoints/reports.py`  
  - 输出一份简明的调用链图（文本/PlantUML 均可）。

- [x] **R015-T02** 主业务线说明书文档  
  - 在 `docs/` 下新增 `2025-11-主业务线说明书.md`（或同等命名）；  
  - 内容覆盖：入口/调度/分析/报告/出口 + 数据准备白名单；  
  - 关联 Spec：在文档头部链接 Spec 008/010/013/015。

- [x] **R015-T03** `.specify` 计划与任务初始化  
  - 将本 `plan.md` / `tasks.md` 链入 Spec 015 的主文档；  
  - 若需要，创建 `research.md` 记录对现有脚本/数据状态的调研。

---

## Phase 1: 数据就绪与 Stats Layer

- [x] **R015-T10** T1 数据状态盘点  
  - 编写一个小脚本或 SQL 清单，检查：  
    - `community_pool` 中 `tier='high' AND is_active=true` 的社区数量；  
    - 这些社区在过去 12 个月内在 `posts_raw`/`comments` 中的帖子/评论数量；  
    - `content_labels` / `content_entities` 对应评论覆盖率。  
  - 把结果记录到 `reports/phase-log/phase015-data-audit.md`。

- [x] **R015-T11** 必要数据准备脚本执行（如需）  
  - 根据 T10 的盘点结果，决定是否需要重新执行：  
    - `backfill_community_pool_from_csv_*.py`  
    - `score_with_semantic.py --from-pool`  
    - 评论标注/实体提取脚本  
  - 记录执行命令、耗时和结果到同一份 phase log。

- [x] **R015-T12** Stats Layer 接口设计  
  - 在 `backend/app/services/` 下设计一个新的模块接口（例如 `t1_stats.py`）：  
    - 输入：社区列表 + 时间窗口；  
    - 输出：社区活跃度、全局/分社区/分 Aspect 的 P/S 比、品牌与痛点共现。  
  - 写出函数签名与返回数据结构（Pydantic 模型或 TypedDict）。

- [x] **R015-T13** Stats Layer 实现与快照  
  - 实现 R015-T12 中定义的 Stats Layer；  
  - 提供简单 CLI（或脚本入口）在本地跑一遍 T1 配置，生成：  
    - `reports/local-acceptance/t1-stats-snapshot.json`；  
  - 验证核心字段是否与 `t1价值的报告.md` 中的描述相符（例如 P/S 比量级）。

---

## Phase 2: Clustering Layer

- [x] **R015-T20** Clustering 需求与输出结构确认  
  - 基于 `content_labels` 现有字段，确定：  
    - 使用哪些列作为聚类输入（category/aspect/keywords/entities）；  
    - 聚类结果的目标结构（topic/size/aspects/top_keywords/sample_comments）。  
  - 更新 Spec 015 中 Clustering 小节（如有需要）。

- [x] **R015-T21** Clustering 模块实现（规则版）  
  - 新增 `backend/app/services/t1_clustering.py`（示例命名）：  
    - 先实现基于 Aspect + 关键词的规则聚类，形成 3–5 个痛点簇；  
    - 每个簇返回若干代表性评论（可用 score/awards 排序）。  
  - 为模块写最基本的单元测试或 smoke test。

- [x] **R015-T22** Clustering 输出快照与人工对齐  
  - 对 T1 配置运行 Clustering，生成：  
    - `reports/local-acceptance/t1-pain-clusters.json`；  
  - 手动对比 `t1价值的报告.md` 中的 3 大痛点，确认语义是否大体一致，并记录差异点。

---

## Phase 3: Report Agent（T1 报告生成器）

- [x] **R015-T30** Report Agent 输入/输出契约设计  
  - 设计一个 Report Agent 接口（例如 `t1_market_agent.py`）：  
    - 输入：Stats Layer 输出 + Clustering 输出 + 可选的 analysis insights；  
    - 输出：Markdown 文本，章节结构对齐 `t1价值的报告.md`。  
  - 明确 Prompt Pipeline 的步骤（先生成提纲，再生成各章节）。

- [x] **R015-T31** Report Agent 实现（离线路径）  
  - 实现 Report Agent 模块，使用现有 LLM/模板基础（可以复用 `controlled_generator` 思路）；  
  - 提供 CLI 命令（如 `make t1-report-demo` 或 `python backend/scripts/generate_t1_market_report.py`），生成：  
    - `reports/t1-auto.md`。  
  - 控制运行时间和 LLM 调用次数，避免超出当前配额/成本。

- [x] **R015-T32** T1 报告对齐评审  
  - 选取至少 1 个真实 task 或固定 T1 配置，生成自动报告；  
  - 与 `reports/t1价值的报告.md` 做人工对比：  
    - 结构是否齐全（决策卡片/战场/痛点/驱动力/机会卡）；  
    - 关键结论是否站得住脚（不硬拗、不瞎编数字）；  
  - 记录评审结果与改进建议到 `reports/phase-log/phase015-t1-review.md`。

---

## Phase 4: 接入主业务线与配置开关

> 当前重点：请优先攻克 R015-T40~T42，完成 ReportService 集成与配置清理。

- [x] **R015-T40** ReportService 集成方案设计  
  - 在不破坏现有行为的前提下，设计：  
    - `ENABLE_MARKET_REPORT` 与 `REPORT_MODE` 的组合如何决定是否调用 T1 Report Agent；  
    - 当 T1 pipeline 失败或数据不足时的 fallback 策略（技术版报告/错误提示）。

- [x] **R015-T41** ReportService 集成实现  
  - 在 `backend/app/services/report_service.py` 中：  
    - 根据配置决定是否调用 Stats + Clustering + Report Agent；  
    - 将生成的 Markdown 转 HTML 填入 `report_html` 字段；  
    - 保证测试环境/现有集成测试不被破坏。  

- [ ] **R015-T42** 配置与文档更新  
  - 清理/统一 `report_mode` 的重复定义；  
  - 在配置文档中解释：technical/executive/market 三种模式的含义与使用场景；  
  - 更新相关 Spec（008/010/013）中对报告生成的描述，让它们引用这条新主线。

---

## Phase N: 验收与回顾

- [x] **R015-T50** 验收检查清单  
  - 按 Spec 015 的 DoD 逐条检查：  
    - 主线说明是否存在且可读；  
    - T1 报告能力是否可重复；  
    - Stats / Clustering / Report Agent 是否各自可独立测试；  
    - 现有 `/api/report` 行为是否未被意外破坏。  

- [x] **R015-T51** 阶段总结与 phase log  
  - 在 `reports/phase-log/phase015.md` 记录：已完成项、未完成项、与最初预期的差异、下一个阶段建议。
