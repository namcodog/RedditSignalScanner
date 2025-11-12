# 语义库开发计划 v2.1 - 执行摘要（基于四层语义结构）

> **文档编号**: 011
> **创建日期**: 2025-01-04
> **更新日期**: 2025-01-04（融入四层语义结构 + 500 词目标）
> **状态**: Ready for Implementation
> **预计完成**: 2025-01-25（21 天，4 阶段）

---

## 📊 一句话总结

**基于 5 个 Reddit 社区的四层语义结构，从 0 抓取 22k 真实帖子，提取 500 个词汇（semantic_sets）+ 100 个核心实体（entity_dict），使命中率从 62% 提升到 70%，精准率从 68% 提升到 75%，pain_points 从 10-15 个增加到 100-130 个。**

---

## 🔑 三大核心改变

### 1️⃣ 从 0 抓取，不依赖已有数据
- ❌ **原有词典库不准确，不满足需求**
- ✅ **使用 Pushshift API + Reddit API 深度抓取历史语料**
- ✅ **22k 帖，12 个月时间范围，确保数据质量**

### 2️⃣ 目标 500 词，比原计划更充分
- ❌ **原计划 200-300 词偏少**
- ✅ **semantic_sets: 500 词（L1-L4 四层结构）**
- ✅ **entity_dictionary: 100 词（核心实体，用于报告）**

### 3️⃣ 完整 NLP 流程，对齐《语义库框架.md》
- ✅ **L1 作为语义坐标**：构建 embedding 基线
- ✅ **痛点主题标注**：结合情感分析（VADER/TextBlob）
- ✅ **层级对齐**：所有词对齐到 L1 baseline

---

## 🎯 核心目标

### 业务价值

| 指标 | 当前值 | 目标值 | 提升幅度 |
|------|--------|--------|---------|
| **Coverage（命中率）** | 62% | 70% | +13% |
| **Precision@20（精准率）** | 68% | 75% | +10% |
| **F1 Score** | 65% | 72% | +11% |
| **误判率** | ~15% | <5% | -67% |

### 技术价值

- ✅ 从人工标注（9-180 条不均）→ 自动挖掘（200+ 条稳定）
- ✅ 从简单正则 → 混合匹配（exact/phrase/semantic）
- ✅ 从静态词表 → 自进化系统（每周迭代）
- ✅ 从黑盒评分 → 可解释指标（Coverage/Precision/F1）

---

## 🆕 核心改变：四层语义结构

### 从 5 个社区构建语义库

```text
┌──────────────────────────────────────────┐
│ L4：情绪层（痛点、人性、焦虑）            │
│   → r/dropshipping（2.5k 帖）             │
│   → r/dropship（3.5k 帖）                 │
├──────────────────────────────────────────┤
│ L3：执行层（运营策略、工具链）            │
│   → r/Shopify（5k 帖）                    │
│   → r/dropship（3.5k 帖）                 │
├──────────────────────────────────────────┤
│ L2：平台层（规则、机制、生态）            │
│   → r/AmazonSeller（6k 帖）               │
│   → r/Shopify（5k 帖）                    │
├──────────────────────────────────────────┤
│ L1：基础层（通用语言、行业框架）          │
│   → r/ecommerce（5k 帖）                  │
└──────────────────────────────────────────┘

总计：22k 真实帖子
```

### 解决的核心问题

1. **实体词典与语义集边界模糊** → 明确职责分工
2. **pain_points 词库稀疏**（10-15 个）→ 增加到 50-80 个
3. **数据源不明确** → 5 个社区，22k 帖
4. **缺乏语义层级** → 四层结构（L1-L4）

---

## 📅 时间线（4 阶段，21 天）

### 🔥 阶段 0：从 5 个社区提取词汇（5-7 天）

| 任务 | 工时 | 交付物 | 验收标准 |
|------|------|--------|---------|
| **抓取 5 个社区语料** | 2-3 天 | 5 个 JSONL 文件（22k 帖） | 每个社区达到目标数量 |
| **提取四层语义词汇** | 3-4 天 | `crossborder_v2.0.yml`（200-300 词） | 四层结构清晰，总词条 200-300 |
| **明确边界提取 entity_dict** | 1 天 | `crossborder_v2.csv`（50-80 词） | 边界清晰，核心实体完整 |

**里程碑**: Day 8 完成 v2.0 发布

