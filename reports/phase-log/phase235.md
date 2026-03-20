# Phase 235 — Stopword 补漏与 ad-hoc topic 放宽修复（2026-03-06）

## 背景

`phase234` 已经把报告主链路救活，但实际跑 ad-hoc topic 时，仍有 3 个残留问题：
- 品牌提取 stopword 漏词，导致 `Thank`、`Ultra`、`ChatGPT`、国家名这类杂音继续被当成品牌。
- `generate_t1_market_report.py` 里的 `NOISE_TERMS` 太小，品牌痛点区块还会混进泛词和 AI 工具名。
- V1→V2 fallback 对 ad-hoc topic 继续做二次 topic 过滤，把本来已经抽出来的 `solutions`、`pains`、`opportunities` 又洗掉一轮，结果偏少。

## 本次修复

### 1. 补齐品牌 stopword

文件：`backend/app/services/analysis/signal_extraction.py`

- 在 `_extract_competitors()` 的内联 stopword set 中补入规格要求的缺失词。
- 新增了 3 组说明注释：
  - `Adverbs / AI tools / country names`
  - `AI tool names`
  - `Country / continent / region`
- 覆盖了副词、AI 工具名、国家/方位词，以及 `everything` / `nothing` / `today` 这类高频假品牌。

### 2. 扩大报告脚本的噪音词集合

文件：`backend/scripts/report/generate_t1_market_report.py`

- 扩展 `NOISE_TERMS`，把规格里要求的泛词、AI 工具名、国家名补进去。
- 目的很直接：减少 `brand_pain` 里把噪音词误当品牌的概率。

### 3. 放宽 ad-hoc topic 的 fallback 二次过滤

文件：`backend/scripts/report/generate_t1_market_report.py`

- `pains` / `solutions` / `opportunities` 三处 fallback 都改成：
  - 只有 `active_profile is not None and _topic_filter_kw` 时，才继续做 topic filter。
  - 如果 `active_profile is None`，就跳过二次过滤，直接保留原始信号。
- 同时把打印日志拆开：
  - profile topic 继续打印 `raw → filtered`
  - ad-hoc topic 打印 `kept as-is`

## 发现与判断（统一反馈）

1. 发现了什么？
   发现 stopword 和 noise term 两层过滤都存在漏词；另外 ad-hoc topic 被错误套用了 profile topic 的严格过滤。

2. 是否需要修复？
   需要。这 3 个点都会直接影响报告可读性和信号数量，属于结果层面的真实问题。

3. 精确修复方法？
   已按规格最小改动修复：补词表，外加给 3 处 fallback 过滤补 `active_profile is not None` 守门条件。

4. 下一步系统性的计划是什么？
   后续如果继续出现“假品牌”问题，建议把 stopword/noise term 收口成统一词表来源，避免两个文件各自漂移。

5. 这次执行的价值是什么？达到了什么目的？
   这次修复把 ad-hoc topic 的信号保留率拉回正常，也继续压低了品牌杂音，目的是让 T1 报告更像人能看的结果，而不是被副词和泛词污染。

## 执行说明

- 本次按要求只修改代码与 phase-log。
- 未运行测试，未做端到端验证。

---

## 追加修复：Phase 235C Prompt 深度优化（2026-03-06）

### 背景

在报告已经能稳定生成 7 个模块后，新的问题不在“有没有内容”，而在“内容是不是在替跨境卖家做决策”。这次规格聚焦 1 个文件里的 prompt 收口，要把读者身份、判断口径、机会卡写法全部往“跨境选品”上拧紧。

### 本次修复

#### 1. 给系统提示补上明确读者画像

文件：`backend/scripts/report/generate_t1_market_report.py`

- 在 `REPORT_SYSTEM_PROMPT_V2` 开头新增 4 行读者定义。
- 明确这份报告是写给“跨境电商卖家 / 选品决策者”的，不是给终端消费者看的。
- 同时把建议目标收口到 3 件事：值不值得做、怎么切入、怎么差异化。

#### 2. 重写系统提示末尾的写作风格

文件：`backend/scripts/report/generate_t1_market_report.py`

- 用新版本替换旧的“写作风格”段落。
- 新文案更强调：
  - 敢下判断，不要两头都说；
  - 看到数据先问“对选品有什么用”；
  - 每一句都要能帮卖家做下一步动作；
  - 加入自查规则，避免把 JSON 字段名、系统变量名、内部标记直接吐给用户。

#### 3. 在禁令区补两条新红线

文件：`backend/scripts/report/generate_t1_market_report.py`

- 新增 F：禁止暴露系统标记和内部变量值。
- 新增 G：社区推荐必须和主题强相关，不能因为偶尔提到关键词就硬塞进去。

#### 4. 强制 Part1 给出四档选品判断

文件：`backend/scripts/report/generate_t1_market_report.py`

- 在模块 2.1“需求趋势”末尾追加强制要求。
- 现在趋势分析最后必须明确给出四档之一：
  - `强烈建议关注 / 可以试水 / 先观望 / 不建议`
- 并要求用 2–3 句话把原因说透。

#### 5. 把 P/S Ratio 的落点改成跨境卖家视角

文件：`backend/scripts/report/generate_t1_market_report.py`

- 替换模块 2.3 里原来偏泛化的两条说明。
- 新写法直接回答：
  - 对跨境电商卖家，选品和定位要注意什么；
  - 对新入场卖家，先发优势还剩多少、适合什么水平的人进。

#### 6. 给痛点卡补“选品启示”

文件：`backend/scripts/report/generate_t1_market_report.py`

- 在模块 5 的“连锁反应”后新增“选品启示”维度。
- 目的很直接：不让痛点卡停在吐槽层，要把它翻成可执行的产品判断。

#### 7. 重写模块 7 机会卡

文件：`backend/scripts/report/generate_t1_market_report.py`

- 把旧的“信息透明 / 预测型”“整合 / 降复杂度型”机会卡，改成：
  - `功能差异化机会`
  - `定位差异化机会`
- 现在每张卡都必须回答 3 个核心问题：
  - 谁痛
  - 为什么还没被满足
  - 卖家怎么切入
- 同时明确只聚焦“可卖的实体产品或功能差异化”，不再往 app / 平台 / SaaS 上飘。

### 发现与判断（统一反馈）

1. 发现了什么？
   发现现有 prompt 虽然能产出完整结构，但读者定位还偏泛，很多地方还没有强制落到“跨境选品决策”。

2. 是否需要修复？
   需要。这个问题不修，报告会继续停留在“能看”，但不够“能拿来做生意判断”。

3. 精确修复方法？
   已按规格 7 点直接改 prompt：补读者身份、补禁令、重写写作风格、收紧 Part1/Part2 的输出要求。

4. 下一步系统性的计划是什么？
   下一步应该用你后续重新跑的 pipeline 结果看 3 件事：
   - 趋势卡是否真的稳定输出四档判断；
   - 社区推荐是否明显更聚焦；
   - 机会卡是否已经从“空泛建议”变成“可上架的实体产品方向”。

5. 这次执行的价值是什么？达到了什么目的？
   这次修复的价值，是把报告从“泛分析”进一步压到“跨境卖家能直接拿来选品”的口径上，让输出更有判断、更有抓手、更能指导动作。

### 执行说明

- 本次只修改 `backend/scripts/report/generate_t1_market_report.py` 的 prompt 文案，以及 phase-log 记录。
- 未运行测试，未做端到端验证。
