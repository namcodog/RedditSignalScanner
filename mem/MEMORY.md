# MEMORY.md — 活跃记忆

> 最近 30 天内的洞察、决策、行动记录。高频更新。
> 超过 30 天未引用的条目应迁移到 ARCHIVE.md。
>
> 文件体系：
> - SOUL.md — AI 人格（行为方式/操作原则）
> - IDENTITY.md — 身份（世界观/风格/偏好，月级更新）
> - PLAYBOOK.md — 商业判断手册（被证伪模式/诊断框架）
> - **MEMORY.md** — 活跃记忆（你在这里）
> - ARCHIVE.md — 归档（30天+的旧记忆，按主题分类）

Last updated: 2026-03-05T13:36:00+08:00

## Current State (实时状态)

**正在做**: MCP 工具全量配置完成，多 Agent 编排方案调研完成，准备重启后执行任务
**下一步**: 重启 session 验证 serena/exa-code 是否正常加载 | 开始执行仓库优化任务
**关键决策**: Antigravity = Orchestrator，直接通过 run_command spawn Codex/Gemini CLI 实现多 Agent 分工，零额外框架
**待落实**:
- P0: 重启验证 serena + exa-code MCP 正常（已干跑通过，等重启确认）
- P1: 用 Antigravity + Codex/Gemini 分工执行仓库优化任务
- P1: NotebookLM 启用（自己的→Obsidian，别人的→NotebookLM）
- P2: 研究 Maestro 插件（Gemini CLI 多 Agent 编排插件）

---

## Recent Signals (外部信号)

- [echotik-creatok-flywheel] **EchoTik+CreaTok 飞轮验证** — Data→Content→Sales→Data。品牌为内容付费，不为洞察付费。差异化在多平台交叉验证。(2026-03-02)

## Recent Frameworks (框架)

- [capability-vs-product] **能力 vs 产品的分界线** — 分界线=翻译过程是否需要人的判断力。快速测试："如果我不在，这个东西还能运转吗？" (2026-03-04)
- [system-design-escape] **系统设计逃逸模式识别** — 诊断方法：文档角色数＞实际执行人数=过度设计。解药：停止写蓝图，做一个真实案例。(2026-03-04)
- [5-file-memory-architecture] **5文件记忆体系** — SOUL(人格)+IDENTITY(身份)+PLAYBOOK(判断)+MEMORY(活跃)+ARCHIVE(归档)。文件即接口，任何AI工具可读写。记忆不绑平台，跟着人走。(2026-03-05)

## Recent Actions (行动记录)

- [reddit-intel-script-automation] **reddit-intel 脚本化改造完成** — prompt→shell 脚本（search/comments/jina/save.sh），LLM 只负责分析。(2026-02-27~03-01)
- [skill-routing-fix] **Agent Skill 路由修复** — Captain theme prompt 增加显式 skill 路由指令。(2026-02-27)
- [sociavault-full-probe] **SociaVault 85 端点全量验证** — 产出两份完整报告，14 个平台全覆盖。(2026-03-01~02)
- [market-intel-query-framework] **市场情报查询框架重设计** — 6 个精确子问题 Q1-Q6，明确工具路由和输出格式。(2026-03-01)
- [api-doc-refinement] **API 文档精炼** — 统一为表格化 API 参考手册。(2026-03-02)
- [pinterest-api-verified] **Pinterest API 字段级验证** — 4 端点核实，/pin 信息密度最高。(2026-03-02)
- [memory-system-restructure] **记忆系统拆分重组** — MEMORY.md 单体文件拆为 IDENTITY/PLAYBOOK/MEMORY/ARCHIVE 四文件体系。(2026-03-04)
- [personal-resume-v1] **个人叙事简历 v1** — 基于全部 mem/ 画像数据 + 产品 SOP/报告素材，输出务实口吻的个人简历，重点展示 RedditSignalScanner 产品价值和商业逻辑。(2026-03-05)
- [antigravity-memory-integration] **Antigravity 记忆系统自动化接入** — GEMINI.md 加 Section 6(启动/关闭协议+权限红线)，MEMORY.md 加 Current State 快速上下文头，创建 3 个 workflow(load/save/archive)。启动协议升级为全量必读。(2026-03-05)
- [openclaw-memory-wiring] **OpenClaw 记忆管道接线** — backend-config.ts 加搜索范围(+3文件)，system-prompt.ts 更新指令，session.ts 接线 archiveDailyFiles。12行代码，32/32测试通过。(2026-03-05)
- [antigravity-mcp-full-config] **Antigravity MCP 工具全量配置** — .gemini/settings.json 新增 sequential-thinking/serena/exa-code 三个 MCP。修复两处 bug：serena uvx 路径错误(改为/opt/homebrew/bin/uvx)、exa-code npx 路径错误(改为nvm实际路径)、serena context 名称过期(ide-assistant→claude-code)、npm 缓存冲突清理。三个工具均干跑验证通过。(2026-03-05)

