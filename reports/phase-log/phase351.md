# Phase 351 - 第三轮继续推进：Post Label Planner 公共化

## 本轮目标

把 `post` 在线标签链里还留在 task 私有函数里的候选规划和评论取样逻辑，收成正式公共 planner。

这轮要解决的不是“标签准不准”，而是：

- 在线 `label_posts_batch`
- 离线 `export_llm_label_candidates.py`

之前还不是同一条真相链。

大白话说：

- 同样是“哪些帖子值得进标签链、配几条 top comments”，不该 task 算一套、script 再偷 task 私有函数算一套。

## 发现的问题

当前仓库里还留着一个很典型的边界漂移点：

- `backend/app/tasks/llm_label_task.py`
  - `_fetch_post_candidates(...)`
  - `_fetch_top_comments(...)`

它们本质上已经不是 task 壳该继续背的逻辑了，因为：

1. 这是候选规划，不是任务调度
2. 离线导出脚本也在反向 import 这两个 task 私有函数
3. 后面如果再改：
   - value score 口径
   - mid/high 配额
   - top comments 取样
   task 和 script 很容易再次漂开

一句大白话：

- **post 候选规划还没像 comment 那样回到服务层。**

## 修复动作

### 1. 新增公共 planner service

新增：

- `backend/app/services/llm/post_label_planner.py`

正式收了：

- `fetch_incremental_post_candidates(...)`
- `fetch_post_top_comments(...)`
- `DEFAULT_HIGH_SCORE_RATIO`

这层现在统一承接：

- `core/lab` 候选帖子筛选
- mid/high 配额拆分
- `text_norm_hash` 去重
- top comments 读取

### 2. 收薄 llm_label_task

修改：

- `backend/app/tasks/llm_label_task.py`

现在：

- `_fetch_post_candidates(...)`
- `_fetch_top_comments(...)`

都只剩薄委托：

1. 注入 `SessionFactory`
2. 透传现有 score/ratio 参数
3. 调公共 planner service

也就是说：

- task 还保留兼容 seam，方便旧测试继续 patch
- 但真正的 SQL 和候选规划逻辑已经不在 task 壳里了

### 3. 收正离线导出脚本

修改：

- `backend/scripts/report/export_llm_label_candidates.py`

现在离线 post 导出不再反向 import task 私有函数，而是直接走：

- `fetch_incremental_post_candidates(...)`
- `fetch_post_top_comments(...)`

一句大白话：

- **在线链和离线导出终于站到了同一条 post planner 真相链上。**

### 4. 补测试并锁边界

新增：

- `backend/tests/services/llm/test_post_label_planner.py`

覆盖：

- mid/high 候选合并后按 `id` 去重
- top comments 按当前合同返回 body 列表

同时保留并跑通：

- `backend/tests/services/llm/test_post_label_workflow.py`
- `backend/tests/tasks/test_llm_label_task.py`
- `backend/tests/scripts/test_export_llm_label_candidates.py`

## 结果

这轮收完后，`post` 标签链和离线导出这条边界终于说清楚了：

- planner 在服务层
- task 是入口壳
- script 是 CLI 壳

后面再改：

- 候选分层
- 去重逻辑
- top comments 抽样

不容易再出现：

- 在线一套
- 离线一套
- AI 再顺着 task 私有函数继续漂

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_post_label_planner.py \
  tests/services/llm/test_post_label_workflow.py \
  tests/tasks/test_llm_label_task.py \
  tests/scripts/test_export_llm_label_candidates.py -q
```

结果：

- `14 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/llm/post_label_planner.py \
  app/tasks/llm_label_task.py \
  ../backend/scripts/report/export_llm_label_candidates.py \
  tests/services/llm/test_post_label_planner.py
```

结果：

- 通过

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 当前判断

这一步是第三轮里一刀很值钱的“边界收口”：

- post 候选规划开始只有一个正式真相源
- task 壳继续变薄
- script 壳不再反向咬 task 私有实现

这很符合当前第三轮的目标：

- 各模块职责更清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
