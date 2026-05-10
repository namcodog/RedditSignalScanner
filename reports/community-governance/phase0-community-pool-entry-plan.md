# Phase 0 社区池只读入池方案

日期：2026-05-07

## 定稿口径

Phase 0 的目标是完成社区池治理，不是砍社区。

- `入池` = 进入系统学习、采集、分析和证据积累范围。
- `入池` 不等于高频采集、不等于高权重、不等于自动发布。
- 泛社区可以入池，但必须设 cap，不能打满默认采集面。
- 长尾社区是重点资产，按活跃度、帖子质量、垂直密度和可学习性判断。
- Hotpost / 小程序没发卡不能作为降级或删除理由。

## 当前盘面

- 社区资产总数：`264`
- 已有证据社区：`108` = `promote_candidate 69 + keep_active 39`
- 补证据社区：`31` = `needs_evidence`
- 旧池待复查资产：`115` = `stale_review`
- 暂不作为第一轮扩充对象：`10` = `observation_queue`

## 108 个已有证据社区的处理结果

| 结果 | 数量 |
|---|---:|
| 建议补入 pool | 69 |
| 保持在 pool | 39 |

| 社区角色 | 数量 |
|---|---:|
| 长尾垂直社区 | 36 |
| 泛社区 / 热点入口 | 27 |
| AI 工具链 / 工作流社区 | 27 |
| 平台 / 卖家 / 增长操作社区 | 17 |
| AI 工具链（配置冲突待确认） | 1 |

## 只读入池明细