## Recent Decisions (决策)

- [reddit-intel-role] **reddit-intel 定位归位** — 作为个人研究工具已足够好。正确角色：自用侦察兵 + AIGC 后台能力。(2026-03-04)
- [multi-agent-orchestration-approach] **多 Agent 编排方案选型** — 不引入 Maestro/ADK 等重框架。Antigravity = Orchestrator，通过 run_command 直接 spawn Codex CLI(后端任务) + Gemini CLI(前端/分析任务)，零配置成本即可实现分工。Codex v0.104.0 + Gemini v0.31.0 均已安装在 nvm 路径下。(2026-03-05)

---

## Pending Implementation (待落实)

- ~~**⚡ 记忆自动管道接线**~~ — ✅ 已完成。archiveDailyFiles 接到 session 重置流程，memory_search 范围扩展到 4 个文件。(2026-03-05)
- **⚡ OpenCode/Codex 记忆接入** — 需配置 AGENTS.md / instructions 文件，让它们启动时读取 MEMORY.md + IDENTITY.md。(优先级：P1)
- **⚡ NotebookLM 启用** — 自己的东西→Obsidian，别人的东西→NotebookLM。尚未用起来。(优先级：P1)
- **🔍 antigravity + stitch 工具组合** — 待研究商业场景。(优先级：P2)

---

## Calibration Log (最近 5 条)

- 2026-03-05: 记忆系统接线 + 架构确立 — OpenClaw 代码接线完成（12行改动，4文件）。确立 5 文件记忆架构（SOUL/IDENTITY/PLAYBOOK/MEMORY/ARCHIVE）。明确记忆系统=文件系统，不绑定任何 AI 工具。待配置 OpenCode/Codex 接入。
- 2026-03-04: Reddit 情报产品化证伪 + 记忆系统重组 — 确认 Reddit 情报无法产品化（产品化三前提全不满足）。系统设计逃逸再次发作。发现记忆系统 archivist 代码写完但未接线/未部署。执行 MEMORY.md 四文件拆分。
- 2026-03-02: Pinterest 套利机证伪 + EchoTik 竞品拆解 — Pinterest 无历史趋势数据，EchoTik 已做完全部设想。新增病因"量化幻觉"。
- 2026-02-25: 深度商业模式校准 — 确立"AIGC获客→挖掘痛点→KAG自动化交付"路线。API 工具定位下调为"探针"。


---

## 2026-02-23

# 2026-02-23 Daily Notes

## OpenCode Server Mode + Discord Bot 方案 (12:53)

**想法：** OpenCode 有 Server 模式，可以创建 Discord Bot 连接 OpenCode 服务器，实现手机远程操控 OpenCode + 项目目录。

**状态：** 社区有现成项目，但打算让 AI 直接写脚本。

