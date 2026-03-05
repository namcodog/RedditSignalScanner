# Scripts 目录索引

> 所有运维脚本按业务域分目录，方便 AI 和人类快速定位。

| 目录 | 用途 | 文件数 |
|------|------|--------|
| `crawl/` | 抓取相关（单次/批量/增量/热启动） | ~9 |
| `semantic/` | 语义管线（词库构建/评分/验收/批量） | ~10 |
| `import/` | 数据导入/迁移/回填 | ~10 |
| `report/` | 报告生成/导出/审计 | ~7 |
| `scoring/` | 评分策略（OpenRouter/本地/对比） | ~7 |
| `community/` | 社区池管理（统计/差异/提案/抓取） | ~10 |
| `monitor/` | 监控/健康检查/验证 | ~6 |
| `seed/` | 测试种子/验收测试 | ~7 |
| `infra/` | DB 维护/配置/清理 | ~7 |
| `archive/` | 归档旧脚本 | - |
| `maintenance/` | 维护工具 | - |

## 常用命令

### 生成市场报告
python backend/scripts/report/generate_t1_market_report.py --topic "xxx" --mode market_insight

### 一次性抓取
python backend/scripts/crawl/crawl_once.py --scope all

### 社区池统计
python backend/scripts/community/pool_stats.py

### Celery 健康检查
python backend/scripts/monitor/check_celery_health.py
