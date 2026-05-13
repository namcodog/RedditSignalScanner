# Brand Intelligence R15 全面审计

日期：2026-05-13

## 审计范围

本次覆盖 R15.0-R15.4：品牌来源归一、质量审查、Dev DB 注册表、日常 sidecar、只读服务/API、CLI 预览、报告产物和验证链路。

## 当前事实

- 当前 DB 已核实为 `reddit_signal_scanner_dev`。
- `brand_registry=1655`，全部为 active。
- `brand_mentions=1254`。
- 注册表状态分布：`accepted=1457 / verified=13 / candidate=2 / match_guarded=58 / canonical_review=81 / metadata_review=44`。
- R15.3 sidecar 扫描 `881` 张已发布 Hotpost 卡，识别 `171` 个品牌，质量审查结果为 `verified=13 / candidate=142 / rejected=16`。
- R15.4 consumer-safe 默认预览返回 `13` 个 verified 品牌和 `710` 条证据。
- R15.4 报告明确 `db_writes=false / consumer_profile=consumer_safe / field_contract_version=brand-consumer-v1 / miniapp_snapshot_fields=false`。

## 问题清单

### P1 - 已修复：API / CLI 默认结果不是产品安全结果

`/brand-intelligence/registry` 和 `preview_brand_registry.py` 已默认使用 `consumer_safe` profile。默认读取只返回 `verified` 品牌；如果显式传入非 consumer-safe 状态，会返回空结果，不会把 `accepted / match_guarded / canonical_review` 混进产品消费面。

内部注册表查看仍保留在 CLI：`--profile internal_registry`。API 暂不暴露 profile 参数，避免前端或小程序误读内部治理字段。

验证：默认 `make brand-registry-view BRAND_ARGS='--limit 30 ...'` 返回 `13` 个品牌，`evidence_status` 唯一值为 `verified`，且不含 `review_status / domains / risk_flags / source_lifecycle`。

### P1 - 已修复：消费字段还不是正式产品合同

consumer-safe 输出已改为产品消费字段：

- `display_name`
- `business_domains`
- `interest_tags`
- `evidence_status`
- `display_status`
- `mention_count`

内部字段 `canonical_name / domains / review_status / source_lifecycle / risk_flags` 只在 `internal_registry` profile 下输出。

### P2 - 已修复：直接运行脚本时可能太晚加载 DB 环境

已调整 Brand Intelligence DB 脚本，在 import `SessionFactory` 前先执行 `load_backend_env()`。覆盖脚本：

- `preview_brand_registry.py`
- `generate_brand_ops_sidecar.py`
- `write_brand_registry_dev.py`

### P2 - 当前索引够用，但不够未来 API 高频读取

R15.4 会按 `BrandRegistry.interest_tags.contains(...)` 过滤，也会按 `BrandMention.brand_key` 统计证据。当前数据量很小，问题不明显；但迁移里没有给 `interest_tags` 加 GIN 索引，也没有给 `brand_mentions.brand_key` 加直接索引。

建议：真正开放 API 流量或数据量变大前补索引。

### P2 - 高证据 archive 候选需要人工晋级通道

当前质量合同故意不让 archive-only 品牌自动变成 `verified`，这是对的，可以防污染。但副作用是：有些证据很多的候选品牌仍然不会出现在 verified-only 预览里。

建议：增加一个“高证据候选晋级审核队列”，不要只靠 `verified` 或原始 `accepted` 两档。

## 通过项

- Brand Intelligence 生产 Python 里没有发现硬编码品牌清单。
- R15.4 reader/API 是只读；写库逻辑隔离在 `brand_registry_writer.py`。
- 已检查的 Brand Intelligence 源码和测试文件都不超过 `200` 行。
- consumer-safe 报告数字和 DB 查询一致：verified 预览为 `13` 个品牌、`710` 条证据。
- 默认消费输出不再暴露内部治理字段；内部查看必须显式走 `--profile internal_registry`。
- 小程序 snapshot 字段仍然关闭，没有提前污染小程序。

## 验证证据

- `PYTHONPATH=backend SKIP_DB_RESET=1 pytest backend/tests/models/test_brand_registry_models.py backend/tests/services/brand_intelligence backend/tests/api/test_brand_registry_api_contract.py -q`
- `make brand-registry-view BRAND_ARGS='--status verified --limit 30'`
- `make brand-registry-view BRAND_ARGS='--limit 30 --json-output /tmp/brand-registry-consumer.json --md-output /tmp/brand-registry-consumer.md'`
- `make brand-registry-view BRAND_ARGS='--profile internal_registry --limit 20 --json-output /tmp/brand-registry-internal.json --md-output /tmp/brand-registry-internal.md'`
- `cd backend && mypy --strict --follow-imports=skip app/services/brand_intelligence/brand_consumer_profile.py app/services/brand_intelligence/brand_registry_reader.py scripts/brand_intelligence/preview_brand_registry.py scripts/brand_intelligence/generate_brand_ops_sidecar.py scripts/brand_intelligence/write_brand_registry_dev.py app/api/v1/endpoints/brand_intelligence.py tests/services/brand_intelligence/test_brand_registry_reader.py tests/services/brand_intelligence/test_brand_script_env_order.py tests/api/test_brand_registry_api_contract.py`

已知限制：完整导入版 mypy 加 `--follow-imports=silent` 仍会卡在第三方 `transformers.models.sam_hq.processing_samhq` 的 mypy 内部错误；崩溃前没有报 Brand Intelligence 源码错误。

## 结论

R15.4 作为“后端只读注册表服务”成立；审计发现的两个 P1 已收口为 consumer-safe 默认合同。现在可以把它作为后续前端 / 小程序读取品牌池的后端底座，但还没有接小程序 snapshot，也还没有做 UI。剩余风险是后续流量索引和高证据候选人工晋级队列。
