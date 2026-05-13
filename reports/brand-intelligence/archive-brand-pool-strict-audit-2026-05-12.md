# Archive Brand Pool Strict Audit

- source: `reports/brand-intelligence/archive-brand-pool-preaudit-2026-05-12.csv`
- db_writes: `false`
- total_brands: `1644`
- p0_clean_accept: `1461`
- p1_text_match_risk: `58`
- p2_canonical_form_review: `81`
- p3_metadata_review: `44`
- strict_focus_total: `183`

## 审计结论

- 这轮严格审计不建议删除任何品牌；风险主要在后续自动文本匹配和 canonical 形式。
- P0 可直接进入细审/入池候选。
- P1 必须加上下文约束，不能用裸词匹配。
- P2 需要确认 canonical 形式、服务/子产品类型或符号格式。
- P3 是元数据问题，保留多领域和重复来源即可。

## Priority Summary

| Priority | Count | Meaning |
|---|---:|---|
| P0_clean_accept | 1461 | 未发现严格审计风险 |
| P1_text_match_risk | 58 | 保留品牌，但自动文本匹配误报风险最高 |
| P2_canonical_form_review | 81 | 保留品牌，需确认 canonical/服务类型/符号格式 |
| P3_metadata_review | 44 | 保留品牌，需保留多领域或重复来源元数据 |

## Flag Summary

| Flag | Count |
|---|---:|
| common_word_collision | 16 |
| contains_digit | 24 |
| duplicate_merged | 45 |
| long_phrase | 8 |
| multi_domain | 44 |
| noise_overlap | 3 |
| punctuation_or_url | 43 |
| service_channel_phrase | 14 |
| short_token | 39 |

## P1 重点复核：文本匹配高风险

| Brand | Domains | Flags | Recommendation |
|---|---|---|---|
| 3M | 家居生活 | short_token; contains_digit | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Action | 省钱消费与零售 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Aer | 工具与EDC; 户外旅行与轻装备 | short_token; multi_domain; duplicate_merged | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Article | 家居生活 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| B&M | 省钱消费与零售 | short_token; punctuation_or_url | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Bim | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Brother | 省钱消费与零售 | noise_overlap | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| C4 | 食品咖啡与生活方式 | short_token; contains_digit | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Campaign | 家居生活 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Case | 工具与EDC | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| CB2 | 家居生活 | short_token; contains_digit | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| CEX | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Cross | 工具与EDC | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| DHL | 电商平台与卖家工具 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Dia | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Downstream | 电商平台与卖家工具 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| DPiù | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| DSV | 电商平台与卖家工具 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| DWR | 家居生活 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| ECM | 食品咖啡与生活方式 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Engineer | 工具与EDC | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Eno | 户外旅行与轻装备 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Flow | 食品咖啡与生活方式 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| GE | 家居生活 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| H-E-B | 食品咖啡与生活方式 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Hay | 家居生活 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Heart | 食品咖啡与生活方式 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Hem | 家居生活 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Jet | 工具与EDC | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Kik | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Kind | 食品咖啡与生活方式 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| LG | 家居生活 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Mam | 家庭与亲子 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Material | 食品咖啡与生活方式 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| MD | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Meh | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| MPB | 省钱消费与零售 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| MSR | 户外旅行与轻装备 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Nuk | 家庭与亲子 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| OFX | 电商平台与卖家工具 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Oxo | 家居生活 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| PayPal | 电商平台与卖家工具 | noise_overlap | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Primary | 家庭与亲子 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| PT's | 食品咖啡与生活方式 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Rab | 户外旅行与轻装备 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Ratio | 食品咖啡与生活方式 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| RH | 家居生活 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Route | 电商平台与卖家工具 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Sharp | 家居生活 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| SMA | 家庭与亲子 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| SOG | 工具与EDC | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Spot | 户外旅行与轻装备 | common_word_collision | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Stripe | 电商平台与卖家工具 | noise_overlap | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| TQL | 电商平台与卖家工具 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| UCO | 户外旅行与轻装备 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| UPS | 电商平台与卖家工具 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Wen | 工具与EDC | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |
| Zip | 电商平台与卖家工具 | short_token | 保留品牌，但禁止裸词自动匹配；需 exact + 上下文/领域约束 |

## P2 复核：canonical / 服务形态