| 社区 | 当前状态 | 入池处理 | 社区角色 | 使用策略 | 卡数 | supply | discovered | 样例 |
|---|---|---|---|---|---:|---|---|---|
| r/ClaudeCode | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 30 | Y |  | Claude Code 提5小时配额引焦虑：更快撞上周上限 |
| r/LLM | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 10 | Y |  | LLM 做 OCR 被质疑大材小用，但雇主只看结果，专用模型未必是首选 |
| r/cursor | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 5 | Y |  | Cursor 用户遇到 AI 处理复杂项目失败时，社区引导先自查代码结构，以‘10 个文件+外部数据库’作为代码混乱的硬指标 |
| r/ExperiencedDevs | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 4 | Y |  | 资深开发者对用 AI 写代码却无好奇心的新人感到疲惫，开始用“不是我的猴子我不操心”来放弃指导 |
| r/MachineLearning | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 4 | Y |  | LLM OCR 跑分帖火了：便宜旧模型常赢，但测试没算开源模型 |
| r/codex | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 3 | N |  | AI 一进代码审查，团队最怕的是谁也说不清它改了什么 |
| r/managers | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 3 | N |  | 行动项写出来没人认领，不是记录不清，是第一步没人敢接 |
| r/Notion | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 3 | N | pending | 很多用户不用 AI 整理资料，不是怕它乱，是怕来源链一断就回不去了 |
| r/agi | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | N |  | AGI 社区用户拒绝阅读 AI 生成文章，嘲讽它是泔水 |
| r/ChatGPTCoding | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | Y |  | 开发者社区集体醒悟：死磕全自动 AI 智能体在生产环境里就是个坑，真干活还得把 LLM 当听指令的聪明工具用 |
| r/claudeskills | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | Y |  | 选 AI SEO 工具，先问能不能接入你的代码库和 90 天数据 |
| r/ContentCreators | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | N |  | AI 让你发得更快，但内容开始像从一个模子里刻出来的 |
| r/OpenWebUI | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | Y |  | Open WebUI iOS 新用户第一问：支持 Siri 吗？ |
| r/perplexity_ai | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | Y |  | 研究者、分析者等用户拒绝 AI 总结，因为怕丢掉从原始证据中形成独立判断的控制权 |
| r/PKMS | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | N |  | 很多用户不用 AI 整理资料，不是怕它乱，是怕来源链一断就回不去了 |
| r/programming | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | N |  | AI 一进代码审查，团队最怕的是谁也说不清它改了什么 |
| r/research | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | N |  | 研究者、分析者等用户拒绝 AI 总结，因为怕丢掉从原始证据中形成独立判断的控制权 |
| r/vibecoding | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | Y | pending | 500个 Vibe Coding 工具清单引发质疑：开发者要能管大项目的工具，而非又一个 GitHub 大杂烩 |
| r/writing | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 2 | N |  | AI 让你发得更快，但内容开始像从一个模子里刻出来的 |
| r/claude | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 1 | Y | pending | Reddit 网友发现 Anthropic 只发布 Claude Mythos Preview 跑分，没放出可测试模型 |
| r/comfyui | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 1 | Y |  | ComfyUI 用户在 LTX-2.3 演示帖下提问：SI2V 和 I2V 有什么区别？ |
| r/ObsidianMD | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 1 | N | pending | 很多用户不用 AI 整理资料，不是怕它乱，是怕来源链一断就回不去了 |
| r/OpenSourceAI | promote_candidate | 建议补入 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 1 | Y |  | 开源社区讨论分布式训练，现在先算带宽账，不再只畅想算力聚合 |
| r/AI_Agents | promote_candidate | 建议补入 pool | AI 工具链（配置冲突待确认） | 入池前确认旧 blacklist 字段；确认后按 AI 工具链限额使用 | 11 | Y |  | 开发者排查 Agent 生产故障，重点从模型能力转向状态同步和上下文腐烂 |
| r/EntrepreneurRideAlong | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 4 | Y |  | 传统羊毛衫太厚太重，城市室内穿会热到融化，耐用反而成了负担 |
| r/b2bmarketing | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 3 | Y |  | B2B 运营发现 SEO 和广告用户意图不同，共用落地页导致转化差 |
| r/sales | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 3 | Y |  | 销售用 AI 克隆自己和团队，把 CRM 管理等日常重复工作全自动化 |
| r/customersupport | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 2 | N |  | 客服转单后背景丢失，客户被迫重复说明，比解决技术问题更耗时 |
| r/Emailmarketing | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 2 | Y |  | 博客主写千篇没流量、邮件营销者洗了列表还发不进，问题都出在底层：谷歌信不信任你，联系人还活不活跃 |
| r/helpdesk | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 2 | N |  | 客服转单后背景丢失，客户被迫重复说明，比解决技术问题更耗时 |
| r/revops | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 2 | N |  | 销售会后跟进动作总丢失：不是忘了做，而是做了也像没做 |
| r/sysadmin | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 2 | N |  | 客服转单后背景丢失，客户被迫重复说明，比解决技术问题更耗时 |
| r/AskMarketing | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 1 | Y |  | 营销人发现：Google 排名靠前，AI 回答里却可能完全没有你 |
| r/Blogging | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 1 | Y |  | 博客主写千篇没流量、邮件营销者洗了列表还发不进，问题都出在底层：谷歌信不信任你，联系人还活不活跃 |
| r/consulting | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 1 | Y |  | 客户嘴上要 AI Agent，实际要干净数据流，硬上 AI 给烂数据打补丁是伪转型 |
| r/sidehustle | promote_candidate | 建议补入 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 1 | Y |  | 做零售套利的人，现在先找本地服务差价，不再死磕热门商品 |
| r/PPC | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 37 | Y |  | 数字广告从业者求职时，社区建议先问对方懂不懂技术细节，再决定讲功能还是讲收益 |
| r/DigitalMarketing | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 33 | Y | pending | Chrome 搜索结果页常驻 AI 框，营销人优化重心从网页排名转向 AI 引用 |
| r/OpenAI | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 30 | Y | pending | ChatGPT 根据兴趣生成游戏概念，用户晒图称准确想玩，但质疑这个方案算不算游戏 |
| r/ClaudeAI | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 23 | Y | pending | 开发者与 AI 重度用户，不再只用一个模型，开始双持 Claude Max 和 GPT Pro |
| r/artificial | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 18 | Y | pending | Reddit 用户预判 Meta 将通过排他性授权协议平息版权诉讼 |
| r/ProductManagement | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 17 | Y |  | PM 用 Figma Make 做概念设计，开始算这个方案省没省时间 |
| r/analytics | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 9 | Y |  | 数据分析与 SEO 社区：新手焦虑学不完，老手优势在知道去哪找答案 |
| r/Google_Ads | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 9 | Y |  | SaaS 投手发现线索便宜但没用，先收紧匹配类型和表单过滤意图，再考虑放量 |
| r/googleads | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 9 | Y |  | Google Ads 新手别再死磕点击成本和 CTR，先检查落地页内容、优惠和体验能否留住用户 |
| r/adops | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 8 | Y |  | 谷歌广告投手面临信任危机：内部爆料称团队为保收入目标，从不讨论点击欺诈 |
| r/projectmanagement | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 6 | N |  | 行动项写出来没人认领，不是记录不清，是第一步没人敢接 |
| r/content_marketing | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 5 | Y |  | GEO 公式越讲越复杂，内容营销人反而先回到基础 SEO |
| r/juststart | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 5 | Y |  | 小企业主用 Gemini API 做关键词研究，不再迷信搜索量，转而用 AI 判断搜索意图能否带来生意 |
| r/productivity | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 5 | N |  | 行动项写出来没人认领，不是记录不清，是第一步没人敢接 |
| r/singularity | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 3 | Y | pending | 马斯克私信 Brockman 试探和解，评论区却把它看成示弱 |
| r/seogrowth | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 2 | Y |  | 新站页面显示“已发现未索引”，别再先提交 sitemap，先查页面有没有权威信号 |
| r/Substack | promote_candidate | 建议补入 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 2 | Y |  | Substack 创作者分享万粉攻略，评论区指责其内容陷入增长套娃循环 |
| r/GiftIdeas | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 21 | Y |  | 送礼者开始想‘我为什么记得这个’，不再只搜创意清单 |
| r/ManyBaggers | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 20 | Y | pending | 2026旅行背包选购，发烧友不再执着完美，转向高复购型号 |
| r/kickstarter | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 18 | Y |  | Kickstarter 神谕卡项目被指 AI 生成，收藏家受不了错别字和构图错误 |
| r/EDC | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 14 | Y | pending | Wuben G5 在31美元价位获实测好评：磁吸和亮度强，背夹成短板 |
| r/CampingGear | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 6 | Y |  | Coleman Cascade 选购帖里，露营者因为集成烤盘难清理，转头选经典款配锅具 |
| r/AsianBeauty | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 5 | N |  | 赴日游客买护肤品，松本清的价格优先级开始超过唐吉诃德 |
| r/stationery | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 4 | Y |  | 文具囤积者把‘用不完’的焦虑，转成‘送出去’的社交价值 |
| r/SkincareAddiction | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 3 | N |  | 欧洲 SPF 唇部买家开始把有色润唇和唇油当作防晒新选择，同时哑光 SPF 润唇膏出现空白 |
| r/beagles | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 2 | N |  | 800行提示词工程，评论区质疑这个方案有什么用 |
| r/hobonichi | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 2 | Y |  | Hobonichi 用户因补充本封面厚实防水，开始评估本体是否够用，不再默认必须买封套 |
| r/ApartmentHacks | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | Y |  | 租客养宠防尿渗，开始问能不能自己铺整块塑胶地板 |
| r/fountainpens | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | Y |  | 英国钢笔买家不再等本地折扣，转而先算日本直购总成本 |
| r/homeoffice | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | Y |  | 升降桌用户选购优先级转变：重物承重后的稳定性比记忆高度功能更重要 |
| r/Journaling | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | Y |  | 手帐用户从问“买哪本”转向先问“怎么分册”，解决日记和规划混用的混乱 |
| r/NewParents | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | N | pending | 新手父母吵妈咪包是不是刚需：要的是分区收纳，不是那个标签 |
| r/planners | promote_candidate | 建议补入 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | Y |  | 手帐买家挑选顺序变了：先问周计划页之间有没有空白页，不再只看日计划页够不够多 |
| r/LocalLLaMA | keep_active | 保持在 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 12 | Y |  | 本地运行 LLM 讨论升温，用户更在意模型控制权和隐私 |
| r/PromptEngineering | keep_active | 保持在 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 8 | N |  | 提示工程师角色讨论帖火了，焦点是‘完美提示词’到底有没有用 |
| r/automation | keep_active | 保持在 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 5 | Y |  | 自建浏览器代理的团队，现在先算人工时，不再只看月费账单 |
| r/StableDiffusion | keep_active | 保持在 pool | AI 工具链 / 工作流社区 | 入池学习，按工具链主题和事故/工作流信号限额 | 1 | Y |  | Stable Diffusion 重度用户在工具帖下先问“以后能读图吗”，而不是先问“能整理文件吗” |
| r/ecommerce | keep_active | 保持在 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 37 | Y | pending | Shopify 划定 B2B 营收门槛，非核心卖家被边缘化 |
| r/FulfillmentByAmazon | keep_active | 保持在 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 28 | Y |  | 亚马逊卖家处理杀虫剂误判从申诉转向新建 ASIN，主图制作放弃手动 PS |
| r/EtsySellers | keep_active | 保持在 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 14 | Y |  | Etsy 卖家被恶意投诉下架爆款，评论区开始教人从投诉方美国地址切入反击 |
| r/AmazonSeller | keep_active | 保持在 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 11 | Y |  | 亚马逊卖家处理杀虫剂误判从申诉转向新建 ASIN，主图制作放弃手动 PS |
| r/shopify | keep_active | 保持在 pool | 平台 / 卖家 / 增长操作社区 | 入池学习，绑定业务线，避免泛运营噪音打满 | 11 | Y | pending | Shopify 卖家开始用 AI 编码替代简单 App，但先要确认自己是想做品牌还是开发者 |
| r/FacebookAds | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 34 | Y | pending | Meta 广告 ROAS 狂跳，投手抱怨两月来流量质量持续恶化 |
| r/SEO | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 27 | Y |  | 搜索引擎算法误伤无 AI 原创站，SEO 从业者质疑其在优化 AI 内容而非打击 |
| r/ChatGPT | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 11 | Y | pending | AI 用户转向把审美与判断力看得比执行速度更重 |
| r/Entrepreneur | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 9 | Y |  | 独立开发者靠 AI 冲 50 万 ARR，社区先追问创始人瓶颈 |
| r/TechSEO | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 7 | Y |  | SEO 专家开始把 llms.txt 当无效劳动，不再优先配置 |
| r/smallbusiness | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 5 | Y | pending | B2B 销售开始比对成功与停滞通话，不再只改邮件文案 |
| r/SaaS | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 3 | Y | pending | 产品经理看到兼职产品负责人招聘，第一反应是‘这是招人还是招 AI 饲料？’ |
| r/startups | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 3 | Y |  | 小团队增长逻辑错了：一边给 VC 生态的冗余 SaaS 交学费，一边用广撒网的笨办法找客户 |
| r/marketing | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 2 | Y |  | Reddit 广告投放前，营销从业者在 r/marketing 质疑八成以上点击可能是假的 |
| r/bigseo | keep_active | 保持在 pool | 泛社区 / 热点入口 | 入池但设 cap，防止打满默认采集面 | 1 | Y |  | 品牌名‘Modeal’被 Google 自动改成‘Modal’，导致搜索流量归零，品牌命名前必须先测搜索引擎行为 |
| r/BuyItForLife | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 51 | Y |  | Vitamix 买家开始对比杯身设计，不再只盯电机参数 |
| r/CleaningTips | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 14 | Y |  | 清理长发地毯的人开始用拆线器切断吸尘器滚刷上的缠绕头发 |
| r/Frugal | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 14 | Y |  | 节俭用户保留15年老刀柄，转用廉价兼容刀片摆脱品牌耗材 |
| r/espresso | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 11 | N |  | 预算足的咖啡新手不再买入门机，怕便宜货更难上手 |
| r/dogs | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 10 | N |  | 宠物主开始找爪部专用防护替代品，不再默认套硬塑料伊丽莎白圈 |
| r/flashlight | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 9 | Y | pending | EDC 手电筒新手帖火了，不是缺推荐，是大家开始教买家先搞清楚自己讨厌什么 |
| r/onebag | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 9 | Y | pending | 极简旅行者争论：登机随身小包还算不算“单包”旅行 |
| r/beyondthebump | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 3 | Y |  | Reddit 用户发现，省下着装费的同事被降职，囤积的杂物占了家人的卧室 |
| r/knives | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 3 | Y |  | 刀友和钥匙扣用户共识：判断一个东西该不该带，别听厂商的，看它有没有在意外场景里救过急 |
| r/3Dprinting | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 2 | N |  | 想买 3D 打印机的人，把售后态度放在了硬件参数前面 |
| r/DIY | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 2 | N |  | 印度 DIY 用户买电动工具，不再迷信品牌，更看重耐用性 |
| r/homeowners | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 2 | Y |  | 首次购房者发现开发商装修升级报价远高于市场价，宁愿收房后自己找口碑好的外部承包商 |
| r/Ultralight | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 2 | Y |  | 轻量睡垫买家开始拆解 R 值：Eclipse 实验室参数高，但边缘管路绝缘只覆盖一半 |
| r/AutoDetailing | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | N |  | 汽车美容争议不在产品推荐，是大家吵安全到底靠选品还是靠防护 |
| r/backpacking | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | Y |  | 背包客选包新顺序：先称装备总重，再匹配背包承重等级 |
| r/Coffee | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | N |  | 视障咖啡爱好者选购设备先看触觉按钮和改装空间，不再优先考虑专用语音秤 |
| r/Justrolledintotheshop | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 1 | N |  | 特斯拉电池包悄悄换了接线方案，修之前不查版本号可能白忙一场 |
| r/battlestations | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 0 | Y |  |  |
| r/bushcraft | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 0 | Y |  |  |
| r/survival | keep_active | 保持在 pool | 长尾垂直社区 | 入池并重点学习，按活跃度和帖质调频 | 0 | Y |  |  |

