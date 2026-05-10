# Phase 643 - 需求信号卡尾巴收口

## 结果

按第二次合同审计留下的尾巴，继续做了一轮定点精修。

这轮之后：

- `summary_line` 里残留的 `subreddit + 英文原话直抄` 已清零
- 报告腔标题已清零
- 超长标题已清零

## 本轮改动

- 不动结构
- 不动 prompt
- 只对现有 34 张 published 卡做定点 override 精修：
  - `title`
  - `summary_line`

同时顺手清掉了 `card_content_polish.py` 里少量重复 key，避免后写入的旧值把新文案覆盖回去。

## 验证

- `python backend/scripts/polish_hotpost_cards.py`
  - `{"polished": 34}`
- 抽检统计：
  - `summary_has_subreddit = 0`
  - `summary_has_raw_english_quote = 0`
  - `title_too_reporty = 0`
  - `title_too_long = 0`
- 8006 首页接口已返回这轮新文案

## 当前判断

这一轮之后，现有 34 张卡片的“尾巴问题”已经基本收平。

后面如果继续推进，优先级才会真正回到：

- prompt 总体升级
- 新卡自动生成质量
