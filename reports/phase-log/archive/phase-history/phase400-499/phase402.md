# Phase 402 - 视觉语言升级与正式 E2E 收口

## 背景

`Phase 401` 已经把正式 E2E 口径拉回当前产品世界，但产品整体还停在约 `92-93`：

- 主链路已经顺了
- 首屏判断已经站住了
- 正式 E2E 已经能代表当前产品
- 但整套视觉语言仍然偏“普通 SaaS 卡片”，还没到高完成度产品的气质

这轮目标不是再修业务逻辑，而是把：

- 全局视觉 token
- 共享产品组件
- report / hotpost / admin 三张脸
- 正式 E2E 的最后一层环境/合同噪音

一起收紧，让产品往更高的完成感推进。

---

## 本轮发现

### 1. 当前界面最大问题，不是结构，而是视觉语言过软

前端主链页面已经能讲清判断，但共享样式层仍然有明显旧世界痕迹：

- 全局 token 还是紫色 SaaS 方案
- 字体还是默认现代产品味，缺品牌个性
- Hero / 决策摘要 / 状态面板虽然结构对，但视觉上不够“像一套高价值产品”
- Admin 还是混着后台页视觉习惯

结论：

- 这轮应该先改设计系统，不应该继续只改文案

### 2. `ui-ux-pro-max` 不是不能用，而是安装入口坏了

排查后确认：

- skill 本体在本机真实目录里存在
- `~/.codex/skills/ui-ux-pro-max/scripts` 和 `data` 只是坏掉的路径指针

这轮已修复为真实路径，并验证脚本可运行。

### 3. 正式 E2E 最后阻塞也不是产品回归，而是测试合同和本地运行面问题

这轮完整跑正式 E2E 时，新增暴露出三类非产品层问题：

- `admin` E2E 曾因为本地后端没起来而误失败
- `admin` 测试账号密码会漂，导致 API 登录拿 token 不稳定
- `product-polish-smoke` 的 live hotpost 结果 URL 用 `127.0.0.1`，和当前 Playwright 托管入口不一致

这些都不是产品页本身回归，但会直接污染验收分。

---

## 本轮执行

### A. 统一视觉方向

这轮明确把产品收成：

- `编辑部式情报台`
- 不是紫色白底 SaaS
- 而是更像“高密度判断工具 + 编辑部风格 + 工业质感”

视觉方向落点：

- 主色从紫色切到暖骨白 + 墨色 + 琥珀强调
- 标题切到更有识别度的 serif 方向
- 正文字体切到更稳定、耐读的中文 sans
- 背景加入轻网格和气氛层，不再是平面白底

### B. 升级全局设计系统

主要改动：

- `frontend/src/styles/index.css`
- `frontend/tailwind.config.ts`
- `frontend/src/App.tsx`

具体落地：

- 重做全局颜色 token、圆角、背景、按钮、焦点态
- 加入 `Noto Serif SC / Noto Sans SC / IBM Plex Mono`
- 新增 `surface-panel / surface-panel-muted / surface-panel-strong / surface-action-* / surface-section-kicker` 这一套共享语言
- 把应用级 loading fallback 从旧 inline-style spinner 改成正式产品 loading 卡

### C. 升级共享产品组件

主要改动：

- `frontend/src/components/product/SurfaceHero.tsx`
- `frontend/src/components/product/DecisionSummaryPanel.tsx`
- `frontend/src/components/product/ProductStatePanel.tsx`
- `frontend/src/components/SkeletonLoader.tsx`

具体落地：

- Hero 改成更像主判断封面，而不是普通卡片
- 决策面板改成“强 verdict + 两块辅助判断”结构的视觉强化版
- 状态面板按钮和容器统一进入新视觉语言
- report skeleton 也进入新语言，不再和正式页面断层

### D. 升级关键页面壳层

主要改动：

- `frontend/src/pages/ReportPage.tsx`
- `frontend/src/pages/hotpost/HotPostResultPage.tsx`
- `frontend/src/pages/AdminDashboardPage.tsx`

具体落地：

- 三张脸顶部统一成更像产品封面/控制台，而不是默认 header
- report 的欢迎页、CTA 区、逐维探索区统一进入新语言
- hotpost 的主摘要区、顶部条、卡片区统一进入新语言
- admin 的统计卡、任务区、控制面捷径收成同一套风格

### E. 把正式 E2E 最后一层噪音清掉

主要改动：

- `frontend/e2e/product-polish-smoke.spec.ts`
- `frontend/e2e/admin-dashboard.spec.ts`
- `makefiles/test.mk`

具体落地：

- 把 hotpost live URL 统一改成当前 Playwright 前端入口，去掉 `127.0.0.1` / `localhost` 差异
- `admin` 正式 E2E 回到更稳的 hand-crafted admin token 方案
- `make test-e2e` / `make test-admin-e2e` 的账号初始化改成 `创建 + 重置`

这一步的价值不是“测试通过更好看”，而是：

- 验收分终于不再被环境漂移污染

---

## 验证结果

### 页面级验证

- `cd frontend && npx vitest run src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/HotPostResultPage.surface.test.tsx src/pages/__tests__/AdminDashboardPage.test.tsx`
- 结果：`3 files passed / 13 tests passed`

### 构建验证

- `cd frontend && npm run build`
- 结果：通过

### Smoke E2E

- `cd frontend && npx playwright test e2e/product-polish-smoke.spec.ts --project=chromium --reporter=line --workers=1`
- 结果：`2 passed`

### 正式 E2E

- `make test-e2e`
- 结果：`21 passed`

---

## 当前判断

按现在的产品标准，我会把这套产品从 `92-93` 再往上调到约 `94-95`。

为什么这次能上这一档：

- 不是只顺了
- 是开始更像“成熟产品”
- 视觉语言终于不是默认后台/默认 SaaS
- 正式 E2E 也重新全绿，验收口径更硬

但还不能直接给 `98`，因为还剩最后几块明显差距：

- `InputPage / ProgressPage / Admin 子页面` 还没完全进入同一套高级视觉语言
- `AdminRoute / AdminLayout` 仍有旧世界样式和 emoji 导航
- 一些次级页面仍有明显“旧后台时代”UI
- 还没做最终一轮更严苛的浏览器截图级精品验收

---

## 下一步建议

直接开 `Phase 403`，只打最后一轮 `98 分冲刺包`：

1. 把 `InputPage / ProgressPage / AdminLayout / AdminRoute` 一起拉进新视觉系统
2. 清掉 admin 体系里残留的 emoji 和旧内联样式
3. 做桌面 + 移动端截图级精品验收
4. 再重打一轮产品分，看能不能从 `94-95` 冲到 `97-98`

---

## 本轮价值

这轮最值钱的，不是“又换了一套皮肤”。

真正的价值是：

- 这套产品终于开始有自己的视觉立场
- 验收结果也不再被测试世界和本地运行面噪音带偏

一句大白话收口：

- 现在它不只是能用、能判断
- 已经开始像一个该拿给真实用户看的成熟产品了
