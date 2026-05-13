# Phase 821 - 小程序前端视觉优化回灌（Alexandria editorial）

## 范围
- 只动小程序前端渲染层与样式层。
- 不改后端接口、不改数据逻辑、不改路由、不改 tab bar 结构。

## 设计方向
- 采用 `DESIGN.md` 的 `Alexandria — High-End Editorial` 路线：
  - serif 大标题
  - tonal layering 代替明显边框
  - Public Sans 元数据标签
  - whitespace 做结构
- 按 `小程序前端视觉优化.md` 先落 `Phase 1 + Phase 2`，并把已存在但未接入的 `detail-immersive.scss` 正式接进详情页。

## 本次改动

### 首页卡片
- `CluePreviewCard.tsx`
  - CTA 从纯文字收成 subtle pill
- `clues.scss`
  - `.clue-sticky-header` 增加半透明毛玻璃
  - `.clue-list` 间距从紧凑调成更松的 editorial 节奏
  - `.clue-card` 去显式 border，改成 tonal layering + diffused shadow
  - 标题字号与行高上调
  - `signal/breakdown/hot` 核心块 padding 与层次增强
  - hot 争议图 compact 样式加厚并去掉边框感
  - `看详情` 改成 subtle button 风格

### 详情页
- `velocity/index.tsx`
  - 将详情页拆成 Hero / Analysis / Proof / Trust 四段
  - 新增 `DetailSection` 包装器，引入 section divider
  - 原帖入口并入 trust footer
  - 首条引用默认展开
- `velocity/index.scss`
  - 正式接入 `detail-immersive.scss`
  - `detail-surface` 去边框，增强 surface 层次
  - quote / trust footer / origin block 视觉收口
- `velocity/detail-sections.tsx`
  - hot 争议雷达接入 spotlight 类
  - `QuoteItem` 支持 `defaultExpanded`
- `velocity/detail-sections.scss`
  - 调整详情块内 item 节奏和标题层级

## 验证
- 执行：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：
  - 构建通过

## 结论
- 首页卡片从“功能稿感”往“高端编辑感”收了一步，但没有动数据结构。
- 详情页不再是平铺文字墙，而是有 Hero / Analysis / Proof / Trust 的阅读节奏。
- 当前版本可以进入开发者工具做视觉验收；如需继续迭代，优先微调 spacing、字体和争议图细节，不要回退到大范围结构改动。
