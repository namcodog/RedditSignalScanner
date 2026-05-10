# Phase 239 — DB 底朝天深度审计 + 全链路修复（2026-03-11）

## 背景

上一轮（Phase 238）把品牌发现做了配置化收口。但 wireless earbuds 报告跑出来后发现 `unique_authors=0`、tier 两次跑不一致，需要彻底查清 DB 层到底发生了什么。

---

## 发现了什么

### Round 1：5 层审计（SQL + Serena + Sequential Thinking）

| 层 | 发现 | 严重性 |
|----|------|:------:|
| 数据量 | 507K 帖子、2.3M 评论、842K 作者 | ✅ 正常 |
| Author 覆盖 | 帖子 100%、评论 100% | ✅ 正常 |
| 去重率 | 帖子 0.1%、评论 0% | ✅ 正常 |
| **评论向量化** | **27%（170 万条缺失）** | 🔴 P1 |
| **评论 LLM 标注** | **29%** | 🟡 P1 |
| 帖子打分 | 136%（含已删帖残留） | ⚠️ 轻微 |

**核心发现：DB 本身是健康的，author 覆盖率 100%。**

### Round 1 根因追踪：unique_authors=0

用 Serena MCP 追踪完整代码链路：

```
_fetch_sample_comments → QuoteExtractor → quotes.append({...}) → brand backfill
```

**根因（P0）**：`quotes.append()` 只保留了 300 字 `text` snippet，**丢掉了原始 `body`**。品牌回填 `c.get("body")` 拿到 None → 搜不到品牌名 → authors=0。

**之前说的"V1 数据 author 缺失"是错误诊断。**

### Round 2：4 方向审计（Serena + Sequential Thinking 6 步推理）

| # | 问题 | 根因 | 优先级 |
|---|------|------|:------:|
| R2-1 | **Tier 两次跑不一致** | 43% 评论 score=1（100 万条），SQL ORDER BY 随机选 | P2 |
| R2-2 | **Pain 计数偏低** | `_count_pain_mentions_in_comments` 先读 text (snippet) 而非 body (全文) | P2 |
| R2-3 | **tier 历史数据丢失** | `facts_quality_audit` 表缺 tier 列（schema drift） | P3 |
| R2-4 | **评论向量化 27%** | Embedding batch 未持续调度（运维问题非代码 bug） | P1 缓 |

---

## 是否需要修复

全部需要修复。R2-4 产品经理要求缓一轮。

---

## 精确修复方法

### P0：quotes 加 body 字段（根治 unique_authors=0）

文件：`generate_t1_market_report.py` L2285

```python
# Before: quotes dict 没有 body key
# After:
"body": item.get("body"),  # 保留原始评论全文，供品牌 unique_authors 回填使用
```

### R2-1：SQL Tie-Breaking（根治 tier 不稳定）

4 处 SQL 末尾加 tie-breaker：

- `_fetch_sample_comments` 主查询：`ORDER BY c.score DESC NULLS LAST, c.id`
- `_fetch_sample_comments` fallback：同上
- `_fetch_top_posts` 主查询：`ORDER BY ... ps.value_score DESC, p.score DESC, p.id`
- `_fetch_top_posts` fallback：`ORDER BY ... p.score DESC, p.id`

### R2-2：Pain text 优先级（优先全文）

文件：`generate_t1_market_report.py` L1830

```python
# Before:
text = str(c.get("text") or c.get("body") or c.get("text_snippet") or "").lower()
# After:
text = str(c.get("body") or c.get("text") or c.get("text_snippet") or "").lower()
```

### R2-3：Schema Drift（tier 列落库）

- `facts_quality_audit` 表 `ALTER TABLE ADD COLUMN tier VARCHAR(32)`
- INSERT SQL 加 `tier` 字段
- 代码写入 `quality["tier"] = quality_result.tier`

### 品牌噪音词扩充

`_BRAND_NOISE` 集合新增 48 个词：

- 英语常用词："does", "sure", "quick", "unless", "christmas"
- 非品牌术语："bluetooth", "wireless", "specs", "master"
- 自行车零件（干扰音频品类）："roubaix", "altus", "ultegra", "campy"
- 泛化 filler 词："really", "maybe", "still", "every", "never", "always" 等

---

## 改动文件

### 代码

- `backend/scripts/report/generate_t1_market_report.py`（P0 + R2-1 + R2-2 + 品牌噪音）

### Schema

- `facts_quality_audit` 表 tier 列（R2-3，Codex 执行 + 用户手动 DDL）

---

## 验证结果

### AST

✅ 通过

### 回归测试

```
20 passed, 1 warning in 2.88s
```

### Schema 验证

```
tier column exists: True
```

### 端到端报告验证（wireless earbuds）

| 指标 | 修复前 (Phase 238) | P0 Fix Only | P0 + R2 全修 |
|------|:-----------:|:-----------:|:-----------:|
| **Tier** | A_full | B_trimmed | **A_full** ✅ |
| **Good brands** | 3 | 0 | **3** ✅ |
| **Flags** | — | brand_pain_low | **无** ✅ |
| **报告大小** | 9.6KB | 5.7KB | **11.5KB** |

---

## 下一步系统性的计划

1. **R2-4 评论向量化 27% → 70%+**：排期运维 batch 扩大调度
2. **facts_quality_audit 补 ORM model**：裸 SQL → SQLAlchemy Model，防 schema drift 再发
3. **跨品类通用性验证**：5 个品类跑两次，验证 tier 是否稳定（R2-1 修复效果）

---

## 这次执行的价值

### 1. 纠正了一个持续两轮的错误诊断

"unique_authors=0 是因为 V1 数据 author 缺失"❌ → 实际 DB author 100% 覆盖，根因在 quotes dict 丢了 body 字段。

### 2. 挖出了 tier 不稳定的隐蔽根因

43% 评论 score=1 导致 SQL ORDER BY 随机选 → 每次运行品牌/pain 结果不同。这类统计分布引发的非确定性，肉眼看代码完全正确，只有查数据分布才能发现。

### 3. 建立了 Serena + Sequential Thinking 审计方法论

不能只看数据层表象（覆盖率正常就放过），必须追踪完整代码链路：DB 查询 → 中间 dict 结构 → 下游消费方式。数据"有"不等于算法"用得到"。