**待办：** 让 AI（coder）写 Discord Bot ↔ OpenCode Server 转发脚本。
**启动信号：** 豆爷提起这个话题时，直接帮他启动（spawn coder 写脚本）。

## 待研究：Antigravity + Stitch 工具组合商业场景 (16:07)

**状态：** 立项，待深度研究

**核心问题：** 这个工具组合能做出什么？有哪些商业场景？

**待探索方向：** 工具能力边界 × 变现场景 × 与 AIGC 视频方向的结合可能

## 新项目立项：视频内容数据库 × Obsidian (13:47)

**文件：** `projects/video-content-db.md`（100%原始思考已归档）

**本质：** 构建 AIGC 时代的"私人情报局"——内容情报与商业变现闭环系统。

**核心动作：** 对顶尖创作者（Hashem Al-Ghaili / László Gaál / 2XLabs）做反向工程，将工具×题材×流量的因果链接入库 Obsidian。

**变现路径：** Spec Ad → Real Order，目标月收入 5K-35K

**待深度分析：** Obsidian 结构设计 + AIGC 创作者拆解模板（YAML）

## 关注点：OpenCode + oh-my-opencode 的战略意义 (13:42)

**核心判断：** 2026年 AI 大趋势 = 多Agent并行。从用镰刀，到开联合收割机成为农场主。

**具体转变：** 不是盯着一个 Agent 写代码，而是管理10-12个 Agent 并行工作。

**为什么 OpenCode + oh-my-opencode：**
- oh-my-opencode 本质是给 OpenCode 加强大编排能力（Orchestrator）
- 内置 Sisyphus Agent：专门负责后台脏活累活、上下文管理和任务分发
- 社区自发涌现的强者，不是官方设计的

**自造形态的初级阶段：** 虽然还是人造的壳，但内部已经开始自我编排——这正是豆爷一年前预测的方向初步落地。

**待办：** 亲自上手体验，没有体感就没有判断力。

## 个人AI知识库架构原则 (13:41)

**两条结论：**
- **自己的东西 → Obsidian**（原创思考、笔记、方法论）
- **别人的东西 → NotebookLM**（外部文章、参考资料、研究素材）

**待启用：** NotebookLM 还没用起来，需要落地。

## 人生哲学：高主体性（High Agency）不会被AI取代 (13:40)

**核心命题：** 任何单一技能都会被 AI 取代或贬值，唯有"高主体性"不会。

**定义：** 在没有外部规则、许可的情况下，依然能持续行动、迭代的能力。拒绝等待批准，独立思考并快速执行。

**两种人的分野：**
- 低主体性：依赖系统、追逐认可、用工具复制别人
- 高主体性：用工具测试自己的想法，主动塑造现实

**关键判断：** AI 不会消灭主体性，反而放大差距——它暴露了谁真正有独立行动能力。

**金句：** 未来的优势不在于天赋、智力或技术，而在于"规则消失后，谁还能继续尝试"。

## 产品需求碎片：知识星球 Thread 功能 (13:39)

**痛点：** 知识星球缺乏 Thread（主题串）功能，持续迭代的思考无法被归拢，只能散落在时间线里。

**想要的：** 同一主题内容归拢到一起（如"关于 Claude Code 的用法"持续更新）+ 能看到思考如何迭代。保留帖子基础功能，额外增加 Thread 层。

**参考：** Substack 的 Thread 做得好——可设置只有管理员能发起新主题，主题下所有内容在一个"聊天"里统一查看。国外普遍有这个设计，国内产品普遍无感。

**现实出路：** 在 Obsidian 里自己实现这种直观的 Thread 体验——按主题组织笔记，看迭代轨迹。

## 工具选型：Zed 编辑器 (13:37)

**结论：** Zed 是目前最符合豆爷需求的编辑器（胜过 VS Code 和纯终端工具）。

**三个核心优势：**
1. 能流畅渲染 OpenCode TUI（VS Code 会卡顿）
2. 具备 Markdown 预览 + 文档编辑功能（纯终端工具没有）
3. 外观现代干净

