# Phase 396 - 冲 95 分最后补刀第一刀：中段信息密度收紧

## 本轮目标

把 `report` 和 `hotpost` 中段从“继续讲信息”再往前推一格，收成更像：

- 继续推动判断
- 继续帮助拍板
- 而不是让用户自己再整理一次

这轮一开始只做第一刀，但现在已经把这包里剩下两条也补上了：

- 真实浏览器验收动作
- hotpost live 验收入口

## 完成情况

### 1. report 中段开始更像“继续判断”，不再像“继续读材料”

这轮把 report 欢迎页中段收了两层：

- 增加中段引导：
  - `继续判断前，先确认这三件事`
- 补一句更短的节奏提示：
  - `别一口气读完整页。先看趋势、抱怨、机会，够了再往下深挖。`

同时把三张判断卡从“多条细节堆叠”收成“结论 + 一句最关键说明”，减少用户第一屏后的信息负担。

另外，把深读入口说明压成更直接的话：

- `别全读。先挑一块最影响你拍板的内容往下拆，确认后再看完整报告。`

这会让 report 的中段更像“继续判断的路标”，而不是“继续看材料的入口”。

### 2. hotpost 中段开始更像“快扫路径”，不再像“信息块堆叠”

这轮把 hotpost 的中段改成明确三步：

- `1 先看摘要`
- `2 再扫证据`
- `3 最后盯社区`

原来的标题 `继续拆这波判断` 也收成：

- `先按这三步拆判断`

并且把原来偏后台/偏英文的区块标题收成更像产品动作的话：

- `热门话题 (Trending Topics)` → `这波最热的三个话题`
- `核心痛点 (Pain Points)` → `用户到底在骂什么`
- `未满足需求 (Unmet Needs)` → `用户现在缺什么`
- `目标人群` → `谁最着急`
- `现有工具评价` → `用户现在拿什么凑合`

这一步的价值，不是换字，而是让用户更容易顺着页面自然往下走。

### 3. 真实浏览器验收动作已经固定下来

这轮没有再回去碰那条被 Chrome 会话卡住的 MCP 入口，而是直接用仓库里现成的 Playwright 跑 headless 浏览器验收。

真实页面验证结果：

- report 真页面命中：
  - `继续判断前，先确认这三件事`
  - `别一口气读完整页。先看趋势、抱怨、机会，够了再往下深挖。`
  - `别全读。先挑一块最影响你拍板的内容往下拆，确认后再看完整报告。`
- hotpost 真页面命中：
  - `先按这三步拆判断`
  - `1 先看摘要`
  - `2 再扫证据`
  - `3 最后盯社区`
  - `这波主要出在哪些社区`

浏览器截图已落到：

- `output/playwright/phase396-browser/report-phase396-validated.png`
- `output/playwright/phase396-browser/hotpost-phase396-validated.png`

### 4. hotpost live 验收入口已经固化成脚本

为了不再依赖会过期的历史 query id，这轮新增了：

- `backend/scripts/acceptance/run_live_hotpost_acceptance.py`

这个脚本会：

1. 发起一条新的 hotpost 查询
2. 轮询直到结果完成
3. 输出新的 `query_id`、摘要和结果页 URL

本轮实测输出了新的 live query：

- `52a0cf9b-3624-49ca-8f5b-0d55fc27de9b`

这意味着 hotpost 的真实验收入口，已经从“手工办法”变成了“正式工具”。

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

已通过：

```bash
python backend/scripts/acceptance/run_live_hotpost_acceptance.py
python -m py_compile backend/scripts/acceptance/run_live_hotpost_acceptance.py
```

浏览器验收命中结果：

```json
{
  "report": {
    "hasMidHeading": 1,
    "hasMidDescription": 1,
    "hasActionCopy": 1
  },
  "hotpost": {
    "hasMidHeading": 1,
    "hasStep1": 1,
    "hasStep2": 1,
    "hasStep3": 1,
    "hasCommunityHeading": 1
  }
}
```

## 关键改动文件

- `frontend/src/lib/product-surface.ts`
- `frontend/src/pages/ReportPage.tsx`
- `frontend/src/pages/hotpost/HotPostResultPage.tsx`
- `frontend/src/pages/__tests__/ReportPage.test.tsx`
- `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`
- `backend/scripts/acceptance/run_live_hotpost_acceptance.py`

## 当前判断

这轮做完后，产品不是一下子到 95 分了，但中段明显更顺了。

如果 `Phase 395` 时大概在 `89` 左右，这包做完后，我会把当前体感上调到：

- `91`

原因很简单：

- 首屏已经会打人
- 现在中段也开始会带路

这会明显减少“第一页很好，往下又开始像看材料”的掉分感。

## 阻塞与提醒

### 当前仍存在的非阻塞提醒

- `baseline-browser-mapping` 版本过期 warning
- 现有 `React.jsx type is invalid` warning，仍指向 `index.tsx`
- Playwright MCP / skill CLI 在当前机器上仍不稳定，但仓库内的 headless Playwright 已可作为正式验收替代方案

## 下一步

进入下一轮 `Phase 397`：

1. 只做最后一层精品化微调
2. 重点盯加载过渡、模块主次、视觉手感
3. 再做一次最终重打分，判断能不能从 `91` 往 `93-95` 冲
