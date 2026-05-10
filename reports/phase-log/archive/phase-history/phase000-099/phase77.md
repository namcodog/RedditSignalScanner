# phase77 - 数据采集降级可见化（点2）

## 目标
- 让缓存/限流导致的“降级”不再悄悄发生
- 让命中率与报告展示更真实

## 发现的问题 / 根因
- `cache_hit_rate` 在分析阶段被强行抬到 >=0.9，真实命中被遮蔽。
- 旧缓存兜底与 API 限流只记录在内部字段，报告里没有直观提示。

## 精确定位
- `backend/app/services/analysis_engine.py` 的 cache_hit_rate 归一化逻辑
- `report_html` 没有对 stale cache / rate limit 做可读提醒
- `SourcesPayload` 与 `ReportService._normalise_sources` 未暴露采集预警字段

## 修复方法
- `cache_hit_rate` 改为真实值（按缓存命中帖子比例计算），不再硬抬到 0.9。
- 新增 `collection_warnings` 字段，包含降级原因的稳定标记。
- 报告 HTML 增加“数据提醒”区块，显示缓存过期/旧缓存兜底/API 限流等问题。
- `SourcesPayload` 与 `ReportService._normalise_sources` 放行 `collection_warnings`。
- 更新相关测试的 cache_hit_rate 断言为范围校验。

## 测试
- `python -m pytest backend/tests/services/test_analysis_engine.py::test_run_analysis_records_collection_warnings_when_fallback_used`
- `python -m pytest backend/tests/services/test_analysis_engine.py::test_run_analysis_fast_with_mocked_database`

## 结果
- 降级原因可被明确识别并展示，不再“悄悄变薄”。
- cache_hit_rate 显示为真实值，避免误导。
