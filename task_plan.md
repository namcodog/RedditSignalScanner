# Task Plan: Reddit Signal Scanner 90 分产品验收基线

## Goal
把当前系统从“工程已稳、产品感知不稳”推进到真正可验收的 90 分产品基线。

这轮只围绕 4 个结果收口：
- live 输出的报告稳定为 `A_full`
- 关键页面首屏一眼看懂，价值 punchline 足够硬
- 输入到结果的用户体验地图完整，不需要用户自己脑补
- 真数据、真分析、真页面、真动作链能完整演示，不靠 mock 或旧样本

## Current Truth
- 工程底盘已基本站住：
  - `make test-e2e-live-report` 连续 `3/3` 通过，且都首轮 `A_full`
  - `make test-e2e` 通过，`21 passed`
  - `make dev-real` 已收掉主要假告警
- 产品感知仍未达标：
  - 用户仍明确感受到“字多、解释硬、交互不够顺、像 demo”
  - live 链路虽已稳定，但“真输入 -> 真分析 -> 真报告 -> 真下一步”还没被固化成默认演示基线
  - 体验优化仍集中在结果页，`Input / Progress / 返回链 / 弱结果路径` 还没完全拉成一张顺滑地图

## Non-Negotiable Acceptance Baseline

### 1. 真结果必须站住
- `make test-e2e-live-report` 连续 `5/5` 通过
- 每轮 live report 最终 `required-tier = A_full`
- 主链演示必须使用真抓取、真分析、真报告、真用户
- 示例态只能出现在明确标注的示例入口，不能混进主链

### 2. 首屏价值必须 10 秒看懂
- `Input / Progress / Report / Hotpost / Admin` 首屏都必须回答：
  - 这是什么
  - 现在值不值得继续
  - 下一步应该点哪里
- 首屏不允许 raw 英文、后台字段、重复解释抢前排
- 每页只保留 1 个主 CTA 和最多 2 个次 CTA

### 3. 用户体验地图必须完整
- 必须覆盖 8 条核心路径：
  - 首次输入成功出 A 级报告
  - 首次输入只出弱结果
  - warmup / auto rerun
  - report 返回输入页重跑
  - hotpost 快扫后继续深挖
  - hotpost 快扫后回搜索页重扫
  - admin 判断当天系统是否可用
  - 权限不足 / 数据不足 / 失败态兜底
- 每条路径都要写清：
  - 用户当前目标
  - 页面主结论
  - 下一步动作
  - 失败后的兜底

### 4. 成品感必须统一
- 关键页面桌面端 / 移动端截图级验收通过
- 等待态、弱结果、失败态、成功态都使用同一套产品语言
- 页面不再有明显“后台味 / demo 味 / 临时说明味”

## 90 分打分尺
| 项目 | 权重 | 通过线 |
|------|------|--------|
| 真结果稳定性 | 35 | live `5/5 A_full`，正式 E2E 全绿 |
| 价值表达硬度 | 25 | 首屏 10 秒看懂，主结论不需要二次解释 |
| 交互顺滑度 | 20 | 主 CTA 清晰，返回链和等待态自然 |
| 体验地图完整度 | 10 | 8 条核心路径全部可演示 |
| 视觉与成品感 | 10 | 关键页面双端截图通过 |

## Current Phase
Phase 36 complete
Next: Phase 37（按 canonical report 合同实施主链重构）

## Completed Foundation
- `Phase 391-405` 已完成首屏价值压缩、CTA 统一、三张脸成品感统一、真实样本验收、mock 感回修。
- `Phase 406-407` 已完成 live report 稳定性打通与验收链路稳固化。
- 当前不再缺“能不能跑通”，而是缺“90 分产品到底怎么验收、按什么顺序收”。

## Phases

### Phase 20: 90 分产品验收基线定义
- [x] 对齐当前真状态：工程底盘已稳，但产品感知未过线
- [x] 定义 90 分验收基线、打分尺、不可妥协门槛
- [x] 输出阶段执行顺序与依赖关系
- **Status:** complete

### Phase 21: live `A_full` 结果门禁化
- [x] 增加验收前队列门禁（stale backlog）：`task_outbox pending(stale)` / `crawler_run_targets queued not enqueued(stale)`
- [x] 增加验收阻塞解锁工具（stale lock blockers）
- [x] 增加验收清淤工具（stale pending/outbox 与 stale queued targets）
- [x] 新增 `test-e2e-live-report-5x` 与 `demo-live-a-full` 目标
- [x] 把 `3/3` 隔离通过升级成 `5/5` 稳定门禁
- [x] 固化“真输入 -> 真 A_full report”标准演示脚本（`demo-live-a-full`）
- [x] 把 live 验收结果写入 phase-log 与 key-os
- **Status:** complete

