# Phase 241 — 代码质量清理 (ORM + 配置化 + 可观测性)

> 执行时间: 2026-03-12
> 来源: Phase 238/239 遗留待做事项 #3 #4 #5

## 完成项

### #3 facts_quality_audit ORM Model
- 新建 `backend/app/models/facts_quality_audit.py`（`mapped_column` 现代语法）
- `_write_quality_audit()` 裸 SQL INSERT → `session.merge(FactsQualityAudit(...))`
- `__init__.py` 已注册

### #4 品牌噪音词配置化
- 新建 `backend/config/brand_noise.yaml`（146 行，含 AI 协作注释）
- `general` 113 词 + `operations` 24 词
- `_load_brand_noise()` 函数替换硬编码
- 改词不再需要发版

### #5 品牌发现可观测性日志
- 3 处日志：加载摘要 + 过滤前后统计 + Top brands 列表
- 实跑输出示例：
  ```
  📋 Brand noise loaded: 113 words (mode=market_insight)
  🏷️ Brand filter: 12 → 9 kept, 3 noise filtered
     Top brands kept: ['Habitat', 'Dawn', 'Bona', ...]
  ```

## 验证结果
- AST: ✅
- ORM 导入: ✅
- YAML 加载: ✅ (general=113, operations=24)
- 定向回归: 14 passed ✅
- quality-gate: 24 passed ✅
- check-determinism: PASS ✅
- 确定性回归: 4 passed ✅
