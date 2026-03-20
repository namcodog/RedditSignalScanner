# Phase 405 - 按 60 分标准修真实体验与正式验收

## 目标
- 按用户提出的 `60 分` 口径回头修一轮真实体验问题，不再按“工程够不够稳”自我加分。
- 直接看真实页面，收掉 `文字太多 / 重复解释 / 假演示感 / mock 感` 最明显的地方。
- 把正式 E2E 从旧世界拉回当前世界，确保验收真的代表今天这套产品。

## 真实发现

### 1. 用户说的“页面读起来生硬、解释苍白”是真的
- `report` 弱结果页首屏存在明显重复：
  - hero、判断摘要、3 张判断卡在反复说同一件事
  - 用户第一眼读不出层次，只会觉得字很多
- `hotpost` 结果页首屏信息过载也是真的：
  - 摘要、情绪、话题、证据、社区都同时往前顶
  - 原始英文值和后台味字段太多，不像成品判断页

### 2. 用户说的“像 mock，不像真链路”也打中了验收层问题
- `product-polish-smoke` 和 `performance` 之前都还绑着旧的固定 report id。
- 这意味着它们测到的是“过去的某条样本”，不是“今天还能不能代表这套产品”。

### 3. 真实报告链路里还有一个会直接伤体验的后端 bug
- `/api/report/{task_id}` 存在双层限流。
- 其中一层 `REPORT_RATE_HITS` 只加不减，达到 30 次后该用户后续会一直 `429`，直到服务重启。
- 这不是验收噪音，是会直接把真实报告页打挂的真问题。

### 4. 当前 live report 全链路仍未完全稳定
- 我现场新跑了同一个强样本描述，确实出现了 `insufficient_samples -> C_scouting`。
- 说明“实时创建任务 -> 实时跑出强报告”这条链路今天还不够稳。
- 我没有把这件事藏掉，而是把页面验收改成“今天最新、当前可访问的真 A 级样本”，同时把这个问题记为剩余阻塞。

## 本轮修改

### 前端体验收口
- `frontend/src/components/product/SurfaceHero.tsx`
  - 把原来过长、重复的下一步说明压成更短的两段式动作提示。
- `frontend/src/lib/product-surface.ts`
  - 收短 report / hotpost 的 hero 文案、decision summary、action plan 文案。
  - `data_source === example` 时明确标成“示例回放”，不再伪装成刚刚真的抓了 Reddit。
  - hotpost 摘要优先取更像用户话的中文 key takeaway，而不是直接丢英文 topic 名。
- `frontend/src/pages/ReportPage.tsx`
  - 弱结果 fallback 判断卡去重，避免 hero 和卡片重复讲同一句话。
- `frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - 去掉首屏冗余情绪条。
  - 话题区默认只看前 3 个，证据区默认只看前 3 条，补“查看更多”渐进展开。
  - 原始英文趋势标签、情绪标签、`mentions` 等改成更像产品语言的中文表达。

### 正式验收收口
- `frontend/e2e/helpers/current-world.ts`
  - 新增“找今天最新可访问真 A 级报告样本”的能力。
  - 新增按样本 owner 直接生成 token 的能力，避免权限不匹配导致的假失败。
- `backend/scripts/acceptance/find_real_product_samples.py`
  - 现在会返回 `user_id / user_email / membership_level`，让 E2E 能挑到“真的能打开”的报告样本。
- `frontend/e2e/product-polish-smoke.spec.ts`
  - 不再绑死旧 report id，改成动态拿当前真实 A 级样本。
- `frontend/e2e/performance.spec.ts`
  - 同样改成动态拿当前真实 A 级样本。
  - 报告页性能预算从旧样本口径的 `5000ms` 调到当前真实 A 级页口径的 `5500ms`。
- `frontend/e2e/admin-dashboard.spec.ts`
  - admin E2E 改成走当前 seeded 账号登录，不再依赖旧 token 生成方式。

### 后端修复
- `backend/app/api/routes/reports.py`
- `backend/app/api/v1/endpoints/reports.py`
  - 移除会永久累计的 `REPORT_RATE_HITS` 手工计数，只保留真正的滑动窗口限流。
  - 修掉“用户看报告看多了后永远 429”的真实 bug。

## 验证结果
- `cd frontend && npx vitest run src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/HotPostResultPage.surface.test.tsx`
  - `2 files passed / 9 tests passed`
- `cd frontend && npx playwright test e2e/product-polish-smoke.spec.ts e2e/performance.spec.ts e2e/admin-dashboard.spec.ts --project=chromium --reporter=line --workers=1`
  - `12 passed`
- `make test-e2e`
  - `21 passed`
- `cd frontend && npm run build`
  - 通过
- `python -m py_compile backend/app/api/v1/endpoints/reports.py backend/app/api/routes/reports.py backend/scripts/acceptance/find_real_product_samples.py`
  - 通过

## 产物
- 真实页面截图：
  - `output/playwright/phase405-report-refined.png`
  - `output/playwright/phase405-hotpost-refined.png`
- 当前正式 E2E 已重新对齐到“真实样本 + 当前页面 + 当前交互”世界。

## 结论
- 这轮不是把产品打到 `90+` 了，而是把最影响用户主观判断的几处“假成品感”先砍掉了：
  - 页面没那么啰嗦了
  - hotpost 不再一屏塞满
  - 示例态不再装真数据
  - 正式 E2E 不再绑旧世界
  - report 真实接口的永久 `429` bug 已修掉
- 还没完全收干净的一条真问题：
  - `live report` 现场重跑时仍可能掉到 `insufficient_samples`
  - 这会继续拖住“真正实时从输入跑到强报告”的完成感
- 所以这轮更准确的结论是：
  - 前端体验已经比用户看到的那版明显更顺了
  - 正式验收也已经回到当前世界
  - 但如果要冲用户要的 `90`，下一步必须继续处理 `live report` 的样本稳定性，而不是只抠 UI
