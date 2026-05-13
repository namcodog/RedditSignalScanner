# Phase 394 - 真实样本成品验收

## 本轮目标

不用 mock，不看想象中的页面节奏，直接拿真实 Dev 样本验：

1. 强结果第一页是不是足够硬
2. 弱结果第一页是不是还能顺
3. hotpost 快扫结果是不是还能保持“先判断、再行动”的节奏

这轮重点不是再补一层文案，而是看产品有没有在真实结果上露出破绽。

## 完成情况

### 1. 用真实样本把强 / 弱 report 重新拉出来验

- 重新扫描 Dev 库里的真实样本，确认当前可用的报告样本：
  - 强结果：`0babc5db-9ad1-4a98-88b1-9fa6705fccf5`
  - 弱结果：`dd6ab502-8d99-48cc-889f-057aef534c29`
- 真实 payload 验证结果：
  - 强结果是 `A_full`
  - 弱结果是 `C_scouting`
  - 弱结果被正确标记为 `insufficient_samples`

这说明我们这轮验收看的不是“最好看的样子”，而是真实会遇到的两端样本。

### 2. 热帖旧样本失效，改成现场重跑真实查询

- 旧 hotpost result id 仍在 Dev 记录里，但 `/api/hotpost/result/{id}` 已经返回 `404`
- 这不是产品页的问题，而是旧的结果缓存已经不在了
- 所以这轮不再拿旧缓存假装验收，而是直接发起一条新的真实查询：
  - query: `tiktok shop sellers`
  - mode: `trending`
  - 新 query id：`517bbfdf-d2a0-46ec-af53-c90d0d6b0c26`

这一步很关键，因为它把 hotpost 验收重新拉回真实链路，而不是靠历史缓存撑着。

### 3. 真实样本真的揪出了一个产品缺陷

强结果 report 在真实 payload 上暴露出一个很伤产品感的问题：

- 首屏“最值得追的机会”原来会冒出一句断裂的话：
  - `need to connect my`

这不是小瑕疵，是会直接削掉价值感的缺陷。用户第一眼看到这里，会立刻觉得结论不够硬。

根因不是没有数据，而是我们之前优先取了太原始、太碎的机会标题。

### 4. 已把机会标题改成优先取结构化价值表达

本轮修复后，report 首屏不再优先拿碎片化 raw title，而改成优先取更像产品判断的话：

优先顺序现在是：

1. `report_structured.opportunities[0].title`
2. `report_structured.opportunities[0].product_positioning`
3. `report.report.opportunities[0].description`
4. `report.report.opportunities[0].text`
5. `report.report.opportunities[0].title`
6. `report.report.executive_summary.top_opportunity`

修完后，同一个真实强样本首屏变成：

- `一键抓 Amazon/Etsy/Shopify/TikTok 回款，费率透明不漏扣`

这才更接近“用户看到就知道值不值得继续做”的状态。

### 5. 三类真实结果现在的产品表现

- 强结果 report：
  - 首屏判断已经更硬，价值点不再断裂
- 弱结果 report：
  - 节奏是顺的，能自然落到“先决定要不要放大”
- live hotpost：
  - 节奏是对的，已经能稳定说清“这波值得马上继续追”

## 验证结果

已通过：

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/HotPostResultPage.surface.test.tsx \
  src/pages/__tests__/AdminDashboardPage.test.tsx
```

结果：
- `3 files passed / 11 tests passed`

已通过：

```bash
cd frontend && npm run build
```

## 关键改动文件

- `frontend/src/lib/product-surface.ts`
- `frontend/src/pages/__tests__/ReportPage.test.tsx`

## 产品判断

这轮最重要的成果，不是“又验了一次”，而是：

- 我们开始真的用真实样本打产品
- 真实样本真的打出了一个会伤价值感的问题
- 这个问题已经被修掉

这说明第四轮已经不在“做得像不像”阶段，而是在“真实使用下能不能站得住”阶段。

## 遗留提醒

当前还有三条提醒，不阻塞这轮验收结论：

- `baseline-browser-mapping` 版本过期 warning
- 现有 `React.jsx type is invalid` warning，仍指向 `index.tsx`
- hotpost 历史结果 id 不能再作为稳定验收样本，后续验收必须走“现场重跑真实查询”

## 下一步

进入 `Phase 395`：

- 做第四轮总复盘
- 按真实样本验收结果重新打产品分
- 整理从 88-90 分继续冲到 95 分的最后补刀清单
