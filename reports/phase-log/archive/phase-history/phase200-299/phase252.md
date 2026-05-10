# Phase 252 - pytest asyncio 配置噪音清理

执行时间: 2026-03-13

## 1. 发现了什么

- 后端测试每次都会出现一条固定噪音：
  - `PytestConfigWarning: Unknown config option: asyncio_default_fixture_loop_scope`
- 根因不是测试代码出错，而是当前仓库使用的 `pytest-asyncio` 版本是 `0.21.1`。
- 这个版本支持 `asyncio_mode`，但**不支持** `asyncio_default_fixture_loop_scope`，所以 `backend/pytest.ini` 里的这行配置属于“写了也没用，还会制造警告”。

## 2. 是否需要修复

- 需要，已经修掉。
- 这是典型的配置噪音问题：
  - 不影响主要逻辑
  - 但会污染测试输出
  - 久了容易把真正的 warning 淹没掉

## 3. 精确修复方法

- 删除 [pytest.ini](/Users/hujia/Desktop/RedditSignalScanner/backend/pytest.ini) 里的：
  - `asyncio_default_fixture_loop_scope = function`
- 保留：
  - `asyncio_mode = auto`
- 这样做是最小改动：
  - 不改测试行为
  - 不升级依赖
  - 只去掉当前版本根本不识别的无效配置

## 4. 验证结果

- 检查当前插件版本：
  - `pytest-asyncio = 0.21.1`
- 本地源码确认：
  - 当前插件实现中不存在 `asyncio_default_fixture_loop_scope`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - `18 passed`
  - 该 warning 已消失

## 5. 这次执行的价值

- 这次不是修功能，是把测试输出里的“固定假噪音”清掉。
- 以后再看 pytest 输出时，更容易第一时间发现真正的新 warning，不会被老噪音盖住。
