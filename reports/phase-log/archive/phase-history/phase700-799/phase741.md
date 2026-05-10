# Phase 741

## 发现了什么

- `1.0` 阶段真正缺的不是“更像报告的文案”，而是三件事一起收口：
  - `hot` 门禁降一档
  - 文案更像“转给朋友”
  - 调度器按最近 `20` 张真实发布时间算 mix
- 这轮修完后，`runtime hot` 审计已经从之前的薄供给长到：
  - `runtime_hot_total = 6`
- validate 队列前排也不再被 `signal` 完全挤死，第一条已经是 `hot` 候选：
  - `cand-ai-automation-1sgojy9`
- 另外炸出一个隐藏 bug：
  - 最近 `20` 张 mix 之前一直算歪，不是口径错，而是 `card_selection_policy.py` 拿了文件尾部顺序，不是真实发布时间
  - 还有 `write` 卡历史上有 `25` 条被写成 `lane=None` 或 `lane=signal`

## 是否需要修复

- 这轮主问题已经修掉：
  - `hot` 不再被过高门禁堵死
  - 文案口径已经正式切成 `1.0` 密度优先
  - 最近 `20` 张的 lane / scope 终于按真实发布时间在算
- 但 lane mix 还没回目标：
  - 当前最近 `20` 张是 `signal=15 / hot=4 / breakdown=1`
  - 领域是 `AI=9 / 增长=6 / 电商=5`

## 精确修复方法

- 新增合同：
  - `docs/superpowers/specs/2026-04-09-v1-density-first-contract.md`
- 更新制度层：
  - `docs/sop/2026-04-09-稳态运营成功SOP.md`
  - `docs/sop/2026-04-09-爆贴热点运营SOP.md`
  - `.agents/skills/hot-ops/SKILL.md`
  - `AGENTS.md`
- 语义层继续收口：
  - `backend/config/prompt_assets/reddit_guide_thinking_contract.md`
  - `backend/config/card_content_rules.yaml`
  - `backend/app/services/hotpost/card_content_prompts.py`
- 调度器关键修复：
  - `backend/app/services/hotpost/card_selection_policy.py`
  - 最近 `20` 张改成按 `published_at` 排序后再截窗
- `breakdown` lane 写回修复：
  - `backend/app/services/hotpost/card_content_generator.py`
  - `write` 草稿统一强制 `lane=breakdown`
- 历史发布集回填：
  - 已把 `25` 条 `write` 卡回填成 `lane=breakdown`
- 新发 1 张 `hot`：
  - `card-cand-ai-automation-1sgojy9-validate`
  - 标题：`Anthropic 这波宣传又把用户惹毛了，评论区开始喊“狼来了”`
- 最新快照已对齐：
  - `release-f979b0a4689b`
  - `card_count = 95`

## 下一步系统性的计划

1. 继续优先补 `hot + breakdown`，停止继续补 `signal`。
2. 利用现在已经长到 `6` 条的 `runtime hot`，继续挑第二张、第三张可发热点卡。
3. 把最近 `20` 张从 `15 / 4 / 1` 继续往 `10 / 6 / 4` 拉。
4. 领域上优先补：
   - `增长`
   - `电商`
   避免继续把最近 `20` 张推成 `AI` 偏重。

## 这次执行的价值

- 这轮真正收掉的不是一两个文案问题，而是把 `1.0` 产品态从“过高门禁 + 伪最近窗口 + breakdown lane 记错”拉回到了正确轨道。
- 现在系统终于开始同时满足三件事：
  - 热点能长
  - 文案更像人
  - 调度按真实最近 `20` 张工作
