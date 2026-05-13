# Phase 816 - Hot 真实争议占比真实验证

## 目标

- 用当前已发布的 `hot` 卡做真实 spot check。
- 验证三件事：
  - 评论样本能不能稳定抓到
  - 默认模型路由能不能直接跑通
  - 真实比例是否已经摆脱模板感

## 本次验证

先看前提：

- 当前已发布总卡：`185`
- 当前已发布 `hot`：`31`
- Reddit 凭证存在
- LLM 凭证存在

第一轮验证：

- 直接跑最近 5 张 `hot`
- 评论抓取都成功
- 但默认 `gemini-2.5-flash-lite` 被错路由到 OpenRouter/OpenAI 客户端
- 结果统一 `403`，`summary_status=llm_failed`

结论：

- 样本抓取没问题
- 真阻塞点是模型路由，不是评论链

## 修复

修改：

- [card_content_llm_router.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_content_llm_router.py)
- [test_card_content_llm_router.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_card_content_llm_router.py)

现在 plain `gemini-*` 也会走 Gemini 客户端，不再要求手工写 `google/` 前缀。

## 修复后 spot check

默认配置下，重新验证最近 5 张已发布 `hot`：

- `card-cand-ai-automation-1sk82sc-validate`
  - `sample_size=35`
  - `confidence=high`
  - `ratios=0.04 / 0.42 / 0.54`
- `card-cand-business-growth-ops-1sk5wuq-validate`
  - `sample_size=36`
  - `confidence=high`
  - `ratios=1.0 / 0.0 / 0.0`
- `card-cand-business-growth-ops-1sjw2o6-validate`
  - `sample_size=28`
  - `confidence=medium`
  - `ratios=0.54 / 0.17 / 0.29`
- `card-cand-ai-automation-1sjgwd1-validate`
  - `sample_size=11`
  - `confidence=low`
  - `ratios=0.18 / 0.0 / 0.82`
- `card-cand-ai-automation-1sfwj9j-validate`
  - `sample_size=32`
  - `confidence=high`
  - `ratios=0.12 / 0.5 / 0.38`

结果：

- 最近 5 张里 `5/5` 比例组合都不同
- 模板感已经被打散

## 当前问题

真实验证后，剩下的是质量问题，不是链路问题：

- `debate_focus` 偶发英文输出
- 个别卡出现 `1.0 / 0 / 0`
- `low sample` 卡容易被压成高比例中性

## 验证命令

```bash
cd backend && pytest tests/services/hotpost/test_card_content_llm_router.py -q
cd backend && python - <<'PY'
# 见 tmp/hot_controversy_validation_default_5cards_2026-04-14.json
PY
```

## 下一步

- 调整 `hot_controversy_llm.py` 的 prompt 与输出约束：
  - 强制中文输出
  - 没有反方时用更克制的语言
  - `low sample` 时把不稳定性表达得更明显
- 再抽最近 10 张 `hot` 做第二轮人工 spot check
