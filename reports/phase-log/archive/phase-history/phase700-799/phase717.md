# phase717 - hot lane sop addendum + “正确的废话” boundary

## 本轮完成

- 新增热点 lane 补充 SOP：
  - [docs/sop/2026-04-09-爆贴热点补充SOP.md](../..//docs/sop/2026-04-09-%E7%88%86%E8%B4%B4%E7%83%AD%E7%82%B9%E8%A1%A5%E5%85%85SOP.md)
- 把“正确的废话”收成硬边界，接入：
  - `评审与发布 SOP`
  - `card_content_rules.yaml`
  - `card_content_prompts.py`
  - `signal-ops` 读取入口

## 核心边界

### 爆贴热点

- 讲这帖为什么火
- 讲大家主要在吵什么
- 不等于“更热的信号快报”

### 正确的废话

- 观点即使正确
- 但如果读完没有新增判断
- 只是把大家都知道的常识顺着说一遍
- 一律算失败

## 验证

- `python -m py_compile backend/app/services/hotpost/card_content_prompts.py`
- 结果：通过

## 下一步

- 继续稳态运营
- 重点观察：
  - 新卡里“正确的废话”是否明显下降
  - `爆贴热点` 是否能在新边界下继续自然增长
