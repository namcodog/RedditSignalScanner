# Phase 640 - 需求信号卡第二轮精修

## 结果

- `intent taxonomy` 已经前后端对齐：
  - signal meter
  - detail intent 文案
  - `why_now` 生成逻辑
- `audience` 已从“社区/帖子描述”收成“谁在聊”
- 详情页残留的“动作建议 / 写作工具”旧心智已收掉

## 本轮改动

- 后端：
  - 扩展 `why_now` 的 intent 解释，覆盖新标签体系
  - 给 `audience` 增加专门的人话清洗
  - 补强 prompt，禁止新卡再把 subreddit / 帖子 / 评论区写进 `audience`
- 前端：
  - signal meter / intent 文案跟上新标签
  - 详情页标题改回“判断卡”口径

## 验证

- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_card_content_generator.py -q`
  - `7 passed`
- `python backend/scripts/polish_hotpost_cards.py`
  - `{"polished": 34}`
- 抽检结果：
  - `34/34` published 卡的 `audience` 不再残留 `r/... / 帖子 / 评论区 / 吐槽 / 分享帖`
  - `why_now` 不再残留内部规则词
  - 8006 接口已返回这轮重刷后的新文案

## 当前判断

这轮已经不是“补文案”，而是把第二层合同硬化完了：

- 先前审计里最大的两个漏项：
  - `intent taxonomy` 漂移
  - `audience` 仍像社区枚举
- 现在都已经收口

## 下一步

- 不再继续改结构
- 直接进入首页前几张卡的第三轮“锋利度”精修
