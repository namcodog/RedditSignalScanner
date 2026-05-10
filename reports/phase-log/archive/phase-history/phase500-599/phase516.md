# Phase 516 - Readiness First：先体检，再提问

时间：2026-03-27

## 本轮目标

回答一个更底层的问题：

为什么我们现在验证 8 大领域时，总有“像开盲盒”的感觉？

并把后续计划从“继续换题干”收口成“先做数据准备度体检，再决定问什么”。

## 发现的问题

### 1. 当前 8 领域矩阵，本质上还是固定题干直冲 live

- `backend/scripts/acceptance/run_warzone_live_matrix.py`
  - 现在仍使用 `DEFAULT_WARZONE_CASES`
  - 也就是每个领域直接绑定一条固定问题描述，先跑 live，再看结果

### 2. 验收只看结果，不看事前准备度

- `backend/scripts/acceptance/validate_warzone_live_matrix.py`
  - 只校验：
    - tier
    - 痛点标题
    - 机会标题
    - 社区标题
    - result_url
  - 不校验：
    - 当前 Dev 库对这个领域到底有没有足够社区
    - 有没有足够帖子/评论
    - 有没有足够 clickable Reddit evidence 潜力

### 3. 仓库里其实已有“体检能力”，但没接进主流程

现成脚本：

- `backend/scripts/acceptance/find_real_product_samples.py`
- `backend/scripts/report/t1_data_audit.py`

问题不是没有工具，而是它们还没被放到 live 验收前面。

### 4. Dev 库的真实状态，确实支持“不能再盲跑”的判断

实查结果：

- `community_pool` 当前活跃社区只有 `r/test`
- `community_pool.vertical` 基本不可用，不能直接作为 8 领域 readiness 真相源

但另一方面，`posts_raw` 近 180 天里其实已有真实分布：

- `r/entrepreneur` 1347
- `r/startups` 1185
- `r/ecommerce` 270
- `r/artificial` 265
- `r/saas` 254
- `r/multitools` 248
- `r/bitcoin` 241
- `r/cryptocurrency` 240
- `r/onebag` 201
- `r/edcexchange` 200
- `r/ultralight` 188
- `r/babybumps` 99
- `r/beyondthebump` 98
- `r/daddit` 97
- `r/parenting` 79
- `r/newparents` 60

这说明当前真实情况是：

- 原始帖子有一些
- 但 Dev 里的“领域脑图 / 社区池 / vertical 映射”还没建好

所以如果继续靠“换一个问题描述”来验证系统，很容易把“底盘还没准备好”误以为“题没问对”。

## 结论

当前主问题应升级为：

### 不是“再想一条更聪明的问题描述”

而是：

### `Readiness First`

也就是：

1. 先做领域准备度体检
2. 再决定当前该验证哪个领域、问什么子题
3. 最后才跑 open-question live final

## 新的落地方案

### Step 1：做 `vertical_readiness_scan`

不再依赖当前 Dev 的 `community_pool.vertical`，而是基于：

- `posts_raw`
- `comments`
- `warzones.yaml`
- 已验证通过的 `open_topic_route / evidence purity` 合同

先产出 8 领域 readiness 卡：

- 可用 subreddit 数
- 近 90 / 180 天帖子量
- 评论量
- 去噪后 on-topic 样本量
- clickable Reddit URL 潜力
- 是否值得直接跑 `A_full` 验收

### Step 2：从 readiness 过线领域里挑 probe

不再固定一条题干硬冲。

改成：

- 每个领域先选一个“当前最像真样本”的子方向
- 再生成同 intent 的不同措辞 probe

这样能避免：

- 总用同一句描述
- 恰好撞上一个没有数据的子题

### Step 3：把 live 验收改成两段式

第一段：

- readiness preflight

第二段：

- open-question live final

只有 readiness 过线的领域，才进第二段。

没过线时，系统要明确告诉我们：

- 现在是数据底盘不够
- 还是社区池没建好
- 还是补量链没接上

## 下一条推荐验证领域

如果下一条要继续横向验证，而又不想重复 `Family / EDC / Ecommerce`：

### 优先建议：`Minimal_Outdoor`

理由：

- 当前 `posts_raw` 已有明显相关社区：
  - `r/onebag`
  - `r/ultralight`
- 题材边界比 `AI_Workflow` 更干净
- 比 `Food_Coffee_Lifestyle` 更像当前已有底盘支撑

## 价值

这轮最重要的不是又跑通一条题，而是把判断从：

- “是不是题没问好”

升级成：

- “系统当前有没有准备好回答这个领域”

这一步会直接决定后面 `crypto / SaaS / 新领域` 接进来时，系统是不是还要继续靠运气。
