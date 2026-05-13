# Phase 630 - Hotpost 上线边界矩阵 + live runtime / frontend 封版口径

## 1. 发现了什么？

- `hotpost` 当前不是 open-question 主链阻塞，但它还没有正式封版。
- 从当前测试和 live 阶段记录看，真正要收口的不是“大重构 hotpost”，而是：
  - 哪些 family 现在可以上线
  - 哪些只能灰度
  - 哪些暂时不能信
- runtime / frontend 这边也已经不再是大坑：
  - live runtime 已有隔离脚本
  - 前端 build 已经通过
  - 剩下要补的是“运维流程口径”，不是继续修主链

## 2. 是否需要修复？

- 需要，但本轮以文档封版和运维口径收口为主，不再开新重构。

## 3. 精确修复方法

### 3.1 hotpost 上线边界矩阵

根目录新增：

- `PROJECT_CLOSEOUT_STATUS_2026-04-02.md`

其中明确给出：

- live 验收预检清单
- `hotpost` family 上线分级
- 失败兜底规则
- runtime / frontend 封版判断

### 3.2 worker 运维口径补齐

修改文件：

- `backend/docs/WORKER_OPS.md`

新增口径：

- 每次 live 验收前必须：
  - 显式重启隔离 runtime
  - 检查 backend health
  - 检查 worker status
  - 确认当前是正确的 dev/live 环境
- 目的：
  - 先排除 runtime 假故障
  - 再判断算法问题

### 3.3 根目录总清单收正

修改文件：

- `PROJECT_REMAINING_WORKLIST_2026-04-02.md`

收正内容：

- `EDC` 已通过
- `analyses.sources` 审计摘要已落地并在 live 确认
- 第三领域 `AI_Workflow` 已通过
- 当前剩余问题收窄到：
  - hotpost 边界
  - runtime 稳定性口径
  - 少量长期优化项

## 4. 验证

### hotpost 测试基线

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/hotpost/test_hotpost_mode_contract.py \
  tests/services/hotpost/test_hotpost_quality_contract.py \
  tests/services/hotpost/test_hotpost_runtime.py \
  tests/services/hotpost/test_hotpost_search_workflow.py -q
```

结果：

- `68 passed`

### 前端 build

```bash
cd frontend && npm run build
```

结果：

- 通过

## 5. 下一步系统性的计划是什么？

1. 根目录文档、phase log、进度文件全部同步
2. 只把 durable delta 写回 `key-os`
3. 当前主线正式切到：
   - 维持 live 可验收
   - 处理长期优化项

## 6. 这次执行的价值是什么？达到了什么目的？

- `hotpost` 终于不再停留在“感觉差不多能上”的模糊状态，而是有了明确边界。
- live runtime 也不再靠个人记忆操作，而是有固定预检清单。
- 当前项目已经从“最后几刀收尾”进一步推进到“可封版、可交接”的状态。
