# Phase 451 - PayPal 第 2 张机会卡收尖到业务表达

## 发现了什么？

- PayPal `Full A` 的核心缺口确实不在前端，而在机会卡生成链：
  - `analysis.insights.opportunities` 里第 2 个机会原本还是英文帖子标题碎片
  - 即便 structured contract 能兜底，长报告里仍会残留 `先验证...帖 / 案例切入` 这类内部执行口吻
- 这意味着之前的 PayPal 样板还不能算 `100 分`：
  - 卡片标题不够尖
  - 长报告的商业机会段仍有机器味尾巴

## 是否需要修复？

- 需要，而且这轮已经把上游翻译、门禁和 live 复验一起收掉。

## 精确修复方法

### 1. 上游机会信号翻译

- 更新 `backend/app/services/analysis/analysis_engine.py`
- 新增：
  - `_translate_opportunity_signal()`
  - `_select_opportunity_channels()`
- 修复点：
  - 把 `need to enable international payments in Indian bank accounts` 这类英文帖子碎片，转成中文业务机会
  - 优先使用 source examples 的真实社区作为机会卡目标社群
  - 把翻译后的中文痛点和卖点，提前注入 `insights.opportunities`

### 2. 去掉机会段里的过程话

- 更新：
  - `backend/app/services/report/content_guardrails.py`
  - `backend/app/services/report/narrative_report_workflow.py`
  - `backend/app/services/llm/report_prompts.py`
- 新增坏文案门禁：
  - `先验证`
  - `案例切入`
  - `payout帖`
- narrative prompt 也同步改成：
  - 动作建议必须写成业务切入和用户收益
  - 禁止再写 `先去 r/xxx 分享案例切入 / 先验证某类 payout 帖`

### 3. 重跑真实 live，并更新 PayPal 标准快照

- 第 1 次复验：
  - `task_id=e707bf7c-aa88-4f4e-af53-5a7ed0e0bc38`
  - 第 2 张卡已从英文碎片收成 `国际收款开通助手`
  - 但长报告里仍残留 `先验证印度用户payout帖`
- 第 2 次复验（新门禁生效后）：
  - `task_id=86087efe-8651-415f-a0ba-1b748fe6fb5f`
  - `A_full`
  - `llm_used=true`
  - 第 2 张卡收成：
    - `国际收款开通诊断`
    - `对应痛点：国际收款开通和费用复杂、Stripe payout失败、国际收款开通受阻`
    - `产品定位：诊断银行/PayPal开通状态，切低费替代`
  - 长报告商业机会段已不再出现 `先验证...帖 / 案例切入`
- 已同步更新标准快照：
  - `frontend/public/topic-profile-reports/cross-border-paypal.json`
  - `frontend/public/topic-profile-reports/index.json`

## 验证

- analysis 定向测试：
  - `cd backend && ../.venv/bin/pytest tests/services/analysis/test_analysis_engine.py -q -k 'translate_opportunity_signal or select_opportunity_channels'`
  - `2 passed`
- prompt / guardrails 定向测试：
  - `cd backend && ../.venv/bin/pytest tests/services/report/test_content_guardrails.py tests/services/llm/test_report_prompts_v9.py -q`
  - `12 passed`
- live preflight：
  - `make test-e2e-live-report-cleanup-apply && make test-e2e-live-report-preflight`
  - `ok=true`
- 真实 live：
  - `run_live_report_acceptance.py --product-description '帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。' --topic-profile-id cross_border_payment_v1`
  - 首轮直出 `A_full`
  - 新任务：`86087efe-8651-415f-a0ba-1b748fe6fb5f`

## 下一步系统性的计划是什么？

1. 保持 PayPal 这条样板不再回退。
2. 把同一套“英文碎片机会 -> 中文业务机会”的翻译逻辑继续观察到其他标准卡。
3. 再开始刷新剩余 5 张标准快照，避免首页只有 PayPal 是新口径。

## 这次执行的价值是什么？

- 这轮不只是“PayPal 第 2 张卡变好看了”，而是把 `Full A` 的一个真实漂移源头掐掉了。
- 现在 PayPal 标准样板里，第 2 张机会卡终于开始像商业机会，而不是 Reddit 帖子标题和内部动作提示的拼接物。