### Phase 22: Report 页价值 punchline 重构
- [x] 先用真实 A 级与弱结果样本重看 report 首屏和中段
- [x] 把第一屏收成“值不值得继续做”的硬判断，不再重复解释
- [x] 把中段改成“支持拍板的 3 个证据块”，不是材料堆
- [x] 收掉弱结果页里所有 mock / demo / 解释性口气
- **Status:** complete

### Phase 23: Hotpost 快扫体验重构
- [x] 把 hotpost 首屏收成“这波追不追”的快扫判断
- [x] 统一摘要、证据、社区三个区块的阅读顺序
- [x] 深挖 / 重扫 / 返回路径统一成自然动作链
- [x] 确保 live hotpost 结果页只展示当前真的有用的信息
- **Status:** complete

### Phase 24: Input / Progress 全链路体验地图补齐
- [x] 画完整用户体验地图，覆盖 8 条核心路径
- [x] 重做 Input 首屏的输入预期、示例引导、提交后承诺
- [x] 重做 Progress 的等待解释、warmup、auto rerun、取消与返回
- [x] 把 report / hotpost / admin 的返回链和来源提示统一
- **Status:** complete

### Phase 25: Admin 信任面与系统反馈统一
- [x] 把 admin 从“后台控制台”继续收成“今天能不能放心开工的信任面”
- [x] 明确当天系统状态、风险、建议动作，不让用户自己翻译指标
- [x] 把任务账本 / 社区池 / 队列状态收成面向决策的表达
- [x] 对齐 admin 的异常态、空态和成功态
- **Status:** complete

### Phase 26: 视觉与交互精品化
- [x] 用统一 token、排版、密度、按钮层级把五张关键页面拉成一套产品
- [x] 收掉“字多、硬解释、说明味重”的残留
- [x] 做桌面端 + 移动端截图级验收
- [x] 按 `ui-ux-pro-max / frontend-design / web-design-guidelines` 再做一轮细修
- **Status:** complete

### Phase 27: 90 分正式验收
- [x] 连跑 `make test-e2e-live-report`、`make test-e2e`、真实浏览器脚本
- [x] 用真实用户完整演示 `Input -> Progress -> A_full Report -> Next Action`
- [x] 对照 90 分打分尺重新打分
- [x] 记录“是否达到 90 分有质感产品基线”
- **Status:** complete

### Phase 28: 冲 95+ 精品化微调
- [x] 收 Input / Progress 的文案密度与动作层级（第一刀）
- [x] 收弱结果/空态的超长解释，统一成“结论-证据-动作”三句内
- [x] 做一轮移动端截图级微调并回归正式 E2E
- [x] 修复 `user-journey` 登录流程导航竞态，恢复正式 E2E 稳定全绿
- **Status:** in_progress

### Phase 29: 产品合同统一
- [x] 收敛统一产品口径：`开放提问 = 产品默认主链`
- [x] 收敛统一优先级：默认先冲 `Full A`
- [x] 明确 `topic_profile` 角色：首页标准展示卡 / 黄金样板 / 加速路径
- [x] 明确 `B_trimmed / C_scouting / X_blocked` 是降级结果，不是默认预期
- **Status:** complete

### Phase 30: 系统现实全面审计
- [x] 审计首页卡片、guidance/example library 与 `topic_profile` 的真实关系
- [x] 审计 `/api/analyze`、`TaskCreate`、`analysis_engine.run_analysis` 的默认主链
- [x] 审计 `facts_v2` 门禁对无 `topic_profile` 任务的真实行为
- [x] 审计 `X_blocked / C_scouting / B_trimmed / A_full` 的后端渲染与前端交付口径
- **Status:** complete

### Phase 31: 合同整改计划
- [x] 入口层：把首页 6 张卡从“快速起草”升级为真正的 `topic_profile` 黄金入口
- [x] 提交层：让开放输入默认主链显式以“冲 Full A”为目标
- [x] 门禁层：把 A/B/C/X 的判定改回“证据硬度驱动”，缩小 `X_blocked` 使用边界
- [x] 交付层：让 B/C/X 也有可执行价值，不再返回“报告拦截 + 废话建议”
- [x] 验收层：新增“无 profile 的正常开放题也能产出高价值报告”的正式验收基线
- **Status:** complete

### Phase 32: 合同修复实施
- [x] 修首页卡片数据结构与提交流程，支持 `topic_profile_id`
- [x] 修开放提问主链的路由、召回、quality gate 与降级逻辑
- [x] 修 `X_blocked` / `C_scouting` 的报告生成与前端页面表达
- [x] 补回归测试、正式 E2E 与真实样本验收脚本
- **Status:** complete

### Phase 33: 新合同正式验收
- [x] 标准卡黄金路径：6 张卡都能稳定打出接近或达到 Full A 的结果
- [x] 开放输入主链：在 DB 已覆盖社区范围内的正常问题，默认能打出接近 Full A 的价值报告
- [x] 降级链：B/C/X 都能说清“当前结论 / 已有证据 / 下一步动作”
- [x] phase-log、planning files、key-os 全部回写完成
- **Status:** complete

