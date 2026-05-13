# Phase 382 - 第三轮大包推进：LLMLabeler 门面 / runtime / support 成组封板

## 1. 发现了什么？

这次收的是语义 / 标签模块里最后一个还比较重的核心服务：

- `backend/app/services/llm/labeling.py`

之前这个文件还是自己背着两大坨逻辑：

- prompt / schema / JSON 解析 helper
- post / comment 单条与 batch 的完整标注编排

大白话说：

- `LLMLabeler` 既像门面，又像真正干活的 runtime
- support、runtime、门面三层还没彻底分开

这不符合第三轮现在的封板目标：

- 门面继续变薄
- 真正干重活的逻辑回到 runtime / support
- 单一真相源继续做硬

## 2. 是否需要修复？

需要，而且这次已经整包修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 收薄 `labeling.py`

修改：

- `backend/app/services/llm/labeling.py`

现在这个文件主要只负责：

- 保留 `LLMLabeler` 对外类接口
- 保留旧的 builder / helper 名称作为薄兼容层
- 把真正的 prompt / parse / orchestration 委托给 support / runtime

直观结果：

- `backend/app/services/llm/labeling.py`：`366 -> 195`

### 3.2 正式启用 support / runtime 真相源

接入：

- `backend/app/services/llm/labeling_support.py`
- `backend/app/services/llm/labeling_runtime.py`

现在这两层分别负责：

- `labeling_support.py`
  - schema
  - prompt 构造
  - JSON 安全解析
  - batch items 提取

- `labeling_runtime.py`
  - `run_label_post(...)`
  - `run_label_posts_batch(...)`
  - `run_label_comment(...)`
  - `run_label_comments_batch(...)`

也就是说：

- `LLMLabeler` 现在更像一个真正的门面类
- 真正干活的链已经回到 runtime / support

### 3.3 补测试锁边界

新增：

- `backend/tests/services/llm/test_labeling_runtime.py`

覆盖了：

- post prompt 截断和 top comments 限制
- batch items 解析过滤
- post batch runtime 正常解析
- comment batch runtime 在不可解析响应下稳定告警并返回空结果

同时继续跑通：

- `backend/tests/services/labeling/test_llm_labeler.py`
- `backend/tests/services/llm/test_post_label_workflow.py`
- `backend/tests/services/llm/test_comment_label_workflow.py`
- `backend/tests/tasks/test_llm_label_task.py`

## 4. 验证结果

### 4.1 成组定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/labeling/test_llm_labeler.py \
  tests/services/llm/test_labeling_runtime.py \
  tests/services/llm/test_post_label_workflow.py \
  tests/services/llm/test_comment_label_workflow.py \
  tests/tasks/test_llm_label_task.py -q
```

结果：

- `19 passed`

### 4.2 更宽的语义 / 标签回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm \
  tests/services/labeling/test_llm_labeler.py \
  tests/tasks/test_llm_label_task.py -q
```

结果：

- `59 passed`

### 4.3 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.4 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/labeling.py \
  backend/app/services/llm/labeling_support.py \
  backend/app/services/llm/labeling_runtime.py \
  backend/tests/services/llm/test_labeling_runtime.py
```

结果：

- 通过

## 5. 下一步系统性的计划是什么？

第三轮继续按“大包封板”推进，不再碎跑。

现在剩下最值钱的包已经很少了：

1. `数据采集模块` 最后一小包清尾
2. 第三轮总复盘
   - 正式判断当前系统是否已经稳定站上 `95+`

## 6. 这次执行的价值是什么？达到了什么目的？

这次的价值很直接：

- `LLMLabeler` 不再既当门面、又亲手跑完整标注链
- prompt / parse / runtime 三层边界现在清楚了
- 后面再改：
  - schema
  - prompt
  - batch 解析
  - 单条 / 批量打标
  不容易再把门面类一起拖重

一句大白话总结：

- 这一步不是修一个 helper，而是把语义 / 标签模块里 `LLMLabeler` 这一整包真正封板了。
