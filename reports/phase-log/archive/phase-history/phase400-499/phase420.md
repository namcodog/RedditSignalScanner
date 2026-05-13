# Phase 420 - Hotpost 首屏英文噪音继续收口

## 目标

继续把 Hotpost 首屏从“原始数据展示”收成“可快速判断”，重点清理中英混杂和英文长段落带来的阅读阻力。

## 本轮修复

- 文件：`frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - 新增 `toHotpostTopicTitle()`：
    - 话题标题不是中文时，首屏改成 `重点话题 N`，不再直接顶英文标题。
  - 新增 `toPostPreviewText()`：
    - 证据帖预览若为英文，改成中文引导句（建议点原帖看上下文）。
  - 强化 `toHotpostReadableText()`：
    - 去 markdown/URL 噪音后，若中文占比过低则回落中文兜底句。

- 文件：`frontend/src/lib/product-surface.ts`
  - 强化 `toUserFacingSnippet()`：
    - 增加中文占比阈值，避免“少量中文 + 大段英文”混杂文本进入首屏卡片。

## 验证

- Hotpost + 相关页面定向测试：
  - `13/13 passed`
- 完整正式 E2E：
  - `make test-e2e -> 21 passed`

## 结果

- Hotpost 首屏进一步去“原始英文直贴”。
- 主链稳定性保持全绿，没有为体验优化引入回归。