---

### ⚙️ 阶段 1：实现匹配策略与版本管理（2 天）

| 任务 | 工时 | 交付物 | 验收标准 |
|------|------|--------|---------|
| **实现 precision_tag 匹配** | 1 天 | `hybrid_matcher.py` + 测试 | 测试通过率 100%，支持四层 |
| **建立词库版本管理** | 0.5 天 | `CHANGELOG.md` + `versions/` | 记录 v2.0 变更，历史可追溯 |

**里程碑**: Day 10 完成 v2.1 发布

---

### 📊 阶段 2：质量指标与候选词挖掘（3-4 天）

| 任务 | 工时 | 交付物 | 验收标准 |
|------|------|--------|---------|
| **建立质量指标看板** | 1.5 天 | `calculate_metrics.py` + `metrics.csv` | Coverage≥0.7, Precision@20≥0.75 |
| **实现候选词挖掘** | 1.5 天 | `extract_candidates.py` + 按层级分类 | 每簇 2-10 个，按 L1-L4 分类 |
| **优化 exclude 词表** | 1 天 | `exclude_reasons.csv` + 更新词库 | exclude 列表 ≥20 个，误判率降 50% |

**里程碑**: Day 14 完成 v2.2 发布

---

### 🔄 阶段 3：别名归并与人工校准（5-7 天）

| 任务 | 工时 | 交付物 | 验收标准 |
|------|------|--------|---------|
| **实现别名归并** | 2 天 | `merge_aliases.py` + 层级感知 | 通过率 ≥70%，支持层级感知 |
| **建立人工校准回路** | 2.5 天 | `weekly_calibration.py` + 分层抽样 | 每周固定节奏，指标改善 |
| **实现受控报告生成** | 2.5 天 | `controlled_generator.py` + 四层模板 | 结构稳定，支持四层语义 |

**里程碑**: Day 21 完成 v2.3 发布

---

## 🏗️ 架构设计亮点

### 双层词库架构

```
核心种子词库（Layer 1）
  - 50-100 精选词条
  - 人工维护，月度更新
  - 高精度、低召回
  ↓ 自动扩展
候选词库（Layer 2）
  - 200-500 动态词条
  - 自动挖掘 + 人工审核
  - 高召回、中精度
```

### 三种匹配策略

| 策略 | 适用场景 | 示例 |
|------|---------|------|
| **exact** | 品牌名、平台名 | "Amazon" 匹配 "I sell on Amazon" |
| **phrase** | 功能词、痛点 | "dropshipping" 匹配 "drop-shipping" |
| **semantic** | 长尾、同义 | "saturated" 匹配 "too competitive" |

### 自动扩展流程

```
聚类分析 → 短语挖掘 → 别名归并 → 人工审核 → 词库更新
   ↓          ↓          ↓          ↓          ↓
HDBSCAN   KeyBERT    Jaro+Cos   10% 抽样   版本号+1
```

---

## 📦 交付物清单（10 个新文件）

### 已创建（3 个）

1. ✅ `backend/config/semantic_sets/crossborder_v2_structure.yml`（架构示例）
2. ✅ `backend/scripts/mine_pain_points.py`（痛点挖掘）
3. ✅ `backend/app/services/analysis/hybrid_matcher.py`（混合匹配器）

### 待创建（7 个）

4. ⏳ `backend/config/semantic_sets/CHANGELOG.md`（变更日志）
5. ⏳ `backend/scripts/extract_candidates.py`（候选词挖掘）
6. ⏳ `backend/scripts/calculate_metrics.py`（质量指标）
7. ⏳ `backend/scripts/merge_aliases.py`（别名归并）
8. ⏳ `backend/scripts/weekly_calibration.py`（人工校准）
9. ⏳ `backend/app/services/report/controlled_generator.py`（报告生成）
10. ⏳ `backend/config/semantic_sets/exclude_reasons.csv`（排除词原因）

---

## 🚨 风险与缓解

### 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **语义模型性能差** | 高 | P0 不依赖，P1 可选启用 |
| **候选词质量低** | 中 | 设置 min_freq 和 confidence 阈值 |
| **词库过拟合** | 高 | 监控 Drift 指标，超过 0.2 告警 |

### 数据质量风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **训练数据偏差** | 高 | 多来源数据（不同时间段、社区） |
| **噪音数据污染** | 中 | 强化 exclude 列表 + 人工审核 |

