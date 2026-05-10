# phase720 - Reddit 带路人角色 prompt 设计收口

## 本轮完成

- 明确了产品本质：
  - 不是“AI 摘要器”
  - 而是“一个很懂 Reddit、很会逛 Reddit、能带用户发现 Reddit 价值的人”
- 明确了这份角色 prompt 的正确位置：
  - 不能一锅端
  - 必须拆成：
    - 角色底座
    - 判断协议
    - 输出模式
- 新增设计稿：
  - `docs/superpowers/specs/2026-04-09-reddit-guide-role-prompt-design.md`

## 这轮确认的关键边界

- 角色 prompt 很重要，但不能替代供给合同
- 社区池 / 关键词 / source mode 继续归 YAML，不准塞回 prompt
- 角色层负责“像谁说话”
- 判断层负责“什么算 signal / hot / breakdown / 正确的废话”
- 输出层负责“每类卡怎么写”

## 下一步

- 从这份设计稿继续拆：
  - `reddit-guide-soul-prompt.md`
  - `reddit-guide-thinking-contract.md`
- 再决定哪些内容进系统 prompt，哪些内容进 lane / judge / SOP
