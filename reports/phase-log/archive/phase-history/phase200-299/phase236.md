# Phase 236 — 数据层全链路修复（2026-03-07）

## 背景

Phase 234-235 把报告主链路救活、prompt 口径拧紧后，进入数据层全链路审计。发现 4 个根因级不稳定问题：

1. V1 SignalExtractor 逐句提取 pain，`frequency` 永远=1 → bridge 写 `mentions=1` → Quality Gate 放水
2. `pain_min_unique_authors` 默认阈值=2，V1 无真实 author 数据
3. LLM `temperature=0.25`，同一份 facts 两次跑不同结果
4. prompt 里残留 xx 党标签（吐槽党/避坑党等），LLM 还会自己生成

## 本次修复

### 1. V1→V2 Bridge Mentions 真实值重算（核心改动）

文件：`backend/scripts/report/generate_t1_market_report.py`

- 新增模块级函数 `_count_pain_mentions_in_comments(pain_description, sample_comments, min_keyword_overlap=2)`
- 从 pain.description 提取内容关键词（≥4字符，去停用词），回 sample_comments_db 做 keyword overlap 匹配
- 匹配到的评论数 = 真实 mentions，去重 author = 真实 unique_authors
- 替换原来的 `max(frequency, 1)` 假数据

**验证结果：**
```
Before: 全 15 个 pain mentions=1
After:  mentions=67, 41, 13, 9, 3, 1, 1, 1, 1, 1...
        7/15 个 mentions≥3 通过 Quality Gate
```

### 2. Quality Gate 阈值微调

文件：`backend/scripts/report/generate_t1_market_report.py`

- `pain_min_unique_authors` 默认值从 2 降到 1
- 因为 V1 评论的 author 信息不一定完整，降低门槛避免误杀

### 3. LLM Temperature

文件：`backend/scripts/report/generate_t1_market_report.py`

- `temperature` 从 0.25 降到 0.05
- 同一份 facts 跑两遍核心结论基本一致

### 4. xx 党标签三层防御

文件：`backend/scripts/report/generate_t1_market_report.py`

**层 1 — Prompt 文本清理（5 处）：**
- Part1 L1498/1499/1500/1503：xx 党描述 → 大白话场景化描述
- Scouting prompt L1741：xx 党 → 自然描述

**层 2 — System Prompt 硬禁令加强：**
- 精确列出 10 个禁止词（吐槽党/避坑党/找货党/工具党/进阶党/学习党/耐用党/预算党/性价比党/颜值党）
- 增加"自查规则"：要求 LLM 写完后检查全文

**层 3 — 代码后处理兜底（关键）：**
- 10 个词的精确替换词表
- 通配正则 `[\u4e00-\u9fff\w]{1,5}党 → \1的人`
- 通配正则 `[\u4e00-\u9fff\w]{1,5}型用户 → \1类型的用户`

**验证结果：** `grep -nc '党' t1-auto.md` = 0

## 最终报告质量

| 指标 | Before | After |
|------|--------|-------|
| 行数 | 22 行 | 133 行 |
| xx 党标签 | 3+ 处 | 0 |
| mentions 真实性 | 全部=1（假） | 1-67（真） |
| Quality Gate | 放水 | 7/15 通过≥3 |
| temperature | 0.25 | 0.05 |
| JSON 化描述 | 有 | 0 |

## 教训

1. **假指标陷阱**：看到一个指标永远=常数（尤其是 1），先怀疑是架构限制导致的精度不足，不是 bug。
2. **LLM 禁令双层保障**：prompt 禁令对 Grok 不足以 100% 控制输出，必须加代码后处理兜底。
3. **近似重算优于等待完美方案**：不等 V2 聚合引擎上线，用已有评论数据做关键词回查就够用。

## 下一步

1. 跨品类通用性验证（wireless earbuds / baby stroller）
2. V2 compute_pain_clusters_v2 激活评估
3. 数据量扩充策略（抓取覆盖面 vs 过滤宽松度）

## 执行说明

- Codex gpt-5.4 Medium 执行核心 9 处代码修改
- 手动补 system prompt 硬禁令和代码后处理兜底
- 3 轮 pipeline 完整跑通验证
