# phase723 - YAML 检索句式层接线与 AI/电商扩面

## 本轮完成

- 把“会搜 Reddit”的句式模板正式接进 YAML：
  - `pain`
  - `help`
  - `switch`
  - `solution`
- 让供给主链不只认关键词，也会展开成 Reddit 原生问法搜索：
  - `hotpost_supply_projection.py`
  - `reddit_search_spec_builder.py`
  - `source_scope_catalog.py`
- 继续按用户指定方向补宽 YAML：
  - AI：`Hamel Husain / Karpathy / swyx / Chip Huyen` 等人物线
  - AI+产品：`ProductManagement / SaaS / ExperiencedDevs`
  - 电商：品牌信任 / 品牌替代 / `Kickstarter / Indiegogo / Crowdfunding`

## 这轮新增的关键题材簇

- `ai-product-and-adoption`
- `brand-trust-and-alt`
- `brand-launch-and-crowdfunding`

## 更新后的硬数字

- `ai-automation`
  - `7` 个题材簇
  - `20` 个去重社区
  - `32` 个命名实体
  - `104` 条关键词
  - `8` 个模板 stem
- `ecommerce-sellers`
  - `9` 个题材簇
  - `31` 个去重社区
  - `11` 个命名实体
  - `110` 条关键词
  - `8` 个模板 stem
- `business-growth-ops`
  - `5` 个题材簇
  - `19` 个去重社区
  - `0` 个命名实体
  - `82` 条关键词
  - `8` 个模板 stem
- 全局去重社区总数：`66`

## 当前结论

- 角色 prompt 里的“检索方法”现在开始真正进系统了，不再只是世界观。
- AI 和电商已经明显变宽。
- 增长线还是偏薄，尤其命名实体还是 `0`，这会继续限制抓取面。

## 验证结果

- `pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py backend/tests/services/hotpost/test_source_scope_catalog.py -q`
  - `13 passed`

## 下一步

- 继续补 `business-growth-ops` 的命名实体层：
  - 平台
  - 工具
  - attribution 对象
  - creator / affiliate 生态对象
- 再按新 contract 跑 collect，观察真实料面是否继续变宽