## 31 个补证据社区

这些社区不降级，不删除。下一步只补活跃度和帖子质量证据。

| 分组 | 社区 | 下一步 |
|---|---|---|
| 增长供给缺证据 | r/advertising, r/affiliatemarketing, r/agency, r/copywriting, r/cro, r/genengineoptimization, r/instagrammarketing, r/marketinganalytics, r/newslettercommunity, r/saasmarketing | 抽样查近期发帖、评论深度、具体需求密度；通过后纳入学习范围 |
| AI 供给缺证据 | r/agentsofai, r/aicuriosity, r/anthropic, r/deepseek, r/mcp, r/n8n, r/opencodecli, r/selfhosted | 抽样查近期发帖、评论深度、具体需求密度；通过后纳入学习范围 |
| 电商供给缺证据 | r/crowdfunding, r/mousereview, r/myog, r/organization, r/petproducts, r/sharktank, r/ultrawidemasterrace | 抽样查近期发帖、评论深度、具体需求密度；通过后纳入学习范围 |
| discovered-only pending | r/babybumps, r/cats, r/daddit, r/digitalnomad, r/dropship, r/dropshipping | 抽样查近期发帖、评论深度、具体需求密度；通过后纳入学习范围 |

## 115 个旧池待复查资产

`stale_review` 不等于垃圾池。它只表示这些旧社区还没被 Hotpost 新链路验证。

