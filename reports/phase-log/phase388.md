# Phase 388 - 第四阶段产品抛光第四包：只用真实 Dev 页面做价值验收

## 1. 发现了什么？

这一步不再看 mock 页面测试，而是直接用 **真实 Dev 数据 + 真实登录用户页面** 验收第四阶段第三包的价值交付。

这次先照出来的真实情况有 3 条：

1. **弱报告样本的动作链是通的**
   - 真实样本：`dd6ab502-8d99-48cc-889f-057aef534c29`
   - 页面能明确给出：
     - `扩大范围重新分析`
     - `逐维探索`
     - `分析其他方向`
   - 点 `扩大范围重新分析` 后，用户会被直接带回输入页，并且自动带回上一轮的产品描述

2. **强 hotpost 样本的动作链是通的**
   - 当前登录用户可访问样本：`89bd57f4-a19c-4b84-927a-1f6a68d07662`
   - 页面能明确给出：
     - `生成深度报告`
     - `先看关键证据`
     - `换关键词重扫`
   - 点 `换关键词重扫` 后，用户会回到 hotpost 搜索页，关键词自动带回
   - 点 `先看关键证据` 后，页面会直接滚到 `热门讨论 (Top Evidence)` 区

3. **真实验收里还有两个不能绕开的真问题**
   - 旧 hotpost 样本 `565e2f36-b95d-4948-afa1-0486fd97c559` 对当前用户返回 `404`
   - 新 scouting 报告样本 `fc00df44-7027-4ecc-86ed-3c815991f3a1` 对当前用户返回 `403`

大白话说：

- 页面本身的 CTA 交付已经站住了
- 但真实验收不能乱拿样本
- **以后验收必须只看“当前登录用户真能打开的 Dev 样本”**

## 2. 是否需要修复？

需要，而且这一包已经修完的是：

1. **验收口径**
   - 不再拿 mock 数据证明产品有价值
   - 改成只用真实 Dev 数据和真实页面证明

2. **样本筛选口径**
   - 不再只看数据库里“存在”
   - 改成同时满足：
     - Dev 库存在
     - 当前用户可访问
     - 页面真实能打开

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

这次没有再改主产品代码，主动作是把真实验收链补齐并把规则钉死。

### 3.1 真实样本筛选

使用：

- [find_real_product_samples.py](/Users/hujia/Desktop/RedditSignalScanner/backend/scripts/acceptance/find_real_product_samples.py)

先筛全局样本，再用当前登录用户 `user_id` 重新筛一遍：

- 当前用户 `user_id`：
  - `58e76e63-3531-4572-9336-90313d3063df`

这样确认下来：

- 真实可用强报告样本：
  - `0babc5db-9ad1-4a98-88b1-9fa6705fccf5`
- 真实可用弱报告样本：
  - `dd6ab502-8d99-48cc-889f-057aef534c29`
- 真实可用 hotpost 样本：
  - `89bd57f4-a19c-4b84-927a-1f6a68d07662`

### 3.2 弱报告价值动作验收

真实页面：

- [ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)
- [InputPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/InputPage.tsx)

验收结果：

- 报告页首屏明确告诉用户：
  - 先判断方向
  - 下一步把范围放大
- 点 `扩大范围重新分析`
  - 真跳回首页 `/`
  - 真带回原产品描述
  - 真出现提示：
    - `已带回你刚才看的方向`

### 3.3 强报告价值首屏验收

真实页面：

- [ReportPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/ReportPage.tsx)

验收样本：

- `0babc5db-9ad1-4a98-88b1-9fa6705fccf5`

验收结果：

- 首屏不是材料堆砌，而是先给：
  - `这份结果已经可以直接看结论`
  - 为什么值得继续看
  - 下一步动作
- 深读入口明确下沉为：
  - `看完整报告`
  - `逐维探索`

### 3.4 hotpost 价值动作验收

真实页面：

- [HotPostResultPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/HotPostResultPage.tsx)
- [HotPostSearchPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/hotpost/HotPostSearchPage.tsx)

验收样本：

- `89bd57f4-a19c-4b84-927a-1f6a68d07662`

验收结果：

- 首屏明确告诉用户：
  - `这波已经值得现在继续追`
  - 为什么
  - 下一步怎么做
- 点 `换关键词重扫`
  - 真跳回 `/hotpost`
  - 真带回 query：`tiktok shop sellers`
  - 真出现提示：
    - `已带回你刚才那次快扫`
- 点 `先看关键证据`
  - 页面真滚到：
    - `热门讨论 (Top Evidence)`

## 4. 验证结果

### 4.1 真实样本筛选

```bash
cd backend && python scripts/acceptance/find_real_product_samples.py
cd backend && python scripts/acceptance/find_real_product_samples.py --user-id 58e76e63-3531-4572-9336-90313d3063df --report-limit 5 --hotpost-limit 5
```

结果：

- 成功筛出当前用户真实可访问样本

### 4.2 真实页面验收

通过浏览器真实验收确认：

1. 弱报告页 CTA 真能把用户带回输入页
2. 强报告页首屏真能先给价值结论
3. hotpost 真能：
   - 回搜索页并带回关键词
   - 直跳关键证据区

### 4.3 前端构建

```bash
cd frontend && npm run build
```

结果：

- 构建通过

### 4.4 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 下一步系统性的计划是什么？

第四阶段接下来不再纠结“状态怎么讲”，而是继续只盯两件事：

1. **价值首屏还能不能再更硬**
   - 报告页首屏的结论、理由、动作还可以继续压缩得更利落
   - hotpost 的“值得追”判断还能不能更像产品判断页

2. **真实样本验收流程固定化**
   - 后面所有产品抛光验收，都只用：
     - Dev 库真实样本
     - 当前用户可访问样本
     - 真实浏览器动作链

## 6. 这次执行的价值是什么？达到了什么目的？

这一步最重要的，不是多改了几个页面，而是把验收标准彻底拉正了：

- **以后不再用 mock 数据证明产品有价值**
- **只用真实 Dev 页面证明用户第一眼能不能感受到价值**

大白话说：

- 弱结果，我们已经证明用户会被自然带回下一步
- 强结果，我们已经证明用户第一眼就能拿到结论、原因和动作
- hotpost，我们已经证明它不只是“看结果”，而是“能继续行动”

一句话收口：

- **这一步把第四阶段的验收口径真正收成了“只看真实用户页面”，不是只看测试文件。**