| Brand | Domains | Flags | Recommendation |
|---|---|---|---|
| 1688.com | 电商平台与卖家工具 | contains_digit; punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 1stDibs | 省钱消费与零售 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 1Zpresso | 食品咖啡与生活方式 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 2Checkout | 电商平台与卖家工具 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 3 Sprouts | 家庭与亲子 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 3dcart | 电商平台与卖家工具 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 4moms | 家庭与亲子 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 5.11 Tactical | 户外旅行与轻装备 | contains_digit; punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 66 North | 户外旅行与轻装备 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 7-Eleven | 食品咖啡与生活方式 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| 99 Ranch | 省钱消费与零售 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| A101 | 省钱消费与零售 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| ABBY&FINN | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Adobe Commerce | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Adorama Used | 省钱消费与零售 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Amazon Marketing Services | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Apt2B | 家居生活 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Authorize.Net | 电商平台与卖家工具 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| B&B Italia | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| B&H Used | 省钱消费与零售 | punctuation_or_url; service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Bing Ads | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Black & Decker | 工具与EDC | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Black & White | 食品咖啡与生活方式 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Boll & Branch | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Bridge City Tool Works | 工具与EDC | long_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| C.H. Robinson | 电商平台与卖家工具 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Checkout.com | 电商平台与卖家工具 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Coupons.com | 省钱消费与零售 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Cow & Gate | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Crate & Barrel | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Crate & Kids | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Dash & Albert | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Dr. Brown's | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Dr. Martens | 省钱消费与零售 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Drink Coffee Do Stuff | 食品咖啡与生活方式 | long_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| DS Amazon Quick View | 电商平台与卖家工具 | long_phrase; service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| E.Leclerc | 食品咖啡与生活方式 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Facebook Ads | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Facebook Marketplace | 省钱消费与零售 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Food 4 Less | 省钱消费与零售 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Google Ads | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| H&M Home | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| H&M Kids | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Hancock & Moore | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Helium 10 | 电商平台与卖家工具 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Informed.co | 电商平台与卖家工具 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Inov-8 | 户外旅行与轻装备 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| J.B. Hunt | 电商平台与卖家工具 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Johnson & Johnson | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Joss & Main | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| McGee & Co | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Melissa & Doug | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Nurture& | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Once Upon A Farm | 家庭与亲子 | long_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Pinterest Ads | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Poly & Bark | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Raymour & Flanigan | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| REI Re/Supply | 省钱消费与零售 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Rema 1000 | 省钱消费与零售 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Rite in the Rain | 工具与EDC | long_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Room & Board | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Ross Dress for Less | 省钱消费与零售 | long_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Safety 1st | 家庭与亲子 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Salesforce Commerce Cloud | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Sana Commerce | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Sellics Advertising | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Serena & Lily | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Shift4Shop | 电商平台与卖家工具 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| ShopGoodwill.com | 省钱消费与零售 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Smart & Final | 省钱消费与零售 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Society6 | 家居生活 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Stamps.com | 电商平台与卖家工具 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Stearns & Foster | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Swap.com | 省钱消费与零售 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| The North Face Renewed | 省钱消费与零售 | long_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| TikTok Ads | 电商平台与卖家工具 | service_channel_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Timbuk2 | 户外旅行与轻装备 | contains_digit | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Tuft & Needle | 家居生活 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Up & Up | 家庭与亲子 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |
| You Need A Budget | 省钱消费与零售 | long_phrase | 保留品牌，入库前确认 canonical 形式和 brand_type |
| Zwilling J.A. Henckels | 食品咖啡与生活方式 | punctuation_or_url | 保留品牌，入库前确认 canonical 形式和 brand_type |

## P3 复核：多领域 / 重复来源

| Brand | Domains | Flags | Recommendation |
|---|---|---|---|
| Aldi | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Anker | 户外旅行与轻装备; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Bellroy | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| BioLite | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Birkenstock | 户外旅行与轻装备; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Black Diamond | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Blackstone | 户外旅行与轻装备; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Bosch | 家居生活; 工具与EDC | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| CamelCamelCamel | 电商平台与卖家工具; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Convoy | 工具与EDC; 电商平台与卖家工具 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Costco | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Darn Tough | 户外旅行与轻装备; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Eufy | 家居生活; 家庭与亲子 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Fellow | 户外旅行与轻装备; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Fisher-Price | 家庭与亲子 | duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Gerber | 家庭与亲子; 工具与EDC | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Goal Zero | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Goruck | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Herschel Supply | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Hydro Flask | 户外旅行与轻装备; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Kaufland | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Keepa | 电商平台与卖家工具; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Kirkland Signature | 家庭与亲子; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| KitchenAid | 家居生活; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Le Creuset | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Leatherman | 工具与EDC; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Ledlenser | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Lidl | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Lodge | 户外旅行与轻装备; 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Miele | 家居生活; 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Mystery Ranch | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Nitecore | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Panasonic | 家居生活; 工具与EDC | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Petzl | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Princeton Tec | 工具与EDC; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Red Wing | 户外旅行与轻装备; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Stanley | 工具与EDC; 户外旅行与轻装备; 省钱消费与零售 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Target | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Thule | 家庭与亲子; 户外旅行与轻装备 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Trader Joe's | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Victorinox | 工具与EDC; 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Vitamix | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Walmart | 省钱消费与零售; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
| Yeti | 户外旅行与轻装备; 食品咖啡与生活方式 | multi_domain; duplicate_merged | 保留品牌，保留多领域/重复来源元数据 |
