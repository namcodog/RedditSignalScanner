# 2026-05-14 品牌发现 SKU Probe

## 目的

用现有品牌池做锚点，不只复查已知品牌，而是发现新品牌、新型号、新类目品牌和配件/翻新机会。

## 执行结果

- 新增 profile：`crossborder-sku-brand-discovery-7d`
- 覆盖领域：家清、咖啡小家电、包袋旅行、户外露营、文具转售、手电硬件
- 采集候选：`30`
- V13 草稿：`7`
- 明确被 gate 拦截：`1`
- 已发布：`0`，本轮只进入待审草稿，不直接污染首页和正式发卡节奏

## 已形成草稿

| 领域 | 新品牌/型号线索 | draft_id | 判断 |
| --- | --- | --- | --- |
| 家清 | Miele C1 / C3 | `draft-cand-ecommerce-sellers-1t7wdq9-validate` | 小户型吸尘器按面积选型 |
| 宠物家居 | 不锈钢猫砂盆 | `draft-cand-ecommerce-sellers-1tad4dx-validate` | 低价替代高价自动猫砂盆 |
| 咖啡 | DF54 | `draft-cand-ecommerce-sellers-1tbet3o-validate` | 平刀磨豆机品控和深烘堵塞风险 |
| 咖啡 | Bambino Plus 改装 | `draft-cand-ecommerce-sellers-1t6o9cd-validate` | 入门机压力控制改装服务 |
| 包袋 | 26+6 背包 | `draft-cand-ecommerce-sellers-1taf2sf-validate` | 可扩容背包轻载体验争议 |
| 文具 | Pilot / Kakuno | `draft-cand-ecommerce-sellers-1tajf30-validate` | 入门爆款带动品牌粘性 |
| 手电 | Convoy 3x21C | `draft-cand-ecommerce-sellers-1tbedjd-validate` | 高流明和持续输出实测信号 |

## 被拦截样本

- `cand-ecommerce-sellers-1tann4t`：日本露营装备展，热度高但单帖单社区证据不足，被 input quality gate 拦截。

## 结论

这条线成立。`discover-only` 只能找帖子，不能直接 seed；必须跑 `harvest` 补足评论证据后再进 V13。品牌发现卡默认应走 `signal`，不能硬塞 `hot`，否则会被 freshness gate 打回。

## 下一步

- 下一轮运营优先审核这 `7` 张草稿。
- 继续用 `crossborder-sku-brand-discovery-7d` 每天小配额跑。
- 对连续能出卡的新品牌，进入品牌池待确认，不自动写正式品牌池。
