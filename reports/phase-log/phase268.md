# Phase 268 - Round 5 第一阶段深修：报告 API 说真话

## 时间
- 2026-03-14

## 背景
- Round 5 审计在 `phase267.md` 已确认两条 live 报告 API 的 P0 问题：
  - `export_communities(scope=all)` 会把整张活跃 `community_pool` 混进“本次报告社区”
  - 社区明细和导出 fallback 没有明确来源标记
- 另外还有一个 P1 问题：
  - `download_report()` 在导出失败 fallback 时，把内部异常原文透给前端

## 本轮目标
- 只修 live 路由：`backend/app/api/v1/endpoints/reports.py`
- 不碰旧未挂载路由，不扩大到导入脚本
- 顺手把过长的社区导出逻辑拆成小 helper，降低阅读成本

## 实际改动

### 1. 真实报告社区不再掺假
- 新增 `_resolve_report_communities()`，统一社区来源口径：
  - 优先 `analysis.sources.communities_detail`
  - 缺失时降级到 `top_communities_fallback`
  - 如果 `overview.top_communities` 也空，再退到 `sources.communities` 名称清单
- `export_communities(scope=all)` 现在只导出本次报告真正涉及的社区
- 不再把整张活跃 `community_pool` 混进结果

### 2. 降级状态显式暴露
- `GET /api/report/{task_id}/communities`
  - 新增响应头：
    - `X-Communities-Source`
    - `X-Communities-Degraded`
- `GET /api/report/{task_id}/communities/export`
  - 响应体新增：
    - `source`
    - `degraded_reason`
- `GET /api/report/{task_id}/communities/download`
  - CSV 文件头部新增：
    - `source`
    - `degraded_reason`

### 3. 导出 fallback 不再泄露内部异常
- `download_report()` 现在 fallback 到 JSON 时：
  - 服务器端保留日志
  - 返回头改成通用错误码 `X-Export-Error=export_generation_failed`
  - 不再把 `str(exc)` 原文透给前端

### 4. 代码瘦身
- 从 `reports.py` 中抽出 5 个小 helper：
  - `_extract_pool_categories`
  - `_load_report_with_analysis`
  - `_build_fallback_community_details`
  - `_resolve_report_communities`
  - `_load_community_maps`
  - `_build_community_export_items`
- `backend/app/api/v1/endpoints/reports.py`
  - 行数从 `956` 降到 `892`

## 测试

### 新增/扩展测试
- `backend/tests/api/test_reports.py`
  - `test_get_report_communities_marks_fallback_source_when_detail_missing`
  - `test_export_communities_all_only_returns_report_communities`
  - `test_export_communities_all_marks_fallback_when_detail_missing`
- `backend/tests/api/test_report_export_markdown_and_fallback.py`
  - `test_download_report_markdown_fallback_hides_internal_error`

### 验证命令
```bash
python -m py_compile backend/app/api/v1/endpoints/reports.py backend/app/schemas/community_export.py backend/tests/api/test_reports.py backend/tests/api/test_report_export_markdown_and_fallback.py

cd backend && SKIP_DB_RESET=1 python -m pytest tests/api/test_reports.py tests/api/test_report_export_markdown_and_fallback.py -q

SKIP_DB_RESET=1 make test-quality-gate
```

### 结果
- `py_compile`：通过
- 报告 API 定向回归：`16 passed, 1 skipped`
- 质量门禁：`27 passed`

## 口径统一
- Round 5 第一阶段解决的是：
  - **报告 API 不再拿近似社区冒充真实报告事实**
  - **导出 fallback 不再把内部异常原文暴露给前端**

## 下一步
- Round 5 第二阶段：
  - 修高风险导入/恢复脚本
  - 加 Dev/Test/Gold 护栏
  - 默认 dry-run
  - 禁止 `restore_pool_hybrid.py` 默认恢复 ghost 社区
