# phase719 - Signal Supply Contract V2 侦查与 YAML 草案

## 本轮完成

- 用 Tavily 对 AI / 电商 / 增长三大领域做了一轮 supply 侦查，不再停留在泛 pack 名。
- 明确了当前真问题：
  - 题材面窄
  - 社区池窄
  - 关键词桶窄
  - 来源模式窄
  - 而且这些边界被直接写在 Python 里。
- 新增配置草案：
  - `backend/config/hotpost_supply_discovery_v2.yaml`
- 新增侦查纪要：
  - `reports/research/2026-04-09-signal-supply-tavily-scan-v1.md`
- 新增详细合同：
  - `docs/superpowers/specs/2026-04-09-signal-supply-contract-v2-contract.md`

## 这轮确认的边界

- 以后不能轻易说“今天这个领域没有够硬的新料”。
- 在 coverage floor 没满足前，正确说法只能是：
  - 当前 supply contract 没覆盖到足够宽的料面。
- 供给规则不允许继续硬编码在 Python 里。
- V2 的主线不是继续 polish，而是 YAML-first 的供给合同重做。

## 下一步

- 把 `topic_pack_scope_*.py` 里的业务供给规则迁到 YAML
- 做统一配置读取层
- 让 `reddit_search_spec_builder.py` 只消费配置
- 再跑扩面后的 collect / review / publish
