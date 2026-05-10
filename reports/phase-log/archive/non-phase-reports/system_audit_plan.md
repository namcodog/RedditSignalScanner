# 系统全量审计扫描计划

## 背景

截至 Phase 247，已完成的修复/审计覆盖了部分核心模块。本计划排除这些模块，对剩余代码做**有节奏的分批审计**。

---

## 已修复/已审计（排除范围）

| 模块 | 修复内容 | Phase |
|------|---------|-------|
| `generate_t1_market_report.py` | 确定性协议 + NOW() 消除 + 11 处修复 | 240/244 |
| `t1_stats.py` | 10 处 NOW() 消除 | 240 |
| `embedding_task.py` | NOW() 治理 | 246 |
| `analysis_engine.py` (部分) | unique_authors 修复 + SQL tie-breaking | 238-239 |
| `report_service.py` (部分) | 本次已做 Serena 符号级分析 | 本次 |
| `crawl_execute_task.py` | 本次已做 Serena 符号级分析 | 本次 |
| `maintenance_task.py` | 本次已做 Serena 符号级分析 | 本次 |

---

## 扫描计划（5 轮）

### Round 1: 数据采集层（最高业务风险）
> 数据不准 = 后面全错

| 文件 | 行数 | 说明 |
|------|------|------|
| `services/crawl/` | 17 文件 / 5,435 行 | 爬虫核心：增量抓取、数据入库、去重 |
| `tasks/crawler_task.py` | 1,696 行 | 爬虫调度 |
| `tasks/comments_task.py` | 582 行 | 评论抓取 |
| `tasks/ingest_task.py` | 273 行 | 数据写入 |

**方法**: Serena `get_symbols_overview` → 重点函数 `find_symbol` + `include_body` → 异常处理模式审查
**交付**: 每个模块的健康卡片（行数/函数数/裸SQL/吞错误/风险评级）
**预估**: ~30 分钟

---

### Round 2: 数据加工层（核心算法）
> 算法错 = 结论错

| 文件 | 行数 | 说明 |
|------|------|------|
| `services/analysis/` (除 analysis_engine) | ~8,600 行 | 统计、聚类、痛点分析、信号提取 |
| `services/facts_v2/` | 3 文件 / 1,034 行 | V2 事实生成 |
| `tasks/analysis_task.py` | 1,334 行 | 分析调度 |

**方法**: 同上 + 重点看数据流转（哪些函数消费 analysis_engine 的输出）
**交付**: 函数依赖图 + 健康卡片
**预估**: ~30 分钟

---

### Round 3: 社区治理 + 语义层
> 社区选错 = 数据源错

| 文件 | 行数 | 说明 |
|------|------|------|
| `services/community/` | 7 文件 / 2,592 行 | 社区池、黑白名单、角色 |
| `services/semantic/` | 15 文件 / 2,914 行 | embedding、检索、匹配 |
| `services/discovery/` | 4 文件 / 867 行 | 社区发现 |
| `services/evaluation/` | 1 文件 / 209 行 | 社区评估 |
| `tasks/semantic_task.py` | 263 行 | 语义调度 |
| `tasks/scoring_task.py` | 169 行 | 评分调度 |

**方法**: Serena 符号分析 + 配置文件引用追踪
**交付**: 健康卡片 + 配置依赖图
**预估**: ~25 分钟

---

### Round 4: 子系统（爆帖 + LLM + 基础设施）

| 文件 | 行数 | 说明 |
|------|------|------|
| `services/hotpost/` | 12 文件 / 3,354 行 | 爆帖检测（已有架构文档） |
| `services/llm/` | 14 文件 / 2,282 行 | LLM 调用、标签生成 |
| `services/infrastructure/` | 12 文件 / 2,597 行 | Reddit 客户端、缓存、监控 |
| `tasks/llm_label_task.py` | 1,014 行 | LLM 标签调度 |
| `tasks/monitoring_task.py` | 836 行 | 监控调度 |

**方法**: Serena 符号分析 + 错误处理模式审查
**交付**: 健康卡片
**预估**: ~25 分钟

---

### Round 5: API 层 + 高风险脚本

| 文件 | 行数 | 说明 |
|------|------|------|
| `api/v1/endpoints/reports.py` | 956 行 | 报告 API |
| `api/routes/admin_community_pool.py` | 922 行 | 社区管理 API |
| `api/routes/reports.py` | 838 行 | 旧版报告路由 |
| `scripts/report/` | 高风险脚本 | 报告生成脚本 |
| `scripts/import/` | 数据导入 | 标签导入等 |

**方法**: Serena 符号分析 + 接口安全审查（权限/校验）
**交付**: 健康卡片 + API 安全清单
**预估**: ~20 分钟

---

## 审计维度（每个模块统一检查）

1. **结构**: 行数、函数数、嵌套深度、内嵌子函数
2. **健壮性**: except...pass 数量、裸 SQL 数量、type:ignore 数量
3. **可维护性**: import 数量、函数间耦合度、重复代码模式
4. **业务风险**: 该模块出 bug 会影响哪些下游

## 输出

每轮产出一个 `phase-log/audit_round_N.md`，包含各模块的健康卡片和风险排名。
5 轮全部完成后，输出一份**系统健康总表**。