### Phase 34: Full A 标杆合同差距审计
- [x] 确认 `reports/t1价值的报告.md` 是 Full A 唯一内容结构标杆
- [x] 审计后端 `A_full / B / C / X` 判定是否受该结构约束
- [x] 审计结构化报告生成链是否把 6 大结构字段当成硬门槛
- [x] 审计前端结果页是否把 `B/C` 交付为同骨架简化版，而不是另起一套
- [x] 输出 P0 差距清单，判断产品方向是否漂移
- **Status:** complete

### Phase 35: 6 卡 Full A 矩阵落地与验收入口固化
- [x] 修复 `run_topic_profile_full_a_matrix.py` 的运行时稳定性（导入路径、字段兼容、DB 校验）
- [x] 为结构化报告缺失场景补后端 deterministic fallback，确保 `report_structured` 符合 6 大结构合同
- [x] guidance 首页 6 卡改为“固定黄金卡优先”，避免示例库噪音覆盖标准展示入口
- [x] 户外（EDC）标准卡提示词升级为 keychain/pocket organizer 真实需求口径，恢复稳定 `A_full`
- [x] 新增 `make test-e2e-topic-profile-matrix` 一键验收命令并验证通过
- [x] 正式回归：`make test-e2e` 全绿 + `make test-e2e-topic-profile-matrix` 全绿
- **Status:** complete

### Phase 36: Full A 统一产品合同与系统合同固化
- [x] 把“分析真相源”和“交付真相源”正式分开：`insights + facts_v2/facts_slice` vs `canonical_report_json`
- [x] 把 `卡片视图 / Markdown / HTML` 必须同源于 `canonical_report_json` 写成硬合同
- [x] 把前端不得自编解释、不得自补结构、不得改区块顺序写成硬规则
- [x] 把 `topic_profile` 首页标准卡 = 固定 canonical snapshot、实时重跑 = 单独动作 写成硬合同
- [x] 产出正式 SOP + phase-log，并简洁写回 `key-os`
- **Status:** complete

## Execution Order
1. 先稳住 `A_full` 门禁，不然前端精修会继续被“像 demo”拖分。
2. 再收 `Report / Hotpost` 的价值 punchline，因为这是用户第一眼最容易打分的地方。
3. 再把 `Input / Progress / Admin` 拉进同一张体验地图，补完整链路。
4. 最后做视觉与交互精品化，并用真实浏览器 + 正式 E2E 同时验收。

## Key Questions
1. 现场从输入到结果，用户能不能在不听解释的前提下直接看懂价值？
2. 弱结果、warmup、失败态有没有把“为什么这样、下一步怎么办”说清楚？
3. 页面现在是在帮用户判断，还是还在让用户自己读材料和做翻译？
4. 整条链路是不是已经完全摆脱 mock / 旧样本 / 假演示感？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 当前阶段先以“90 分验收基线”而不是“95/98 冲刺”组织工作 | 先把产品从“能用”推进到“可验收”，再谈精品化 |
| 把 `A_full` 稳定性放到第一优先级 | 没有真结果稳定性，前端体验再好也会继续像 demo |
| 把 UX 地图单列成独立阶段 | 现在最大缺口已经不只是单页，而是全链路节奏 |
| 正式验收必须同时看 live report、正式 E2E、真实浏览器 | 只看其中一项都会高估当前分数 |
| `开放提问 = 产品默认主链` | 用户不会按 `topic_profile` 思考，默认价值必须覆盖自由提问 |
| `topic_profile = 首页标准展示 / 黄金样板 / 加速路径` | 它负责展示产品上限，不负责定义产品边界 |
| `A/B/C/X` 必须由证据硬度决定 | 否则系统会把正常开放题误杀成“不会答” |
| `reports/t1价值的报告.md` 是 Full A 唯一内容结构标杆 | 后续 Full A/B/C 都必须围绕这份报告的 6 大结构组织，不再各走各路 |
| `canonical_report_json` 是唯一交付真相源 | 卡片和长报告都必须从同一份对象渲染，不能再双源语义 |

## Risks / Watchouts
| Risk | Handling |
|------|----------|
| 历史队列积压再次污染 live 验收 | 先做队列门禁和清淤，再跑 live |
| 页面文案越修越多 | 每次只保留“结论 / 证据 / 下一步”三层 |
| 视觉精修再次脱离真链路 | 所有页面必须用真实样本和真实状态截图验收 |
| 首页标准卡与 `topic_profile` 继续脱钩 | 把示例卡和黄金入口拆开，避免标准展示永远只是“填文字” |
| 无 `topic_profile` 任务继续被 fallback topic mismatch 误伤 | 先修 quality gate 合同，再修页面文案 |
| `X_blocked` 继续被前端伪装成“像结果页”的方向页 | 后端渲染与前端交付要一起改，不能只修一层 |
