# Phase 306 - 第三轮下一刀：语义/标签模块在线与离线标签持久化合同统一

> 时间：2026-03-16
> 模块：语义 / 标签模块
> 范围：在线增量打标签、离线标签导入、标签写库合同
> 当前状态：已完成第三轮这一刀

---

## 1. 发现了什么？

第三轮继续回到语义 / 标签模块后，这一刀没有去动 prompt，也没有去碰离线 Codex 流程本身，而是先盯住了一个更底层、更容易继续漂的点：

- **在线 `llm_label_task` 和离线 `import_client_llm_labels.py` 还在各写各的标签入库逻辑**

更具体一点：

1. 在线 task 里自己维护一套 post/comment label upsert 逻辑
2. 离线导入脚本里又自己维护一套类似的 build-row / upsert 手势
3. 这意味着：
   - 相同标签结构，可能由两套写法落库
   - 后面一旦字段、序列化方式、metadata 合同再变，就容易再次分叉

一句大白话：

- **第一轮让标签链开始说真话，第二轮把评论候选规划服务化，第三轮这一刀继续把“标签怎么写进库”也收成同一套合同。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这轮做的是结构性收口，不是标签算法改版。

---

## 3. 精确修复方法？

### 3.1 新增正式标签持久化服务

新增：

- `backend/app/services/llm/label_persistence.py`

正式收口了两类公共能力：

1. **统一 row 构造**
   - `build_post_label_row(...)`
   - `build_comment_label_row(...)`

2. **统一 upsert 写库**
   - `upsert_post_label_rows(...)`
   - `upsert_comment_label_rows(...)`

也就是说，现在不是：

- 在线一套写法
- 离线一套写法

而是：

- **先通过同一套 row 合同**
- **再通过同一套持久化口子写库**

### 3.2 在线 task 退回“执行入口”

修改：

- `backend/app/tasks/llm_label_task.py`

现在在线链里的：

- `_upsert_post_label(...)`
- `_upsert_comment_label(...)`

不再自己拼 row、自己管 SQL，而是改成：

1. 调 `build_*_label_row(...)`
2. 调 `upsert_*_label_rows(...)`

这样 task 层继续保留：

- 原流程
- 原状态合同
- 原测试 seam

但“标签怎么落库”这件事，已经不再继续长在 task 文件里。

### 3.3 离线导入脚本不再自己维护第二套写库手势

修改：

- `backend/scripts/import/import_client_llm_labels.py`

现在：

- `_upsert_posts(...)`
- `_upsert_comments(...)`

也改成统一走共享持久化层。

这一步的意义很直接：

- 离线导入不再是“另一套平行世界”
- 在线增量和离线补标终于开始围绕同一套标签写库合同协作

### 3.4 测试把新边界锁住

新增：

- `backend/tests/services/llm/test_label_persistence.py`
- `backend/tests/scripts/test_import_client_llm_labels.py`

并补跑：

- `backend/tests/tasks/test_llm_label_task.py`

这轮还顺手修正了一条新测试断言：

- `import_client_llm_labels.py` 的评论评分结果当前真实合同是 `business_pool = "lab"`
- 所以测试改回当前真实评分口径，而不是为了过测试把业务规则硬拉回旧世界

一句大白话：

- **测试现在锁住的是“共享持久化合同”，不是某个历史假设。**

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“标签更准了”，而是：

- 在线增量和离线导入不再各自维护两套标签写库逻辑
- 后面如果继续改标签结构、metadata、序列化方式，不会再两边一起漂
- 语义 / 标签模块又少了一处“同一件事由两只手各写一遍”的高耦合点

一句大白话：

- **这刀把“标签怎么写进库”先钉成了一个真相源。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_label_persistence.py \
  tests/tasks/test_llm_label_task.py \
  tests/scripts/test_import_client_llm_labels.py -q
```

结果：

- `8 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/label_persistence.py \
  backend/app/tasks/llm_label_task.py \
  backend/scripts/import/import_client_llm_labels.py \
  backend/tests/services/llm/test_label_persistence.py \
  backend/tests/scripts/test_import_client_llm_labels.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

语义 / 标签模块第三轮这一刀之后，还剩几个继续值得打磨的点：

1. posts 标签链和 comments 标签链还能继续统一边界
2. provider / import-export / semantic sync 之间还能再压薄一轮
3. 评论历史价值激活这条高成本专项，后面还要单独做成本与质量平衡，不在这刀里一起展开

所以这轮的正确定位是：

- **第三轮这一刀已经把“标签写库合同”先统一了**
- 但不是语义 / 标签模块第三轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第三轮当前节奏，下一步继续打最重的剩余耦合点：

- facts / 报告模块
- 数据采集模块
- 或语义 / 标签模块的下一刀（provider / sync / import-export 边界）

优先原则不变：

- 继续打最重的几组齿轮
- 继续把“同一件事两只手各写一遍”的地方收成单一真相源
- 继续把整机往 `95+` 的产品级稳定状态推进

一句话：

- **这刀先把标签写库合同统一了，后面继续按同样节奏稳稳打磨。**
