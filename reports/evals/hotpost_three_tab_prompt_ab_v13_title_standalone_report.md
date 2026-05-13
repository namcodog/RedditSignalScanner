# Hotpost 三 Tab Prompt A/B v13 title-standalone 小样本报告

这份报告只比较 title 是否能脱离 summary_line 独立看懂，不代表候选质量、发布 gate 或小程序 UI 变更。

## 总览

- `breakdown`: baseline 2/2 成功，variant 2/2 成功
- `hot`: baseline 2/2 成功，variant 2/2 成功
- `signal`: baseline 2/2 成功，variant 2/2 成功

## breakdown

### card-group-ai-automation-1de9c05516

- model: `v12 baseline vs v13 title-standalone`
- summary_line: 有用户展示800行提示词工程，但围观者没被行数唬住，反而先质疑定义和实际效果。
- issues before: 1
- issues after: 0

- A title: 写了800行提示词，评论区却在问：这到底是什么？
- B title: 800行提示词被评论区追问定义和实际用途

### card-group-ai-automation-3a7f66c166

- model: `v12 baseline vs v13 title-standalone`
- summary_line: 开发者发现高分模型可能被服务商量化变笨，选模型时先问量化情况而非看跑分。
- issues before: 0
- issues after: 0

- A title: 开源模型跑分高没用，先问服务商有没有偷偷量化
- B title: 开源模型跑分高也可能变笨，因为服务商可能偷偷量化


## hot

### card-cand-ai-automation-1rweoq5-validate

- model: `v12 baseline vs v13 title-standalone`
- summary_line: 帖子标题说‘人类编程时代结束’，但最高赞评论是‘感谢你们的免费训练数据’，讽刺的是开发者自己养大了取代自己的工具。
- issues before: 0
- issues after: 0

- A title: 程序员自嘲：我们免费交出去的代码，正在被 AI 拿去抢饭碗
- B title: 程序员免费贡献的代码，正被 AI 拿去训练并可能取代他们

### card-cand-ai-automation-1saaqfv-validate

- model: `v12 baseline vs v13 title-standalone`
- summary_line: 全自动方案实际用起来基本不行，边界情况会耗光开发时间。
- issues before: 0
- issues after: 0

- A title: 全自动 AI 代理行不通，开发者转向“智能助手”
- B title: 全自动 AI 代理难落地，开发者转向受控智能助手


## signal

### card-cand-ai-automation-1s6pkg3-validate

- model: `v12 baseline vs v13 title-standalone`
- summary_line: 判断标准从‘提示词写得好不好’，转成‘工具能不能接入真实代码和数据’。
- issues before: 0
- issues after: 0

- A title: AI 做 SEO，光写提示词不够；还得看网站代码和搜索数据
- B title: AI 做 SEO，光写提示词不够；还得看网站代码和搜索数据

### card-cand-ai-automation-1saabgz-validate

- model: `v12 baseline vs v13 title-standalone`
- summary_line: 有用户已经把账摊开：花大量时间调提示词，加上最贵模型的持续账单，可能比自己干还贵。
- issues before: 0
- issues after: 0

- A title: 想用 AI 自动干活，先算清调教时间和模型账单
- B title: 用 AI 自动干活前，先算调提示词时间和 API 账单
