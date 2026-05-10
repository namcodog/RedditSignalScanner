# phase722 - 爆贴热点独立运营 skill 与 YAML 丰富度审计

## 本轮完成

- `爆贴热点` 已从 `signal-ops` 里拆成独立运营 skill：
  - `.agents/skills/hot-ops/SKILL.md`
- 新增独立运营 SOP：
  - `docs/sop/2026-04-09-爆贴热点运营SOP.md`
- `signal-ops` 已收窄回只处理 `信号快报`
- `AGENTS.md` 与稳态运营 SOP 已同步到三 skill 口径：
  - `signal-ops`
  - `hot-ops`
  - `breakdown-ops`

## 这轮确认的关键边界

- `爆贴热点` 现在要“操作分家”，但不“系统分家”。
- 底层仍然是：
  - `validate + lane=signal`
  - `validate + lane=hot`
  - `write + lane=breakdown`
- 运营层已经独立：
  - `signal-ops` 不再处理 hot
  - `hot-ops` 只处理 listing-first 高热帖

## YAML 丰富度硬审计

- 当前 `hotpost_supply_discovery_v2.yaml` 已明显比旧硬编码宽：
  - `ai-automation`：`6` 个题材簇 / `15` 个社区 / `25` 个命名实体 / `85` 条关键词
  - `ecommerce-sellers`：`7` 个题材簇 / `27` 个社区 / `85` 条关键词
  - `business-growth-ops`：`5` 个题材簇 / `19` 个社区 / `82` 条关键词
  - 全局去重后社区总数：`59`
- 但它还不算“已经足够丰富”：
  - 电商和增长的 `named_entities` 还是 `0`
  - 说明这两条线现在更多是泛题材和泛社区覆盖，还没把关键对象、关键人、关键项目名拉进来
  - 这会继续限制抓取面

## 当前结论

- `hot-ops` 现在值得独立成 skill / workflow / SOP
- YAML 现在已经比旧主链强很多，但还没有宽到“可以放心说料面够了”
- 后续主线继续是：
  - 补宽 supply contract
  - 然后再跑运营

## 下一步

- 继续给 `ecommerce / growth` 补 `named_entities`
- 继续扩长尾社区和对象词
- 再用新的 supply contract 跑 collect，看真实新料面是不是明显变宽
