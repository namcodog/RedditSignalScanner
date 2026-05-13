# phase693

## 本轮完成
- 对“情绪吐槽/社区礼仪抱怨被误发成信号卡”做了一次彻底核查。
- 已发布 `validate` 卡里，可疑集合收敛到 `6` 张，不是大面积跑偏。
- 明确撤掉一张偏方向的伪信号：
  - `card-cand-ai-automation-1sas9s3-validate`
  - 原因：本质是“标题党/社区礼仪吐槽”，不是市场信号。
- 新增 `meta_community_complaint` 质量闸门，拦住同类单帖单社区伪信号。
- 修复客户端文案 bug：
  - 删除 `lead -> 线索` 的危险全局替换，避免 `r/googleads` 被污染成 `r/goog线索s`
- 修复 `category-winds` 详情表达：
  - 不再把原帖类比（如“国际象棋”）直接端给用户
  - `pain_point / target_user_and_scene` 改成业务判断句

## 审计结论
- 当前严重问题存在，但不是“很多卡都偏了”，而是少量单帖卡混进了不该发的 meta 抱怨。
- 其余可疑卡大多仍属于有效信号：
  - 避坑信号
  - 替换信号
  - 求解法/求推荐信号
- 方向层现在更清楚：
  - 纯礼仪吐槽/社区情绪抱怨不再算信号
  - 真实的避坑、替换、回传缺失、安全性担忧仍算可发信号

## 验证
- `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_signal_input_quality.py tests/services/hotpost/test_card_content_generator.py -q`
- 结果：`28 passed`
- `published` 数量：`49 -> 48`

## 当前结果
- 前台文案边界继续保持：
  - 保留：`SEO / GEO / Ads`
  - 继续清理：`CAC / LTV / G2 / niche` 等黑话
- 情绪吐槽类卡片已被进一步收口：
  - 存量撤掉 1 张
  - 主链新增 1 条拦截规则
