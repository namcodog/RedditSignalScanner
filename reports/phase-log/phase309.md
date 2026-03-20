# Phase 309 - 第三轮语义/标签模块下一刀：标签规范化/评分合同收口

## 背景

第三轮继续打语义/标签模块这块“价值放大器”。

上一刀已经把“哪些评论值得进标签链”收成了独立 planner：

- 在线增量评论：`IncrementalCommentLabelPlan`
- 历史激活评论：`HistoricalCommentActivationPlan`

但继续往下看，还有一根更隐蔽、也更容易继续漂的线没有拆干净：

- 在线 `LLMLabeler`
- 离线 `import_client_llm_labels.py`

虽然现在都已经共用了持久化层，但“标签结果怎么规范化、怎么算业务分”这件事，离线导入脚本还在反向依赖：

- `app.services.llm.labeling` 里的私有 helper

也就是：

- 在线标注器内部实现细节
- 还在泄漏给离线导入器

这不符合第三轮“继续降耦合、继续把单一真相源做硬”的目标。

---

## 这一步发现了什么？

### 1. 剩余最高耦合点已经很明确

`backend/scripts/import/import_client_llm_labels.py` 之前直接 import：

- `_normalize_post_analysis`
- `_normalize_comment_analysis`
- `_score_post`
- `_score_comment`

这些都来自：

- `backend/app/services/llm/labeling.py`

问题很直接：

- `labeling.py` 是在线标注器
- 离线导入脚本不应该反向咬住它的私有 helper

大白话：

- 现在“标签怎么规范化、怎么算 value/opportunity/business_pool”
- 还不是正式公共合同
- 只是 `labeling.py` 里一套“顺手写的内部实现”

### 2. 这会继续制造两种漂移风险

#### 风险 A：在线/离线边界继续缠死

后面如果改标签结构、默认值、评分口径：

- 在线链会改
- 离线导入也得一起跟着盯 `labeling.py`

等于：

- “公共规则”还躲在“在线标注器私有实现”里

#### 风险 B：AI 和人都容易再沿旧路径漂回去

因为脚本现在的姿势是在暗示：

- “去 `labeling.py` 拿私有函数也没问题”

这会让后面继续扩脚本、补标签、做回填时，很容易又沿着旧世界长回去。

---

## 是否需要修复？

需要，而且已经完成。

这次没有：

- 改数据库 schema
- 新增 migration
- 改 LLM prompt
- 改标签业务口径

这次改的是：

- 标签规范化/评分的**公共合同层**
- 在线标注器与离线导入器的**依赖边界**
- 对应测试门禁

---

## 精确修复方法

### 1. 新增共享标签合同层

新增文件：

- `backend/app/services/llm/label_contract.py`

正式抽出这几个公共真相源：

- `LLMScoreResult`
- `normalize_post_analysis(...)`
- `normalize_comment_analysis(...)`
- `score_post_analysis(...)`
- `score_comment_analysis(...)`

这意味着：

- “标签怎么规范化”
- “标签怎么转成 value/opportunity/business_pool”

现在开始有独立、正式、可复用的合同层。

### 2. 在线标注器改成依赖公共合同层

调整：

- `backend/app/services/llm/labeling.py`

这次不是继续在 `labeling.py` 里维护私有 `_normalize/_score` 世界，而是：

- 直接依赖 `label_contract.py`

效果：

- `LLMLabeler` 继续只负责：
  - 调模型
  - 拿返回
  - 走公共规范化/评分合同

大白话：

- 在线标注器不再自己私藏“评分规则”

### 3. 离线导入脚本也改成依赖同一套公共合同

调整：

- `backend/scripts/import/import_client_llm_labels.py`

现在它不再反向 import `labeling.py` 的私有 helper，
而是直接走：

- `normalize_post_analysis(...)`
- `normalize_comment_analysis(...)`
- `score_post_analysis(...)`
- `score_comment_analysis(...)`

大白话：

- 离线导入器不再“借用在线标注器的内部零件”
- 而是和在线链站在同一条正式合同线上

### 4. 用测试把这套合同锁住

新增测试：

- `backend/tests/services/llm/test_label_contract.py`

覆盖：

- 默认值规范化
- post 高价值进入 `core`
- comment `offtopic` 落到 `noise`

调整脚本测试：

- `backend/tests/scripts/test_import_client_llm_labels.py`

现在明确验证：

- 离线导入脚本会调用公共 `normalize_comment_analysis`
- 会调用公共 `score_comment_analysis`
- 之后再走共享持久化层

也就是：

- 不是只看“最后写进去了没”
- 还锁了“中间是不是走了公共合同层”

---

## 结果

### 结构结果

- 在线标注器的私有 helper，不再是离线导入器的依赖源
- 标签规范化/评分开始有独立、正式的公共合同层
- 语义/标签模块里“同一件事两只手各写一遍”的风险继续下降

### 工程结果

这一步把语义/标签模块继续往下面这条准则推进了一层：

- 职责更清楚
- 统一接口协同
- 彼此少牵连
- 链路更顺、更可控

大白话：

- 现在“标签怎么解释、怎么算分”
- 不再藏在在线标注器肚子里
- 而是成了在线和离线都能共用的一块正式齿轮

---

## 验证

### 1. 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_label_contract.py \
  tests/scripts/test_import_client_llm_labels.py \
  tests/tasks/test_llm_label_task.py -q
```

结果：

- `9 passed`

### 2. 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/label_contract.py \
  backend/app/services/llm/labeling.py \
  backend/scripts/import/import_client_llm_labels.py \
  backend/tests/services/llm/test_label_contract.py \
  backend/tests/scripts/test_import_client_llm_labels.py
```

结果：

- 通过

### 3. 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方，不是“多了一个公共文件”，而是：

- 把语义/标签模块里“标签规范化 + 评分”这块真正钉成了公共真相源
- 在线标注器和离线导入器不再通过私有 helper 黏在一起
- 后面继续改标签结构、默认值、评分口径，不容易两边一起漂

一句大白话收口：

- 这刀把语义/标签模块里最容易继续反向耦合的一根线先剪开了，第三轮节奏还是稳的，可以继续往 95 分以上推进。
