# Phase 424 - Phase 28 第二刀（弱态文案压缩 + 移动端截图复核）

## 目标

继续收尾，把弱态/空态的“解释味”压到更短的结论与动作语句，并做移动端截图复核。

## 本轮改动

- 文件：`frontend/src/pages/ReportPage.tsx`
  - 空态说明统一收短：
    - 社区/痛点/驱动力/机会四类空态说明改成一句结论 + 一句动作。
  - 错误态文案收短：
    - 描述改为 `系统刚才没整理完整，先重新加载一次。`
    - 下一步改为 `先重载一次；还不行就回首页重跑。`
  - 多个维度空态 `nextStep` 收成更直接的动作表达。

- 文件：`frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - 快扫失败态收短：
    - 描述改为 `系统已接到这次搜索，正在重新整理热点信号。先重试一次，不行就换关键词重扫。`
    - 下一步改为 `先重试一次；还不行就换关键词，回搜索页重扫。`

- 测试同步
  - `frontend/src/pages/__tests__/ReportPage.test.tsx`
  - `frontend/e2e/report-page-simple.spec.ts`
  - `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`

## 移动端截图复核

- 产物目录：`output/playwright/phase423-mobile/`
  - `input-mobile.png`
  - `hotpost-mobile.png`
  - `progress-mobile.png`
- 复核发现：
  - `progress` 直链在无会话上下文时会回首页（URL 从 `/progress/{task_id}` 回到 `/`），属于当前路由行为，不是本轮回归。

## 验证

- 定向测试：
  - `ReportPage / HotPostResultPage.surface / ProgressPage` 共 `16 passed`
- 构建：
  - `frontend build` 通过
- 完整正式 E2E：
  - `make test-e2e` -> `21/21 passed`

## 结果

- 弱态、空态和错误态的阅读负担继续下降。
- 主链稳定性保持不变，正式验收继续全绿。
