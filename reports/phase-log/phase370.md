# Phase 370 - 标签导出链成组收口（大脚本回服务层）

## 1. 发现了什么？

这次第三轮按“大包推进”打的是标签模块里还很重的一条离线链：

- `backend/scripts/report/export_llm_label_candidates.py`

这支脚本之前有 `624` 行，而且自己背着整套导出逻辑：

- post 增量导出
- post 全量导出
- comment 增量导出
- comment 全量导出
- historical activation 导出
- JSONL 落盘
- noise 配比
- activation batch 拆分

大白话说：

- 这不是“脚本调服务”
- 而是“脚本自己就是半个业务模块”

这会带来两个问题：

- 导出合同容易和在线链再漂一次
- 后面要改导出口径时，很容易又回到“大脚本里手改一坨”的状态

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增统一导出服务层

新增：

- `backend/app/services/llm/label_export_service.py`

把整套离线导出链收回服务层，正式承接：

- `_export_posts(...)`
- `_export_posts_all(...)`
- `_export_comments(...)`
- `_export_comments_all(...)`
- `_build_comment_activation_export(...)`
- `_export_comment_activation(...)`
- `_write_jsonl(...)`
- `run_label_export(...)`

同时把默认参数也统一收进服务层：

- `DEFAULT_NOISE_RATIO`
- `DEFAULT_NOISE_MIN_SCORE`
- `DEFAULT_NOISE_MIN_COMMENTS`
- `DEFAULT_ACTIVATION_TARGET`
- `DEFAULT_ACTIVATION_BASE_QUOTA`
- `DEFAULT_ACTIVATION_FIRST_BATCH`
- `DEFAULT_ACTIVATION_BATCH_SIZE`

### 3.2 把导出脚本收成薄 CLI

更新：

- `backend/scripts/report/export_llm_label_candidates.py`

这支脚本现在只剩两件事：

1. 解析命令行参数
2. 组装 `LabelExportWorkflowInput` 后调 `run_label_export(...)`

很直观的结果：

- `backend/scripts/report/export_llm_label_candidates.py`
  - 从 `624` 行降到 `82` 行

也就是说：

- 脚本不再自己背业务逻辑
- 现在它终于更像 CLI 壳了

### 3.3 测试一起拉回服务层真相源

更新：

- `backend/tests/scripts/test_export_llm_label_candidates.py`

这次测试不再直接咬脚本实现，而是改成直接测：

- `app.services.llm.label_export_service`

大白话说：

- 后面就算 CLI 再继续变薄，测试也不会把业务逻辑拽回脚本里

## 4. 测试与验证

### 成组定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/scripts/test_export_llm_label_candidates.py \
  tests/services/llm/test_post_label_planner.py \
  tests/services/llm/test_comment_label_planner.py \
  tests/services/llm/test_llm_label_task_runtime.py -q
```

结果：

- `11 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/label_export_service.py \
  backend/scripts/report/export_llm_label_candidates.py \
  backend/tests/scripts/test_export_llm_label_candidates.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 下一步系统性的计划是什么？

第三轮继续按“大包封板”推进，不再回到碎跑。

接下来优先顺序还是：

1. `数据采集模块` 最后一包
2. `语义 / 标签模块` 最后一包（剩余 sync / import-export 接缝）
3. 第三轮总复盘

当前完成度判断更新为：

- 第三轮完成度：约 `82%-83%`
- 整个系统总完成度：约 `91%-92%`

## 6. 这次执行的价值是什么？达到了什么目的？

这一步很值钱，因为：

- 标签导出链现在开始有自己的正式真相源了
- 大脚本不再自己背业务逻辑
- 后面再改导出口径、activation batch、noise 策略，不容易再把 CLI 一起拖重

一句大白话：

- 这次不是又改了几个 helper，而是把“标签怎么导出来”这一整包从大脚本里真正搬回服务层了。以后这条离线链会稳很多。 
