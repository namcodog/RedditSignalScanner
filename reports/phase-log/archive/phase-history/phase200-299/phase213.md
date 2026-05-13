# Phase 213

## 目标
- 进行“爆帖速递”最终验收（后端 + 最小流程）。

## 验收范围
- 配置核对（.env 关键键）
- 后端 hotpost 单测 + API 测试
- 一次真实流程（中文问题）

## 执行记录
- 配置核对：
  - backend/.env 存在
  - OPENROUTER_API_KEY 存在（OPENAI_API_KEY 不存在）
  - REDDIT_CLIENT_ID/SECRET/USER_AGENT 存在
  - OPENAI_BASE 存在
- 单测：
  - pytest backend/tests/services/hotpost -q （20 passed）
  - pytest backend/tests/api/test_hotpost.py -q（1 passed）
  - 警告：pytest config / pydantic / fastapi deprecation 警告（不影响结果）
- 真实流程：
  - 查询："最近 AI 工具领域有什么热门讨论？"（mode=trending）
  - 结果：from_cache=True（首次执行后缓存命中）
  - summary：找到 30 条相关讨论，来自 3 个社区。
  - top_posts=30，key_comments=5
  - LLM 结果：topics=0，trending_keywords=None
  - 原因：首次执行时 LLM 调用返回 401（"No cookie auth credentials found"），导致 LLM 报告未生成

## 结论
- 数据抓取与缓存流程可用；后端核心测试通过。
- LLM 报告未生成（topics/keywords 为空），需要修复 LLM 认证/路由后才算“完整验收通过”。

## 待处理
- 核实 LLM 调用的认证与基址（OPENAI_BASE 指向 openrouter，且 key 有效）。
- 修复后复跑一次相同查询，确认 topics/keywords 正常产出。

## 补充修复
- 发现 OPENAI_API_KEY 在运行环境中仍有值（长度 24），优先级覆盖 OPENROUTER_API_KEY，导致 OpenRouter 401。
- 通过在运行进程中清空 OPENAI_API_KEY（仅保留 OPENROUTER_API_KEY）后，LLM 产出恢复正常。

## 复跑结果（修复后）
- 查询："最近 AI 工具领域有什么热门讨论？"（mode=trending）
- from_cache: False
- summary：本周Reddit AI工具热点：Moltbot爆火、AI代理系统创新、ML学术论文争议、Google代理AI进展。
- top_posts=30，key_comments=5
- trending_keywords：['Moltbot', 'AI agents', 'LAD-A2A', 'OpenClaw', 'Gemini 3 Flash', 'AI slop', 'YOLO', 'RL post-training', 'photo to video', 'AAAI awards']
- topics=5（示例：AGI路径投资与奇点 hype / Moltbot安全担忧 / ML学术AI slop论文担忧 / AI代理构建 / 实用视觉训练工具）

## 最终结论
- LLM 报告生成已恢复，满足验收要求。

## 补充产物
- 生成并保存报告：`reports/2026-02-02-Reddit-中国文化-爆帖速递报告.md`

## 前端构建验收补记
- 前端同学反馈构建已通过（npm run build），TS 错误已清零。
- 记录来源：`reports/phase-log/phase214.md`