**Zed vs VS Code：** Zed 是 Rust 原生编辑器（非 Electron），比 VS Code 轻很多。代价是插件生态不如 VS Code 丰富。

**Zed vs 纯终端：** 填补了"终端能力 + 图形文档体验"之间的中间地带，两头都不牺牲。

**短板：** 扩展生态 niche 功能需要等社区或自己配置。

## 工具推荐：OpenCode + oh-my-opencode = 深度定制 AI OS (13:32)

**核心观点：** 想深度定制自己的 AI OS，用 OpenCode + 插件 oh-my-opencode，配置丰富度远超 Claude Code。

**关键能力：** 可以重新设定属于自己的多 Agent 流水线。

**待探索：** oh-my-opencode 插件的具体能力边界；与当前 OpenClaw + newtype Profile 体系的关系和兼容性。

## 技术认知：真正的多Agent编排 vs Claude Code Sub-agents (13:31)

**结论：** Claude Code Sub-agents = "内部任务路由 + 轻量委托"，入门级，只适合简单场景。不是行业期待的多Agent编排。

**真正的多Agent编排五要素：**
1. **层次化嵌套** — meta-orchestrator 管子 orchestrator，形成团队中的团队（hierarchical/swarm），支持复杂委托链和辩论/审核机制
2. **多模型跨提供商** — 不同 Agent 用不同模型（Opus规划、Flash执行、Grok搜索），成本/性能各自优化
3. **共享状态与高级协调** — 持久记忆、冲突解决、动态路由、循环迭代、错误恢复，由外部框架管理
4. **真正并行与扩展性** — 数十至数百 Agent 并发，适合长运行大规模任务（全栈重构、企业自动化）
5. **可编程灵活性** — 开发者用代码定义 workflow，不依赖单一 LLM 的"自然语言委托"

## 工具技巧：Chrome 拆分视图 (13:30)

**功能：** Chrome 内置拆分视图，两个网页并排显示在同一窗口。

**典型用法：** 左边 Gemini + 右边 GPT，对比两个 AI 输出；或左边参考资料 + 右边写作窗口。

**触发场景提醒：**
- 需要对比多个 AI 模型输出时
- 需要同时打开参考资料 + 写作/编辑窗口时
- 配合 Gemini Add tabs 功能使用效果更佳

## 人生哲学：先有实践，后有理论 (13:27)

**来源：** KK《科技想要什么》——Science is not the parent of technology, but its child.

**核心反转：** 我们以为是"科学→技术→应用"，实际历史是反过来的：
- 瓦特造蒸汽机时，热力学不存在。机器跑了50年，物理学家才来总结"热力学第二定律"
- 莱特兄弟靠自制风洞的经验数据飞上天，当时流体力学数据很多是错的

**映射到个人成长：** Learning by doing 就是这个意思。清晰是行动的结果，不是行动的前提。

**两个障碍：**
1. 学校教育强调理论先行（只有理论，不考实践）
2. 对失败的恐惧——"没想清楚"是最好的拖延借口

**Bug 所在：** 行动前能想到的，只是你已经知道的。真正需要的 Insight 藏在还不知道的地方——只有做了才能拿到。

**金句：** 蒸汽机跑了五十年，才跑出热力学。你也一样。先跑起来。

## 商业机会：扣子技能商店 (13:27)

**信号：** 扣子（Coze）上线技能 + 技能商店，变现路径打通。

**机会：**
- 职场人：技能直接提升工作效率（ToB/ToC 需求都有）
- 开发者：国内扣子生态开发者基数大，技能商店是新的变现出口

**待思考：** 自己做的 Skills（Super Analyst/Writer/等）能否移植/适配扣子生态？国内扣子开发者社区的竞争密度和变现天花板如何？

## 知识储备：运营美国公司实际成本 (13:25)

**注册：** Stripe Atlas 一次性费用 $500（2-3个工作日，无门槛）

