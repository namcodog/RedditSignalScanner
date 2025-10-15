# Speckit 任务板 — 端到端验收（Lead）

> 追溯：PRD/PRD-INDEX.md、docs/2025-10-10-实施检查清单.md、docs/2025-10-10-质量标准与门禁规范.md

## 阶段与任务

- [ ] MCP 工具自检（Serena / exa-code / Chrome DevTools / Spec Kit）
  - 产出：`scripts/verify-mcp-tools.sh` 输出截图与结论
- [ ] 环境基线（Python3.11、Node、Postgres、Redis）
  - 产出：`Makefile env-check` 运行记录
- [ ] 后端启动与健康检查（8006）
  - 产出：`/api/healthz` 响应、OpenAPI 可访问
- [ ] 前端启动与健康检查（3006）
  - 产出：首页可打开、API 基地址指向 8006
- [ ] 认证与多租户（PRD-06）
  - 用例：注册/登录、不同用户隔离、Admin 邮箱白名单
- [ ] 任务创建与状态（PRD-02-Analyze/Status/Report + PRD-04）
  - 用例：/api/analyze → Celery → /api/status → /api/report
- [ ] SSE 实时通道（PRD-02 + ADR-002）
  - 用例：`/api/analyze/stream/{task_id}` 事件序列（connected/progress/completed）
- [ ] Reddit 数据抓取与分析引擎（PRD-03）
  - 用例：缓存优先、并发采集、关键词→筛选→排序→洞察
- [ ] Admin 后台（PRD-07/PRD-10）
  - 用例：模板下载、Excel 导入（dry_run/commit）、导入历史
- [ ] 前端页面完整链路（PRD-05）
  - 用例：输入页 → 等待页（SSE）→ 报告页
- [ ] Chrome DevTools MCP 端到端验证
  - 用例：打开 3006，跟踪网络与控制台，无报错
- [ ] 验收报告与问题闭环
  - 产出：`reports/phase-log/DAY12-END-TO-END-ACCEPTANCE-REPORT.md` 更新

## 四问记录模板（每条任务均需）
1. 通过深度分析发现了什么问题？根因是什么？
2. 是否已经精确的定位到问题？
3. 精确修复问题的方法是什么？
4. 下一步的事项要完成什么？

— 本任务板由 Lead 基于 Speckit 原则生成，随验收过程实时更新。

