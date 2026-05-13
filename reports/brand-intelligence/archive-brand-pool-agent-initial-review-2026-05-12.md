# Archive Brand Pool Agent Initial Review

- source: `archive-brand-pool-preaudit-2026-05-12.csv`
- db_writes: `false`
- total_brands: `1644`
- approve: `1625`
- approve_with_ambiguous_name_guard: `16`
- review_noise_config_keep_likely: `3`
- multi_domain_count: `44`

## 初审结论

- 大部分品牌可进入你的细审列表：不建议删除。
- 16 个品牌名同时是常见英文词，建议保留品牌，但后续做文本匹配时加上下文约束。
- 3 个品牌和旧噪音词表冲突，按品牌常识建议保留，并回头修正噪音配置。
- 44 个品牌跨多个领域出现，这不是问题，建议保留多领域归属。

## 领域分布

| 领域 | 品牌数 |
|---|---:|
| 家居生活 | 231 |
| 家庭与亲子 | 266 |
| 工具与EDC | 217 |
| 户外旅行与轻装备 | 205 |
| 电商平台与卖家工具 | 267 |
| 省钱消费与零售 | 212 |
| 食品咖啡与生活方式 | 294 |

## 需要你重点看的 19 个

| Brand | 初审建议 | Domains | Reason |
|---|---|---|---|
| Action | approve_with_ambiguous_name_guard | 省钱消费与零售 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Article | approve_with_ambiguous_name_guard | 家居生活 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Brother | review_noise_config_keep_likely | 省钱消费与零售 | 和旧噪音词表冲突；按品牌池口径建议保留，但需要修正噪音配置 |
| Campaign | approve_with_ambiguous_name_guard | 家居生活 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Case | approve_with_ambiguous_name_guard | 工具与EDC | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Cross | approve_with_ambiguous_name_guard | 工具与EDC | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Downstream | approve_with_ambiguous_name_guard | 电商平台与卖家工具 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Engineer | approve_with_ambiguous_name_guard | 工具与EDC | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Flow | approve_with_ambiguous_name_guard | 食品咖啡与生活方式 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Heart | approve_with_ambiguous_name_guard | 食品咖啡与生活方式 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Kind | approve_with_ambiguous_name_guard | 食品咖啡与生活方式 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Material | approve_with_ambiguous_name_guard | 食品咖啡与生活方式 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| PayPal | review_noise_config_keep_likely | 电商平台与卖家工具 | 和旧噪音词表冲突；按品牌池口径建议保留，但需要修正噪音配置 |
| Primary | approve_with_ambiguous_name_guard | 家庭与亲子 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Ratio | approve_with_ambiguous_name_guard | 食品咖啡与生活方式 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Route | approve_with_ambiguous_name_guard | 电商平台与卖家工具 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Sharp | approve_with_ambiguous_name_guard | 家居生活 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Spot | approve_with_ambiguous_name_guard | 户外旅行与轻装备 | 品牌名也是常见英文词；建议保留品牌，但后续文本匹配必须加上下文约束 |
| Stripe | review_noise_config_keep_likely | 电商平台与卖家工具 | 和旧噪音词表冲突；按品牌池口径建议保留，但需要修正噪音配置 |

## 跨领域样例

| Brand | Domains | Reason |
|---|---|---|
| Aer | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Aldi | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Anker | 户外旅行与轻装备; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Bellroy | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| BioLite | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Birkenstock | 户外旅行与轻装备; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Black Diamond | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Blackstone | 户外旅行与轻装备; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Bosch | 家居生活; 工具与EDC | 跨多个领域出现；建议保留多领域归属 |
| CamelCamelCamel | 电商平台与卖家工具; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Convoy | 工具与EDC; 电商平台与卖家工具 | 跨多个领域出现；建议保留多领域归属 |
| Costco | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Darn Tough | 户外旅行与轻装备; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Eufy | 家居生活; 家庭与亲子 | 跨多个领域出现；建议保留多领域归属 |
| Fellow | 户外旅行与轻装备; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Gerber | 家庭与亲子; 工具与EDC | 跨多个领域出现；建议保留多领域归属 |
| Goal Zero | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Goruck | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Herschel Supply | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Hydro Flask | 户外旅行与轻装备; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Kaufland | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Keepa | 电商平台与卖家工具; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Kirkland Signature | 家庭与亲子; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| KitchenAid | 家居生活; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Le Creuset | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Leatherman | 工具与EDC; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Ledlenser | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Lidl | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Lodge | 户外旅行与轻装备; 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Miele | 家居生活; 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Mystery Ranch | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Nitecore | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Panasonic | 家居生活; 工具与EDC | 跨多个领域出现；建议保留多领域归属 |
| Petzl | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Princeton Tec | 工具与EDC; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Red Wing | 户外旅行与轻装备; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Stanley | 工具与EDC; 户外旅行与轻装备; 省钱消费与零售 | 跨多个领域出现；建议保留多领域归属 |
| Target | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Thule | 家庭与亲子; 户外旅行与轻装备 | 跨多个领域出现；建议保留多领域归属 |
| Trader Joe's | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Victorinox | 工具与EDC; 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Vitamix | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Walmart | 省钱消费与零售; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
| Yeti | 户外旅行与轻装备; 食品咖啡与生活方式 | 跨多个领域出现；建议保留多领域归属 |