| 分组 | 数量 | 处理 |
|---|---:|---|
| 平台 / 卖家 / 增长旧资产 | 21 | 先抽样查旧 DB 和当前活跃度，不删除 |
| 商品 / 家居 / 户外 / 兴趣旧资产 | 84 | 查近期帖质和垂直需求密度，通过则继续保留 |
| 低优先级旧资产 | 10 | 最后审，仍不自动删除 |

## 10 个 observation_queue 的处理

`observation_queue` 不是全局黑名单，也不是噪音池。它只表示 Phase 0 证据还不够，不作为第一轮社区池扩充对象。

| 类型 | 社区 | 处理 |
|---|---|---|
| 可转低频观察 | r/aiToolForBusiness, r/BusinessIntelligence, r/carcamping, r/dataengineering, r/linear, r/VacuumCleaners | 有一张卡但证据不足，低频观察 |
| 暂不扩充 | r/AynThor, r/Denmark, r/Leuven, r/Yorkies | 明显错配或业务价值暂不清楚 |

## Phase 0 验收结论

Phase 0 到这里完成的是只读治理收口：

- 已确认当前社区资产总数。
- 已确认 108 个已有证据社区的入池 / 保留 / 使用策略。
- 已确认泛社区不排除，只设 cap。
- 已确认长尾社区按活跃度和帖质学习。
- 已确认 31 个补证据社区和 115 个旧池资产不降级、不删除。

下一步进入 Phase 1：做 dry-run 入池差异表、活跃度 / 帖质字段和写库前验收，不在 Phase 0 直接写 DB。
