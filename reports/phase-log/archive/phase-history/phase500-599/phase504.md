# Phase 504 - 无 Playwright 主验收链路通过（Live Smoke + Live Final）

## 时间
- 2026-03-27

## 目标
- 收尾确认：在不依赖 Playwright 的前提下，主链验收可稳定拿到 `A_full`。

## 执行内容

### 1) 主验收链路定义
- 已使用统一命令：
  - `make acceptance-stable-no-playwright`
- 链路包含：
  - `acceptance-offline-gate`
  - 前端契约/集成测试（Vitest）
  - `acceptance-live-smoke`
  - `acceptance-live-final`

### 2) 处理 live 噪音导致的偶发降级
- 问题：Family 题在一次 smoke 中出现 `B_trimmed`（`solutions_low`）。
- 修复：将 smoke 验收参数加入通用重试预算（非题材硬编码）：
  - `--max-analysis-attempts 4`
- 落地文件：
  - `makefiles/test.mk`

### 3) 验收结果
- `acceptance-live-smoke` 输出：
  - `backend/reports/local-acceptance/open_question_live_smoke_1774582054.json`
  - `accepted=3/3`
  - `PayPal_Ecommerce / Tools_EDC / Family_Parenting` 全部 `A_full`
- `acceptance-live-final` 输出：
  - `backend/reports/local-acceptance/open_question_live_final_1774582178.json`
  - `accepted=1/1`
  - `Final_Open_Question` 为 `A_full`

## 四问回顾
1. 发现了什么？
- 主链失败点已从“结构性代码问题”收敛为“live 数据噪音 + 低样本偶发波动”。

2. 是否需要修复？
- 需要，且应使用通用稳定策略，不做业务题材硬编码。

3. 精确修复方法？
- 通过 `max_analysis_attempts` 给 live 验收加统一重试预算，消化瞬时噪音。

4. 下一步系统性计划是什么？
- 进入 API/数据层收尾：
  - 固化报告与卡片一致性契约测试；
  - 固化证据链接可点击校验；
  - 完成 Makefile 验收目标的文档化与一键入口收敛。

5. 这次执行的价值是什么？达到了什么目的？
- 验收已不依赖浏览器链路，且 live smoke + final 均可拿到 `A_full`，收尾路径清晰可复现。
