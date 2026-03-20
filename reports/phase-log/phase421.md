# Phase 421 - Hotpost 交互减负与文案压缩

## 目标

继续收掉“字多、解释重、一眼不清楚”的掉分点，不扩功能，只把 Hotpost 首屏和动作文案压成更短、更直接的判断语言。

## 本轮修复

- 文件：`frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - 首屏判断区改为更短口径：
    - `先决定追不追，再转深度报告` -> `先定追不追`
    - `先按这三步拆判断` -> `这页先看三件事`
    - 三步标签从带编号改成短词：`先看摘要 / 再扫证据 / 最后看社区`
  - 压缩加载态、重扫提示、深挖带回提示和空态下一步文案，去掉重复解释。
  - 收短社区区与补充细节区描述，降低阅读负担。

- 文件：`frontend/src/lib/product-surface.ts`
  - Hotpost action plan 文案继续压缩：
    - `值钱就深挖；不放心就先看证据。` -> `有价值就深挖；拿不准先看证据。`
    - `先看关键证据；不稳就带着关键词回去重扫。` -> `先看关键证据；不稳就换词重扫。`

- 测试与验收同步
  - 更新 `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx` 断言到新文案。
  - 更新 `frontend/e2e/product-polish-smoke.spec.ts` 断言到新标题与新三步标签，并处理 strict mode 精确匹配。

## 验证

- 定向页面测试：
  - `cd frontend && npm run test -- src/pages/__tests__/HotPostResultPage.surface.test.tsx src/pages/__tests__/InputPage.test.tsx`
  - `11/11 passed`
- 前端构建：
  - `cd frontend && npm run build` 通过
- 完整正式 E2E：
  - `make test-e2e` -> `21/21 passed`

## 结果

- Hotpost 页面首屏判断更短、更直接，重复解释继续下降。
- 主链稳定性保持不回退，正式 E2E 继续全绿。
