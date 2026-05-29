# r/Entrepreneur 探索记录

日期：2026-05-29

## 结论

`r/Entrepreneur` 有价值，但不适合直接放进默认日常大池。它适合作为 `ecommerce-sellers` 和 `business-growth-ops` 的小配额实验社区持续观察。

价值点集中在：

- 产品上线前的市场测试和需求验证
- 同一产品在不同渠道里的转化差异
- AI agents / AI call center / AI search optimization 等服务机会
- Shopify / ecommerce 运营痛点

噪音也明显：

- 周常服务合作贴
- 泛创业心态、人生建议、求鼓励
- 与选品、渠道、真实经营数据无关的个人叙事

## 为什么之前没探索到

1. `Entrepreneur` 以前在旧资料和 `candidate_communities` 里出现过，但没有进入当前 Hotpost 显式探索用的 `experimental_communities`。
2. 当前日常产卡默认不跑 experimental 社区；只有显式 probe 才会进入小配额探索。
3. 探索 specs 有小预算截断，社区放在列表尾部时会被前面的社区吃掉预算。
4. 当前 gate 更偏向具体卖家、平台、商品、渠道证据；`r/Entrepreneur` 过宽，泛创业内容容易被挡掉。

## 本轮调整

- 在 `backend/config/hotpost_supply_discovery_v2.yaml` 中，把 `Entrepreneur` 加入并前置到：
  - `ecommerce-sellers / seller-category-direction / experimental_communities`
  - `business-growth-ops / funnel / experimental_communities`
- 补了更贴近该社区的实验关键词：
  - `market testing before launch`
  - `validating a product before launch`
  - `product launch without validation`
  - `tested the same product in a new channel`

## 验证

- `build_reddit_search_specs(..., include_experimental=True)` 已能生成 `Entrepreneur` specs。
- 默认 specs 仍不包含 experimental probe，日常大池未被污染。
- 回归测试通过：`17 passed`。
- safe probe 结果：
  - `business-growth-ops` 命中 `r/Entrepreneur` 的 `$65k with AI Agents`。
  - `ecommerce-sellers` 命中 `r/Entrepreneur`，但当前样本仍偏噪音：`Talent Tuesday`、`founders' drive`。

## 出卡信号复查

补抓 `r/Entrepreneur` 近期 listing 和定向搜索后，最值得进入出卡判断的是：

1. `1tkojtq`：同一个 AI 产品放在网站聊天组件和 WhatsApp，30 天结果差异明显。
   - 判断：可做 `signal`，主题是“AI 服务产品不是只看模型能力，交互渠道会改变转化”。
   - 已补关键词并被 safe probe 收进实验候选：`cand-business-growth-ops-1tkojtq`。
2. `1told4x`：创业者提醒产品上线前要做反复市场测试。
   - 判断：可作为选品 / 产品验证方向的观察样本，但单帖更像方法论，需要评论里有具体执行问题才适合出卡。
3. `1tok3mm`：讨论 AI agents 是否有真实需求，还是 YouTube hype。
   - 判断：可作为 AI 服务机会判断的辅助信号；需要避免落成泛 AI 讨论。
4. `1tmr2ri`：把销售问题误判成漏斗 / 运营问题，两年后才发现真实漏点。
   - 判断：可做商业增长运营信号，但和 `r/Entrepreneur` 新社区价值关系弱于 `1tkojtq`。

本轮又把 `business-growth-ops / funnel` 的实验词收紧为更能命中渠道实验和真实需求：

- `website chatbot whatsapp`
- `same ai product website whatsapp`
- `ai agents demand`

最初 `seed --live cand-business-growth-ops-1tkojtq validate` 未成功，因为该候选只在 `experimental_candidates`，正式 review store 还找不到；这符合“不直接从 experimental 发布”的边界。后续按 live Reddit 数据重建正式 candidate 后，已进入 V13 review 链路。

## 已发布卡

用户确认该方向适合作为后续运营新方向后，本轮正式发布 `5` 张：

| card_id | 主题 | 类型判断 |
| --- | --- | --- |
| `card-cand-business-growth-ops-1tkojtq-validate` | 同一个 AI 助手放在 WhatsApp 比网站插件更能让用户开口 | 渠道实验 |
| `card-cand-ecommerce-sellers-1told4x-validate` | 创业者开始反思亲友反馈不能替代市场验证 | 市场验证 |
| `card-cand-business-growth-ops-1tok3mm-validate` | AI agents 需求从买 demo 转向买可靠性补救 | AI 服务需求 |
| `card-cand-business-growth-ops-1tmr2ri-validate` | 创始人误判销售问题，实际漏在客户流程 | 漏斗误诊 |
| `card-cand-business-growth-ops-1tmf2nk-validate` | 早期增长先弄清第一批用户为什么买，再扩大渠道 | 早期增长 |

发布结果：`release-a20b49bf877d / card_count=1241`，`miniRelease / miniFavorites / cloud_db / feed_contract / hot controversy guard / copy guard` 均通过。

## 下一步

继续收录观察，不做 R12 正式入池写入。后续只在出现“市场测试 / 需求验证 / 渠道对比 / 明确电商运营痛点”的帖子时进入草稿候选；泛创业贴不出卡。
