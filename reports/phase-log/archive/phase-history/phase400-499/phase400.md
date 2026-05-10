# Phase 400 - 完整正式 E2E 验收与当前分数校准

## 本轮目标

用户这轮要求的不只是 smoke，而是：

- 把仓库里真正该算分的正式 E2E 套件跑完
- 区分“产品真回退”和“历史测试已过时”
- 基于完整 E2E 结果，重新判断当前到底是多少分

本轮纳入的正式 E2E 范围是：

- `e2e/user-journey.spec.ts`
- `e2e/report-page-simple.spec.ts`
- `e2e/product-polish-smoke.spec.ts`
- `e2e/admin-metrics-tab.spec.ts`
- `e2e/performance.spec.ts`

明确排除：

- `*debug.spec.ts`

因为这些是调试探针，不适合直接算产品验收分。

## 完整正式 E2E 结果

已执行：

```bash
cd frontend && npx playwright test \
  e2e/user-journey.spec.ts \
  e2e/report-page-simple.spec.ts \
  e2e/product-polish-smoke.spec.ts \
  e2e/admin-metrics-tab.spec.ts \
  e2e/performance.spec.ts \
  --project=chromium \
  --reporter=line \
  --workers=1
```

结果：

- `35 tests`
- `9 passed`
- `15 failed`
- `2 skipped`
- `9 did not run`

这说明一个很重要的事实：

- 现在不能再按“页面体感 93”直接给阶段分
- 必须把“正式 E2E 套件还没站住”算进当前验收分

## 失败结构拆解

### 1. `admin-metrics-tab.spec.ts`：8 条全挂

这一组失败非常集中：

- 还在找旧 Admin 页的 4 个 Tab：
  - `社区验收`
  - `算法验收`
  - `用户反馈`
  - `数据质量`
- 还在等旧的 `/api/metrics` 请求

而当前 Admin 已经被收成：

- `系统控制面`
- `今天先看什么`
- `今天机器稳不稳`

所以这 8 条更像：

- **正式 E2E 套件已经落后于现有产品结构**

不是这轮产品打磨把 Admin 打坏了，而是测试合同没跟上。

### 2. `performance.spec.ts`：4 条失败，分成两类

#### A. 陈旧选择器

- 还在找首页旧的 `示例 1` 按钮
- 还在找旧的字数统计选择器

这两条属于：

- **测试仍在对旧首页结构说话**

#### B. 资源预算阈值真实超标

两条资源数量断言失败：

- 首页资源数：`86 > 50`
- 报告页资源数：`85 > 50`

但同一组里，加载时间和 FCP 都是过的：

- 首页加载约 `138ms`
- 报告页加载约 `85ms`

所以这里的结论不是“性能很差”，而是：

- **用户体感性能还行**
- **但资源预算门禁口径没有达标**

这两条不能完全算成陈旧测试，它们暴露的是一条真实优化线索。

### 3. `report-page-simple.spec.ts`：2 条失败

这组还在期待旧错误页标题：

- `获取报告失败`

而当前产品已经换成更像产品的错误状态表达。

所以这两条更像：

- **错误态产品化之后，E2E 文案断言没有同步**

### 4. `user-journey.spec.ts`：核心链路存在多处旧合同与真风险混合

由于这个文件是 `serial`，第一条挂了后面会停，所以我又补跑了多轮 targeted rerun，把后段链路补齐。

补跑后确认至少有 5 类阻塞：

#### A. 注册弹窗提交按钮选择器冲突

- `注册` 按钮命中两个元素，触发 strict mode violation

#### B. 登录弹窗提交按钮选择器冲突

- `登录` 按钮同样命中两个元素

#### C. 任务提交流程还在找旧字数统计节点

- 旧断言找不到当前输入页的字数统计展示

#### D. SSE 阶段等待策略偏旧

- 5 秒内没等到它预期的旧 heading / progress 结构

#### E. 报告展示测试存在 timeout 合同问题

- 测试内部写了 `waitForURL(..., timeout: 300000)`
- 但整条 test 仍受默认 `30000ms` 总超时限制

所以它卡死在：

- 还停留在 `/progress/...`

这条目前不能直接下结论说“报告永远出不来”，只能说：

- **当前 E2E 合同和真实任务耗时模型并不匹配**

### 5. `product-polish-smoke.spec.ts`：2 条都通过

这组在完整套件里仍然稳：

- `report` 真实样本页：通过
- `hotpost` live 结果页：通过

它依然是目前最贴近这轮产品打磨目标的真实主链路 E2E。

## 额外补跑结果

为了补掉 `serial` 造成的“未运行”，本轮还执行了：

```bash
cd frontend && npx playwright test e2e/user-journey.spec.ts --project=chromium --reporter=line --workers=1 --grep-invert "应该成功注册新用户"
cd frontend && npx playwright test e2e/user-journey.spec.ts --project=chromium --reporter=line --workers=1 --grep "2\\. 用户登录流程|3\\. 任务提交流程|4\\. SSE 实时进度测试|5\\. 报告展示测试"
cd frontend && npx playwright test e2e/user-journey.spec.ts --project=chromium --reporter=line --workers=1 --grep "3\\. 任务提交流程|4\\. SSE 实时进度测试|5\\. 报告展示测试"
cd frontend && npx playwright test e2e/user-journey.spec.ts --project=chromium --reporter=line --workers=1 --grep "4\\. SSE 实时进度测试|5\\. 报告展示测试"
cd frontend && npx playwright test e2e/user-journey.spec.ts --project=chromium --reporter=line --workers=1 --grep "5\\. 报告展示测试"
```

目的不是刷通过率，而是把：

- 登录
- 提任务
- SSE
- 报告页

这些后段链路到底卡在哪里看清楚。

## 当前分数怎么改

现在我会给两套口径：

### 1. 页面产品体感分

- `93`

因为页面本身、主链路表达、真实 smoke E2E 仍然站得住。

### 2. 完整正式 E2E 验收分

- `89`

因为完整正式套件现在还远没绿：

- 35 条里只有 9 条直接通过
- 而且失败里既有陈旧用例，也有真实验收链没收紧的问题

## 如果只能给一个现在的分数

我这次会收成：

- `89`

原因很简单：

- 你说得对，**要把完整 E2E 验证算进去**
- 那就不能还按只看 smoke 时的 `93`
- 必须回到更严格的验收口径

## 当前判断

一句大白话总结：

- 产品页面本身已经接近 `93`
- 但完整正式 E2E 验收只够 `89`
- 所以现在不能说“已经快到 95”

真正把分拉下来的，不是首页不行，而是：

- 正式 E2E 套件和当前产品已经明显脱节
- 核心用户旅程里仍有几条真链路没有被完整、稳定地验证穿

## 下一步

如果继续冲，下一阶段不要再只做页面 polish，而要先收两件事：

1. **正式 E2E 套件对齐当前产品**
   - 清掉过时选择器
   - 更新旧文案断言
   - 修正 serial 文件的阻断式结构
   - 调整不合理 timeout

2. **把真实链路再打穿**
   - 登录 / 注册弹窗提交流程
   - 输入页提交到进度页
   - 进度页到报告页
   - Admin 当前 IA 的正式 E2E

等这两件事做完，再谈能不能回到 `93+`，再冲 `95` 才有意义。
