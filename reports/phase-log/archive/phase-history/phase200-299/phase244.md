# Phase 244 - Phase240 确定性协议永久落地

## 这轮改了什么

### 1. 关键文件增加确定性协议注释
- `backend/scripts/report/generate_t1_market_report.py`
  - 文件头增加 `DETERMINISM PROTOCOL` 注释
  - `deterministic_validation = bool(args.anchor_ts)` 上方增加开关注释
  - 4 个 `if deterministic_validation:` 守卫点都补了原因说明
- `backend/app/services/analysis/t1_stats.py`
  - 文件头增加 `DETERMINISM PROTOCOL` 注释
  - 明确规定新增时间查询必须接受 `anchor_ts`

### 2. Makefile 增加确定性门禁
- 新增 target:
  - `check-determinism`
- 检查范围:
  - `backend/scripts/report/generate_t1_market_report.py`
  - `backend/app/services/analysis/t1_stats.py`
- 规则:
  - 两个关键文件中不允许再出现 `NOW()`
- 同时把 `check-determinism` 设为 `test-quality-gate` 的前置依赖

### 3. 新增确定性回归测试
- 新文件:
  - `backend/tests/services/report/test_determinism_regression.py`
- 覆盖点:
  - 报告脚本中无 `NOW()`
  - `t1_stats.py` 中无 `NOW()`
  - `deterministic_validation` 守卫变量存在
  - `if deterministic_validation:` 守卫点数量 >= 4

### 4. 新增协议文档
- 新文件:
  - `docs/determinism-protocol.md`
- 内容:
  - 确定性模式定义
  - 协议规则
  - 门禁命令
  - AI 协作指引

## 验证结果

### 1. NOW() 门禁
- 命令:
  - `make check-determinism`
- 结果:
  - `✅ PASS: No NOW() in critical files.`

### 2. 确定性回归测试
- 命令:
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_determinism_regression.py -v`
- 结果:
  - `4 passed`

### 3. 已有质量门不破
- 命令:
  - `SKIP_DB_RESET=1 make test-quality-gate`
- 结果:
  - `24 passed`

## 这轮特别注意的点

- 文件头协议注释里**没有**直接写 `NOW()` 字面量。
- 原因不是漏写，而是新的 `check-determinism` 门禁本身就是用 `grep "NOW()"` 扫关键文件。
- 如果把 `NOW()` 原样写进注释，门禁会把注释也当成违规命中。
- 所以这里改成“当前时间函数 / 动态时间 SQL”这种说法，保证协议说明和门禁规则不互相打架。

## 收口结论

- Phase240 的“确定性模式”已经从“修过一次”升级成“有注释、有门禁、有回归测试、有文档”的长期协议。
- 后续如果有人再往这两条关键链路里塞动态时间 SQL 或未受控的 LLM 调用，至少会在：
  - 文件头协议
  - `check-determinism`
  - `test_determinism_regression.py`
  这三层里被拦住。
