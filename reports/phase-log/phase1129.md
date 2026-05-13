# phase1129 - Brand Intelligence R15.4 只读消费服务

- 这轮达到的目的：让主系统、小程序和其他支线能读同一个品牌注册表，而不是各自维护品牌清单。
- 当前状态变化：新增 `brand_registry_reader` 只读服务、`/brand-intelligence/registry` API 和 `make brand-registry-view` 预览命令。
- 今日 verified 预览：`returned_brands=13 / mention_count=710 / db_writes=false / miniapp_snapshot_fields=false`，报告在 `reports/brand-intelligence/brand-registry-view-2026-05-13.md/json`。
- 边界：本轮不写 Gold DB、不写小程序 snapshot、不自动写语义库；小程序展示字段仍需产品评审。
- 下一步：评审品牌消费字段，再把品牌注册表接到推荐解释、卡片证据和语义审核里。