**每年固定成本（首年实际发生）：**

| 项目 | 费用 |
|------|------|
| Stripe Atlas 代理年费 | $100/年 |
| Stripe Tax 订阅 | $90/月 = $1080/年 |
| Stable 虚拟地址+邮箱 | $24.5/月 = $294/年 |
| 特拉华州政府年度税 | $300/年（有无收入都要交）|
| 国内代理年度报税（公司+个人）| ¥6000 |
| **合计首年** | **约 ¥18,362** |

**额外：** ITIN 申请（本人+配偶）约 ¥2000

**总结：** 首年成本约 ¥2万+。美国公司有好处，但维持成本是实实在在的，注册前想清楚。

**来源：** 他人亲身经历（借鉴，非豆爷本人），数据截至2025年。

**备注：** 豆爷尚未注册美国公司。有需要时，Agent 协助 update 最新流程并完成注册。

## 系统型选手 vs 天赋型选手 (13:20)

**核心信条：** 不当天赋型选手，当系统型选手。把不确定的"灵感"和"状态"，固化为可复用的"资产"和"流程"。

**实践来源：** MCP、Skills、多Agent编排插件——都是这个哲学的产物。

**校准（13:23）：** SOP 和思维之间有张力——系统化的边界不是非此即彼，而是**权重划分**，两者都是变量。实践中动态调整，不固化边界本身。"系统服务于判断，而不是替代判断。"

## 文化基因 vs 生物基因 (13:17)

**核心命题：** 生物繁衍只是肉体存续，观念传播才是更高维度的延续。

**三层拆解：**

1. **生物基因高损耗** — 每代只传递50%，无法遗传智慧和思维方式，投资回报率极低

2. **文化基因（Meme）零边际成本** — 三个极客属性：
   - 高保真复制（思想100%传递，不打折扣）
   - 无限分发（同时运行在无数大脑，边际成本≈0）
   - 可迭代性（吸收者的优化让基因更强）

3. **智识血缘** — 不是有人长得像我，而是有人像我一样思考。读Newsletter → 认可判断 → 复用方法论，那一刻运行的就是我的源代码。

**文明观：** 人类文明是所有个体文化基因的汇总代码库。圣贤贡献底层操作系统，普通人每次有效的观念传播 = 向文明数据库提交一次 Commit。

**个人使命：** 让思维方式在更多人大脑中获得 root 权限并长久运行——这才是 newtype 的更高级进化。

## 多Agent编排 — 子Agent质量评分机制 (13:16)

**来源：** newtype Profile 实践总结

**核心设计：** 给每个专业 Agent 加多维度质量评分，维度按角色定制：
- Researcher（情报员）：覆盖度 / 来源质量 / 相关性
- Writer（写手）：结构 / 清晰度 / 有据可依

**评分阈值：**
- ≥ 0.8 → 交给下一个 Agent
- 0.5–0.79 → 自我优化后重试
- < 0.5 → 重做

**关键点：** 系统必须精确指出最弱维度 + 针对性改进建议，而不是笼统"再试一次"。闭环靠精准诊断，不靠重跑。

## NVIDIA 200亿收购 Groq — 商业信号解读 (13:13)

**核心命题：** 这笔交易不是买一家公司，而是买一个威胁的消失。

**关键信号：**
- AI工作负载重心：训练（10%成本）→ 推理（90%成本），GPU在推理场景严重过剩
- Groq LPU 的价值：确定性架构，推理速度是 H100 的5倍，能耗低一个数量级
- NVIDIA 焦虑点：Groq 用事实证明了**推理不需要 GPU**

**防御性收购三层逻辑：**
1. 买 IP — TSP 技术栈数百项专利直接嫁接下一代推理加速卡
2. 消灭萌芽 — 颠覆性创新用《创新者的窘境》视角看，不赌它失败，直接买下
3. 重构产品线 — 用独立品牌运作推理线，避免与训练卡自我蚕食

