# Phase 419 - 截图级验收与首屏噪音清理

## 目标

基于桌面端 + 移动端真实截图做最后一轮“问题即修复”收口，把仍影响完成感的噪音点清干净。

## 截图级验收范围

输出目录：`output/playwright/phase418-browser/`

- 桌面端：
  - `input-desktop.png`
  - `progress-desktop.png`
  - `report-desktop.png`
  - `hotpost-desktop.png`
  - `admin-desktop.png`
- 移动端：
  - `input-mobile.png`
  - `progress-mobile.png`
  - `report-mobile.png`
  - `hotpost-mobile.png`
  - `admin-mobile.png`

## 验收发现与修复

### 1) Progress 页阶段状态会露英文

- 发现：
  - `当前阶段` 曾出现 `data collection` / `done`。
- 修复：
  - 文件：`frontend/src/pages/ProgressPage.tsx`
  - 增加阶段值归一化（空格/连字符转下划线）+ 扩充映射：
    - `data_collection / content_extraction / nlp_analysis / report_generation / done / success ...`
  - 结果：进度页阶段状态统一为中文表达。

### 2) Report 页首屏会顶出英文碎句

- 发现：
  - 首屏 `最值得追的机会 / 最明显抱怨` 在部分 live 样本会出现英文碎句。
- 修复：
  - 文件：`frontend/src/lib/product-surface.ts`
  - 新增文本清洗与首屏兜底策略：
    - 过滤 markdown 链接/URL 噪音
    - 非中文主文案不再直接上首屏，改为中文可执行兜底句
  - 同时保持结构化机会优先级（`product_positioning` 优先）。

### 3) Hotpost 首屏摘要含 markdown 原文噪音

- 发现：
  - live 热点首屏会直接出现 `[title](url)` 这类原始格式，信息密度过高。
- 修复：
  - 文件：
    - `frontend/src/lib/product-surface.ts`
    - `frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - 处理：
    - 去 markdown 链接和裸 URL
    - 压缩长度，避免首屏超长段落
    - 非中文文本走中文判断句兜底
  - 结果：hotpost 首屏从“原始数据贴墙”收成“可扫判断”。

### 4) Admin 首屏最近任务状态露英文

- 发现：
  - `最近任务` 里出现 `completed`。
- 修复：
  - 文件：`frontend/src/lib/product-surface.ts`
  - 增加 admin 任务状态映射（`completed -> 已完成` 等）。

## 验证结果

- 定向测试：
  - `Input/Progress/Report`：`17/17 passed`
  - `Admin/Hotpost/Report`：`13/13 passed`
- 完整正式 E2E：
  - `make test-e2e`：`21 passed`
- 构建：
  - `cd frontend && npm run build`：通过

## 当前判断

- 这轮是“截图驱动修复”，不是主观润色。
- 主链稳定性继续保持全绿。
- 输入/等待/报告/热点/控制面在双端都更接近统一产品语言。

## 下一步

继续 Phase 26 最后一段：

1. 按 `ui-ux-pro-max / frontend-design / web-design-guidelines` 再做一轮只针对“信息密度与阅读节奏”的细修。
2. 目标是把 hotpost 首屏英文残留再压一档，进一步提升第一眼完成感。
