# Phase 655 - Card Skill Optimization 标准版合同

## 结果

围绕 `AI_Skill_Optimization_Deep_Dive_Report`、`evals-skills` 和 `autoresearch`，
已经把“卡片生成工作流”的标准版优化路线收成正式合同。

最终选择：

- 不走轻量人工补丁版
- 不走激进全自动版
- 选择 **B. 标准版**

即：

- 先建立卡片 eval 体系
- 再校准 judge
- 最后才让 autoresearch 进场优化 signal skill

## 核心判断

最关键的结论不是“怎么让 AI 更会写卡”，而是：

**不能在没钉死靶子的前提下，把整个卡片链交给自动优化。**

当前真正该优化的对象只有：

- `card_content_prompts.py`
- `card_content_polish.py`
- `card_content_rules.yaml`

而不是：

- collect
- publish
- topic-pack
- suggestion 门槛

## 正式文档

落点：

- `docs/superpowers/specs/2026-04-07-card-skill-optimization-design.md`

## 当前决策

1. 先只做 `signal skill optimization`
2. 先建 `signal eval set v1`
3. 先做人工 error analysis 和 failure taxonomy
4. judge 先校准，再允许 autoresearch 式循环
5. 所有优化都先离线评估，再 canary，再 promote

## 当前判断

这轮之后，“怎么优化卡片 skill”这件事已经不再是口头共识，而是正式基线。

下一步最值钱的动作不是改 prompt，而是：

- 建第一版 `signal eval set`
- 开始人工读卡建失败分类