---

## 🎬 立即开始（5 分钟）

### 快速启动命令

```bash
# 1. 进入项目目录
cd /Users/hujia/Desktop/RedditSignalScanner

# 2. 创建工作目录
mkdir -p backend/reports/local-acceptance
mkdir -p backend/config/semantic_sets/versions

# 3. 备份当前词库
cp backend/config/semantic_sets/crossborder.yml \
   backend/config/semantic_sets/versions/crossborder_v1.0_backup_$(date +%Y%m%d).yml

# 4. 运行 pain_points 挖掘（如果数据文件存在）
python backend/scripts/mine_pain_points.py \
  --data backend/data/crossborder_candidates.json \
  --lexicon backend/config/semantic_sets/crossborder.yml \
  --output backend/reports/local-acceptance/pain_points_candidates.csv \
  --min-freq 5

# 5. 查看结果
head -n 11 backend/reports/local-acceptance/pain_points_candidates.csv | column -t -s,
```

### 详细步骤

参考：`.specify/specs/011-quick-start-guide.md`

---

## 📈 成功指标（如何判断成功）

### P0 验收（本周五）

- ✅ `pain_points_candidates.csv` 包含 ≥50 条
- ✅ 词库版本号更新为 `v1.1`
- ✅ `HybridMatcher` 测试通过率 100%
- ✅ mypy --strict 无错误

### P1 验收（下周五）

- ✅ `candidates.csv` 每簇 2-10 个候选词
- ✅ `metrics.csv` 包含 Coverage/Precision/F1
- ✅ exclude 列表扩充到 ≥20 个

### P2 验收（第三周五）

- ✅ 别名映射通过率 ≥70%
- ✅ 每周校准流程运行成功
- ✅ 报告生成结构稳定，证据可溯源

### 最终验收（v2.0 发布）

- ✅ Coverage ≥ 70%（当前 62%）
- ✅ Precision@20 ≥ 75%（当前 68%）
- ✅ F1 Score ≥ 72%（当前 65%）
- ✅ 误判率 < 5%（当前 ~15%）

---

## 🔗 相关文档

1. **完整计划**: `.specify/specs/011-semantic-lexicon-development-plan.md`
2. **快速启动**: `.specify/specs/011-quick-start-guide.md`
3. **原始思路**: `docs/reference/词义库思路.md`
4. **项目规范**: `AGENTS.md`
5. **实施清单**: `docs/2025-10-10-实施检查清单.md`

---

## 💬 关键决策记录

### 为什么选择双层架构？

**问题**: 单一词库难以平衡"精准度"和"覆盖面"。

**方案**: 
- Layer 1（核心）：高精度，人工维护，用于基准评分
- Layer 2（候选）：高召回，自动挖掘，用于发现新趋势

**收益**: 既保证核心词的质量，又能快速响应新兴话题。

---

### 为什么 P0 不依赖语义匹配？

**问题**: 语义模型加载慢（~2s），推理慢（~100ms/句），可能影响性能。

**方案**: 
- P0 只用 exact/phrase 匹配（正则，<1ms）
- P1 可选启用 semantic 匹配（默认关闭）
- P2 评估性能后决定是否默认开启

**收益**: 快速交付，降低风险。

---

### 为什么每周校准而不是每天？

**问题**: 每天校准成本高，变化小，容易过拟合。

**方案**: 
- 每周五下午固定时间
- 抽取 10% 低置信样本
- 人工标注 + 应用变更

**收益**: 平衡成本和效果，避免频繁变动。

---

## 🎉 预期成果

### 3 周后，我们将拥有：

1. **一个会自我进化的语义库**
   - 每周自动挖掘新词
   - 每周人工校准迭代
   - 版本可追溯、可回滚

2. **一套可量化的质量体系**
   - Coverage/Precision/F1 可视化
   - 每周对比，趋势明确
   - 问题可定位、可优化

3. **一个可解释的评分系统**
   - exact/phrase/semantic 三种策略
   - 权重可调、规则透明
   - 证据可溯源、可审计

4. **一个标准化的报告流程**
   - 固定模板、结构稳定
   - 证据充分、可信度高
   - 生成快速、成本低

---

**下一步**: 阅读快速启动指南，立即开始 P0 任务！

📖 `.specify/specs/011-quick-start-guide.md`
