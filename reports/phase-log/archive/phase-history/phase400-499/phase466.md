# Phase 466 - Canonical Report Assembly 第一段抽离

## 背景

在连续完成：

- `Evidence Selection`
- `Evidence Ledger`
- `Insight Synthesis`
- `Analysis Artifacts`

之后，下一步终于进入 `Canonical Report Assembly`。

但这一步必须有一个硬约束：

- **不能破坏原来的产品输出合同**

也就是说，允许拆内部编排，不允许偷改外部 `Full A` 的交付口径。

## 本轮改动

### 1. 新增 canonical assembly 模块

- 文件：`backend/app/services/report/report_canonical_assembly.py`

当前抽离出的编排职责：

- structured report 合同清洗 / 兜底
- narrative markdown 选择
- controlled markdown 回退
- render bundle 生成

### 2. 收窄 workflow 边界

- 文件：`backend/app/services/report/report_assembly_workflow.py`

此前 workflow 自己同时承担：

- quality gate 判断
- enrichment
- canonical 装配
- payload 构建
- 审计

现在 canonical 装配已经移入新模块。

workflow 留下的职责变成：

- 门禁判断
- enrichment
- payload 构建
- 审计

### 3. 补齐定向测试和回归测试

新增：

- `backend/tests/services/report/test_report_canonical_assembly.py`

更新：

- `backend/tests/services/report/test_report_assembly_workflow.py`

这轮也把 workflow 测试边界收回到了新职责上，不再继续盯旧的 monkeypatch 接缝。

## 验证

通过：

- `cd backend && pytest tests/services/report/test_report_canonical_assembly.py -q`
- `cd backend && pytest tests/services/report/test_report_assembly_workflow.py -q`
- `cd backend && python -m py_compile app/services/report/report_canonical_assembly.py app/services/report/report_assembly_workflow.py`

## 结论

这轮之后，`Canonical Report Assembly` 已经开始落地，而且没有破坏原来的产品输出合同。

也就是说：

- 后端装配边界更清楚了
- 前端和用户看到的报告口径没有被擅自改掉

## 下一步

- 继续盘点剩余 report workflow / runtime 职责
- 准备下一段 Assembly 重整
