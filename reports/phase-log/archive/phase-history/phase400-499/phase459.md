# Phase 459 - Worker / State Orchestration P0 落地

## 背景

这一轮不再继续修报告层补丁，而是开始执行“分析主链中段重构”的第一段：`Worker / State Orchestration`。

目标很明确：

- 把 live 验收从“手工起 worker、旧 shell 可能残留、结果可能被污染”的状态，
- 收成仓库内统一、可复用、可自检的执行合同。

## 发现

- `analysis-live` 和 `bulk-live` 旧进程确实可能残留在不同 shell 里继续跑。
- 如果 runtime 没有统一入口，`Full A live` 的复验结果就不够可信。
- 这不是单纯的运维小问题，而是会影响架构重构判断的 P0 风险。

## 本轮改动

### 1. 新增统一 runtime 管理脚本

- 文件：`backend/scripts/acceptance/manage_live_runtime.py`
- 支持动作：
  - `start`
  - `stop`
  - `restart`
  - `status`

脚本职责：

- 统一拉起隔离 backend：`127.0.0.1:8016`
- 统一拉起：
  - `analysis-live`
  - `bulk-live`
- 统一管理 pid/log 文件
- 检测 duplicate worker
- 清扫残留进程
- 检查 backend readiness

### 2. 固化 Makefile 合同

- 文件：`makefiles/test.mk`

新增命令：

- `make live-runtime-start`
- `make live-runtime-stop`
- `make live-runtime-restart`
- `make live-runtime-status`

并把 `make test-e2e-live-report` 改成依赖这套隔离 runtime，不再默认吃主开发环境。

### 3. 补运维文档

- 文件：`backend/docs/WORKER_OPS.md`

把 live worker 的启动、停止、状态查看写成仓库级合同，避免继续靠临时 shell 和记忆操作。

### 4. 补定向测试

- 文件：`backend/tests/scripts/acceptance/test_manage_live_runtime.py`

覆盖：

- 参数解析
- 隔离 backend/worker spec 构建
- duplicate worker 检测
- clean runtime 状态判定

## 验证

已通过：

- `cd backend && pytest tests/scripts/acceptance/test_manage_live_runtime.py -q`
- `cd backend && python -m py_compile scripts/acceptance/manage_live_runtime.py`
- `make live-runtime-start`
- `make live-runtime-status`
- `make live-runtime-stop`

现场验证结果：

- backend 正常起在 `8016`
- `analysis-live` 正常 ready
- `bulk-live` 正常 ready
- `stop` 后残留进程为 `0`

## 结论

这轮的价值，不是“又补了一个脚本”，而是：

- `worker` 层已经正式被纳入中段重构
- live 验收现场第一次有了统一、隔离、可检测的运行合同
- 后续再做 `Evidence Selection / Evidence Ledger` 重构时，复验结果终于有可信底座

## 下一步

- 不回头加更多领域硬编码
- 以这套干净 runtime 为唯一现场
- 继续推进：
  - `Evidence Selection / Evidence Ledger`