**产业趋势：训推分离加速**
- 训练集群：H100/B100（CUDA生态）
- 推理集群：LPU/专用架构（工具链分裂）
- 可重构架构（Groq/Cerebras/SambaNova/Tenstorrent）估值重估，灵活性 > 极致性能

**对创业公司的启示（残酷版）：**
- 技术突破必要，商业成功不必要——只需让巨头焦虑的 demo
- 被收购可能是 AI 芯片创业最优解
- 真正的颠覆者可能永远无法独立长大

**金句：** 有时候，失败者定义了未来的方向，而胜利者只是买下了那张地图。

## 人生哲学："富不过三代"是天道 (13:12)

**核心命题：** 精英不是培养出来的，不是资源堆出来的，是筛选出来的。

**三层拆解：**

1. **均值回归（生物层）** — 第一代精英是基因突变+时代红利的产物，后代大概率向均值靠拢。资源是乘数不是加数——内在素质是0，给100倍资源结果还是0。用钱对抗均值回归是反熵增的徒劳。

2. **公平幻觉（政治层）** — "公平"的本质是降低治理成本。让底层觉得能上牌桌，就不会掀桌子。程序公平的精髓：规则有利于庄家，但你有参与感就不造反。二战后的高流动性是历史异常值。

3. **豢养筛选（现代层）** — 物质淘汰已失效（低保/医疗让庸才也能活）。新的筛选靠认知和自律：AI生产财富，算法/短视频/游戏消耗大众时间精力。精英控制多巴胺保持深度思考，大众沉溺廉价数字快感丧失行动力。这是温柔的、无痛的淘汰。

**四层漏斗模型：**
- 基因层：筛智商和精力
- 意志层：筛延迟满足和对抗本能
- 认知层：筛看穿社会运行本质、不被意识形态忽悠
- 运气层：筛在大周期转折点做对选择

**金句：** 把资源给一个通不过前三层的人，就像把水倒进漏底的桶。

## Super Writer 重做复盘 — Skill 设计原则 (13:09)

**核心教训：SOP 不能为做而做。**

旧版的三大死穴：
1. **强制仪式化** — 无论任务复杂度都走完整流程，简单任务也强制跑3次 Sequential Thinking
2. **描述性而非可执行** — 方法论文档只有10-20行描述，不是能直接跑的 Prompt
3. **主动打断** — 每次问"有风格参考吗"，用户其实经常没有

新版三条设计原则提炼：
- **流程最小化**：UNDERSTAND → PREPARE → CREATE，去冗余；能跳的步骤就跳
- **内容可执行化**：方法论从20行扩展到200-450行，变成完整 System Prompt
- **按需触发**：风格分析、MCP调用只在用户明确需要时启动

**元认知：** 旧版是把 Super Analyst 的 SOP 照搬过来——陷在上一个成功框架里，没有根据新场景重新思考。

**信条：** Learning by doing 是最有效的。亲手做 Skills = 梳理工作流 + 赋能 AI 系统，一石二鸟。

## 记忆系统设计思考 (13:05)

**来源：** Clawdbot 启发 → 在 newtype Profile（OpenCode 内容创作插件）里实现了类似机制。

**两层记忆架构：**
- **短期记忆：** 对话停止后，自动保存进 `.opencode/memory/` 文件夹，如 `2026-01-29.md`
- **长期记忆：** 超过 7 天的日志自动处理、归档进 `MEMORY.md`；也可通过 `/memory-consolidate` 命令手动触发

**洞察：** 这套机制和我们 captain workspace 的设计高度一致——日志文件对应短期，MEMORY.md 对应长期蒸馏。豆爷在独立项目里验证了同一套思路。

## Gemini in Chrome — Add Tabs 功能 (12:58)

最喜欢的功能：**Add tabs** — 把多个已打开网页作为上下文一并喂给 Gemini 处理。看大量文章时极其高效。