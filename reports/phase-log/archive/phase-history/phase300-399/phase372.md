# Phase 372 - 第三轮大包推进：标签导出链封板第一包

## 1. 发现了什么？

这次我没有再拆一个小 seam，而是直接收掉了标签导出链里最重的一坨：

- `backend/app/services/llm/label_export_service.py`

它之前是一个 `617` 行的离线大总管，自己同时背着：

- posts 导出
- comments 导出
- historical activation 导出
- jsonl 写文件
- comment payload 组装
- domain 轮转

大白话说：

- 同一个文件既当入口，又亲手跑 posts/comments/activation 三套逻辑。

这类文件最容易继续漂，也最不适合后面继续做产品级维护。

## 2. 是否需要修复？

需要，而且这一大包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 拆成三块正式子模块

新增：

- `backend/app/services/llm/label_export_io.py`
- `backend/app/services/llm/post_label_export.py`
- `backend/app/services/llm/comment_label_export.py`

职责现在已经拆清：

- `label_export_io.py`
  - `_truncate`
  - `_write_jsonl`
  - `_comment_payload_from_row`
  - `_interleave_selected_rows_by_domain`

- `post_label_export.py`
  - `_export_posts`
  - `_fetch_post_candidates_all`
  - `_count_post_candidates_core_lab`
  - `_export_posts_all`

- `comment_label_export.py`
  - `_export_comments`
  - `_fetch_comment_candidates_all`
  - `_count_comment_candidates_core_lab`
  - `_build_comment_activation_export`
  - `_export_comment_activation`
  - `_export_comments_all`

### 3.2 收薄总入口

调整：

- `backend/app/services/llm/label_export_service.py`

现在这个文件只保留：

- `LabelExportWorkflowInput`
- `run_label_export(...)`
- 对旧测试和脚本兼容的导出别名

也就是说：

- 总入口只管分流和返回结果
- posts/comments/activation 的真逻辑已经各回各位

### 3.3 先补总控测试，再锁整包

新增：

- `backend/tests/services/llm/test_label_export_service.py`

锁住两条最关键的总控路径：

- default mode 下 posts/comments 正常写文件
- historical activation 下 batch 写文件和 summary 透传正常

同时继续跑通既有测试：

- `backend/tests/scripts/test_export_llm_label_candidates.py`
- `backend/tests/services/llm/test_post_label_planner.py`
- `backend/tests/services/llm/test_comment_label_planner.py`
- `backend/tests/services/llm/test_llm_label_task_runtime.py`

## 4. 验证结果

### 4.1 成组定向回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_label_export_service.py \
  tests/scripts/test_export_llm_label_candidates.py \
  tests/services/llm/test_post_label_planner.py \
  tests/services/llm/test_comment_label_planner.py \
  tests/services/llm/test_llm_label_task_runtime.py -q
```

结果：

- `13 passed`

### 4.2 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.3 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/llm/label_export_service.py \
  backend/app/services/llm/label_export_io.py \
  backend/app/services/llm/post_label_export.py \
  backend/app/services/llm/comment_label_export.py \
  backend/tests/services/llm/test_label_export_service.py
```

结果：

- 通过

## 5. 文件体量变化

命令：

```bash
wc -l \
  backend/app/services/llm/label_export_service.py \
  backend/app/services/llm/label_export_io.py \
  backend/app/services/llm/post_label_export.py \
  backend/app/services/llm/comment_label_export.py \
  backend/scripts/report/export_llm_label_candidates.py
```

结果：

- `label_export_service.py`: `171`
- `label_export_io.py`: `54`
- `post_label_export.py`: `235`
- `comment_label_export.py`: `225`
- `export_llm_label_candidates.py`: `82`

最关键的变化是：

- `label_export_service.py` 从原来的 `617` 行，压到了现在的 `171` 行

这说明这次不是小整理，而是真正把离线导出大总管拆成了可维护的几块。

## 6. 当前完成度判断

我的最新判断：

- 第三轮完成度：约 `88%`
- 系统整体完成度：约 `93%-94%`

离 `95+` 还差最后几包：

1. `facts / 报告模块` 最后一包 request / assembly / runtime 清尾
2. `数据采集模块` 最后一小包 wrapper / side-effect 清尾
3. `语义 / 标签模块` 最后一包 sync / import-export 接缝清尾

## 7. 这次执行的价值是什么？达到了什么目的？

这次最值钱的地方很直接：

- 标签导出链不再是一个 600 多行的大总管
- posts / comments / activation 三条链终于开始有各自的正式齿轮
- 总入口开始真正像入口，而不是又当入口又亲手干重活

一句大白话总结：

- 这次把标签导出这一大包真正拆开了，第三轮已经明显从“拆主链”进入“封板清尾”阶段。
