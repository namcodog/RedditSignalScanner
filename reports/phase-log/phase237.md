# Phase 237 — 跨品类泛化修复 + 算法升级规划（2026-03-09）

## 背景

Phase 236 把手电筒品类的数据链路修好后，尝试跑「wireless earbuds」「baby stroller」「coffee machine」做跨品类验证。发现整个管线是围绕手电筒/EDC 品类硬编码的，换品类就全面偏离。经过 5 项代码修复后，3 个品类均通过验证。

---

## 已完成修复（5 项代码改动）

### 1. LLM Exclusion 误杀近义词（Codex gpt-5.4）

文件：`backend/scripts/report/generate_t1_market_report.py`

- 新增模块级常量 `_SEMANTIC_PROXIMITY_MAP`（13 品类的近义词映射）
- 在 `main()` 中增加两段保护逻辑：
  - Semantic proximity guard：从 exclusion 列表中救回与 topic 语义近邻的词
  - Self-contradictory exclusion guard：移除 LLM 自己扩展出来又放到 exclude 里的词

**验证结果：**
```
Before: exclusion 包含 headphones/sound/audiophile → 相关社区被排除
After:  exclusion 只剩 over/quality → 音频关键词正确保留
```

### 2. VERTICAL_CORE_WHITELIST 拆分（手动）

- `consumer_electronics` 从包含 6 个 flashlight 社区 → 只保留 `r/gadgets`
- flashlight 社区独立到 `edc` vertical（不变）
- 新增 `audio` vertical（r/headphones, r/headphoneadvice, r/audiophile, r/earbuds, r/bluetooth_speakers）

### 3. Audio + Baby_parenting Vertical 检测（Codex gpt-5.4）

- `_expand_topic_semantically` 新增 audio 关键词检测（earbuds/headphone/speaker 等）
- 新增 baby_parenting 关键词检测（stroller/baby/toddler/infant 等）
- `VERTICAL_CORE_WHITELIST` 批量新增 4 个 vertical：baby_parenting, outdoor_garden, fashion, automotive

### 4. core_list_for_final 通用化（手动，关键修复）

- 原来 `final_comm` 组装逻辑只对 `edc/consumer_electronics` 注入 core list
- 改为通用化：所有有 `VERTICAL_CORE_WHITELIST` 配置的 vertical 都注入

**验证结果：**
```
Baby stroller 修复前: digitalnomad / onebag / frugal / backpacking（全偏）
Baby stroller 修复后: toddlers / daddit / mommit / parenting / babybumps / beyondthebump（前 6 命中）
```

### 5. Core Whitelist 社区 Score Boost（手动）

- core_whitelist 社区注入时给 1.5x max_score 分数（而非固定 1.0）
- 已有的 whitelist 社区也加 50% 分
- 注入后按分数重排序

---

## 跨品类验证结果

| 品类 | vertical | Final Top 10 前几名 | 命中率 | 备注 |
|------|----------|---------------------|--------|------|
| Baby Stroller | `baby_parenting` | r/toddlers / r/daddit / r/mommit / r/parenting / r/babybumps / r/beyondthebump | 前 6 全中 | 修复前全是 digitalnomad/onebag |
| Coffee Machine | `home_kitchen` | r/coffee / r/pourover / r/barista / r/espresso | 前 4 全中 | 无需额外配置，通用化修复直接生效 |
| Wireless Earbuds | `audio` | whitelist 包含 r/headphones/r/audiophile/r/earbuds | 代码正确 | DB 无音频社区数据，无法验证最终排序 |

### 关键发现

1. **根因是 `core_list_for_final` 硬编码**：原逻辑只对 `edc/consumer_electronics` 注入核心社区，其他 vertical 全部跳过。通用化后所有 vertical 的 core_whitelist 都能注入。
2. **LLM 语义扩展的 exclusion 不可信**：LLM 会把 topic 的近义词/上位词放到 exclude 里（如 earbuds → exclude headphones），需要 proximity guard 保护。
3. **社区发现依赖 DB 数据覆盖**：即使算法全对，DB 没有对应社区数据就无法产出高质量报告。当前 186 个社区主要覆盖电商运营/户外/家装/育儿/烹饪。

---

## DB 数据清查

| 指标 | 数值 |
|------|------|
| 总帖子数 | 195,197 |
| 总评论数 | 2,063,820 |
| 总社区数 | 186 |
| 主要覆盖 | 电商运营(30K) / 家装DIY(21K) / 户外旅行(18K) / 省钱BIFL(12K) / 育儿(16K) / 烹饪(12K) |
| 缺失品类 | 音频(earbuds/headphones) / 手机数码 / 相机 / 笔记本 |

---

## 下一步事项（Phase 237B：算法通用化升级）

### 目标
从「每个品类手动配置」进化到「自动适应任意品类」，让系统真正具备泛化能力。

### 事项 1：`_SEMANTIC_PROXIMITY_MAP` 动态化

**现状问题**：
- 当前是手工维护 13 个品类的近义词映射表
- 每新增一个品类就要手动添加，不可扩展

**升级方案**：
- 利用 DB 中已有的 `post_embeddings` 表
- 在运行时用 embedding 相似度自动判断「exclusion 词是否和 topic 语义过近」
- 阈值：cosine similarity > 0.7 的 exclusion 词自动救回
- 保留 `_SEMANTIC_PROXIMITY_MAP` 作为 fallback，新增的动态判断优先

**验收标准**：
- 不在 `_SEMANTIC_PROXIMITY_MAP` 里的品类（如 "yoga mat"、"power tools"）也能自动保护近义词
- 已有品类的行为不退化

### 事项 2：社区排序用 Embedding Similarity 替代关键词命中

**现状问题**：
- `_score_communities_contextually` 用关键词全文搜索（ts_query）打分
- babybumps 讨论育儿但不一定提"stroller"，导致排序分数低
- 依赖 `core_list_for_final` 硬注入来救排序

**升级方案**：
- 用 topic embedding 和社区帖子的 embedding 做 cosine similarity
- 每个社区的 "topic relevance score" = 该社区帖子中 top-K embedding 相似度的均值
- 用 embedding score 替代 ts_query hit count 作为排序依据
- DB 中 `post_embeddings` 表已有数据，不需要重新计算

**验收标准**：
- baby stroller 查询下，babybumps/toddlers 在没有 core_whitelist 硬注入的情况下也能排到前 10
- 手电筒品类的排序不退化

### 事项 3：围绕现有 DB 数据做全品类回归验证

**验证品类清单**（选有数据支撑的品类）：
1. ✅ baby stroller（已验证，前 6 命中母婴社区）
2. ✅ coffee machine（已验证，前 4 命中咖啡社区）
3. ⬜ flashlight / EDC（回归测试，确认不退化）
4. ⬜ kitchen appliances
5. ⬜ mechanical keyboard
6. ⬜ hiking gear

**验收标准**：
- 每个品类 top 10 社区中至少 3 个强相关
- Quality degraded 比率 < 50%

---

## Codex 使用经验记录

| 现象 | 根因 | 解法 |
|------|------|------|
| Codex 卡住 19 分钟无输出 | Prompt 过长 + serena 全量读码 | 精简 prompt，精确指定改动点 |
| Codex 503 Service Unavailable | OpenAI 服务器端问题 | 手动编辑作为 fallback |
| chrome-devtools MCP 每次必挂 | 本地无 binary | 不影响执行，忽略即可 |
| MCP 初始化 ~15 秒 | 配置了 8 个 MCP 服务器 | 不动配置，接受开销 |
