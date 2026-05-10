# Phase 250 - Round 2 数据加工层深度审计

执行时间: 2026-03-13

## 1. 发现了什么

- 按 `系统全量审计扫描计划.md` 的 Round 2 范围复核后，实际审计范围是：
  - `backend/app/services/analysis/`（排除 `analysis_engine.py` 与 `__init__.py`）共 **29 个文件**
  - `backend/app/services/facts_v2/` 共 **3 个文件**
  - `backend/app/tasks/analysis_task.py` 共 **1 个文件**
  - 合计 **33 个文件 / 10,910 行**
- 定量扫描结果：
  - `except`: **72**
  - `type: ignore`: **16**
  - SQL/查询相关调用: **105**
- Round 2 和 Round 1 的味道不一样：
  - Round 1 的主问题是“状态骗人”
  - Round 2 的主问题是“口径会悄悄变”
- 也就是说，这层最危险的不是直接报错，而是：
  - 悄悄降级
  - 悄悄换口径
  - 悄悄补兜底数据，然后继续对外当正式结果展示

## 2. 是否需要修复

- 需要。
- 优先级建议：
  - P0：`analysis_task.py`
  - P1：`pain_cluster.py` + `facts_v2/midstream.py` + `facts_v2/quality.py`
  - P1：`topic_profiles.py` + `t1_stats.py` + `facts_v2/midstream.py`

## 3. 精确修复方法

### 3.1 P0 - `analysis_task.py`：分析结果与展示结果已经混层

- 证据：
  - `backend/app/tasks/analysis_task.py:397-403`
    - `facts_v2_package` 缺失时，会直接 `_build_minimal_facts_package(...)`
  - `backend/app/tasks/analysis_task.py:523`
    - 用 `task.id` 拼接伪 Reddit 链接
  - `backend/app/tasks/analysis_task.py:536`
    - 直接写入 `Auto generated evidence`
  - `backend/app/tasks/analysis_task.py:628-661`
    - “确保至少生成 3 张卡片”的兜底逻辑，会继续补卡片和证据
  - `backend/app/tasks/analysis_task.py:670`
    - 洞察持久化失败不影响主流程
- 风险：
  - `AnalysisResult`、`facts_v2_package`、`InsightCard/Evidence` 三层已经不完全是一回事。
  - 对外 API 可能看到的是“补出来的卡片 / 补出来的证据 / 伪链接”，不是分析引擎真实抽出来的证据。
  - 这会让“分析结果可信度”和“展示出来像不像真的”混在一起。
- 建议：
  - 把“真实分析结果持久化”和“展示兜底生成”拆成两层。
  - 如果必须兜底，必须显式标记 `synthetic=true` / `fallback_generated=true`，不能伪装成真实 Reddit 证据。
  - `facts_v2_package_missing` 不应该直接无声补最小包后继续走成功路径，至少要把降级事实明确打进 lineage / diagnostics。

### 3.2 P1 - `pain_cluster.py` → `facts_v2/midstream.py` → `facts_v2/quality.py`：隐性降级链

- 证据链：
  - `backend/app/services/analysis/pain_cluster.py:524-532`
    - `cluster_pain_points_auto()` 在 DB 聚类失败、fallback 失败时都会直接吞掉并返回 `[]`
  - `backend/app/services/facts_v2/midstream.py:157-171`
    - `compute_brand_pain_v2()` 里如果 `pain_clusters` 为空，直接 `return []`
  - `backend/app/services/facts_v2/quality.py:167`
    - 质量门会打 `pains_low`
  - `backend/app/services/facts_v2/quality.py:183`
    - 质量门会打 `brand_pain_low`
- 风险：
  - 一次上游聚类失败，会被包装成“痛点太少 / 品牌痛点太少”。
  - 质量门能看到症状，但看不到根因。
  - 这会把“真实数据稀薄”和“算法/DB 降级失败”混成一类。
- 建议：
  - 这条链要补显式 diagnostics：
    - `pain_clusters_pipeline_status`
    - `brand_pain_pipeline_status`
    - `degraded_reason`
  - 质量门在看到 `pains_low/brand_pain_low` 时，还要能知道是“样本不足”还是“上游失败后变空”。

### 3.3 P1 - `topic_profiles.py` / `t1_stats.py` / `facts_v2/midstream.py`：配置层与语义层静默降级

- 证据：
  - `backend/app/services/analysis/topic_profiles.py:295-310`
    - `_load_topic_profiles_payload()` 读 YAML 失败直接 `continue`，最后返回 `{}`
  - `backend/app/services/analysis/t1_stats.py:601-605`
    - `fetch_topic_relevant_communities()` 的 embedding 失败只 `print(...)`，然后退回 keyword-only
  - `backend/app/services/facts_v2/midstream.py:355-372`
    - `_resolve_domain_pain_config()` 读 domain pain 配置失败直接返回 `{}`
- 风险：
  - topic profile 没加载成功、embedding 没算出来、domain pain 配置失效，这三种情况都会让系统继续跑。
  - 但调用方很难知道这次拿到的是“配置失效版结果”还是“完整语义版结果”。
  - 这会直接影响社区发现、上下文过滤、品牌发现、quality gate 的判断基础。
- 建议：
  - 这些“可继续运行”的降级可以保留，但必须统一做成：
    - 模块级 logger
    - 结构化降级日志
    - 写入 lineage / diagnostics
  - `print()` 这类临时输出不够，后续排查时没有上下文，也不会稳定进日志系统。

## 4. 健康样本

- `backend/app/services/analysis/signal_extraction.py`
  - `SignalExtractor.extract()` 本身职责比较清楚：归一化输入 → 提取 pain / competitor / opportunity / solution → 排序输出。
  - 说明 Round 2 也不是整层都乱，问题主要集中在“持久化兜底”和“静默降级链”。
- `backend/app/services/facts_v2/quality.py`
  - 虽然会接收很多降级后的症状，但它自己的输入/输出合同是清楚的，而且已有较完整测试覆盖。

## 5. 验证依据

- Serena 符号级概览：
  - `analysis_task.py`：顶层函数多，`_store_analysis_results()` 单函数 300+ 行，还包含多个内嵌 helper
  - `t1_stats.py`：社区相关性、统计快照、实体情感都收在一个文件里
  - `topic_profiles.py`：配置加载、匹配、过滤、fetch keyword 构建全耦在一起
  - `midstream.py`：source_range、pain/brand/solution 中间结果都在一个模块中
- 关键引用链：
  - `cluster_pain_points_auto()` 被 `analysis_engine.run_analysis()` 使用
  - `quality_check_facts_v2()` 同时被 `analysis_engine` 和 `generate_t1_market_report.py` 使用
  - 说明这轮发现的问题会同时影响分析链路和报告链路，不是单点问题

## 6. 这次执行的价值

- 这次把 Round 2 的真正主风险找准了：
  - 不是“算法实现细节不完美”
  - 而是“算法层、facts 层、展示层已经开始说不同的话”
- 这为下一轮修复明确了方向：
  - 先拆“真实分析结果”和“展示兜底”
  - 再把降级链显式化
  - 最后统一配置/语义失败的可观测性
