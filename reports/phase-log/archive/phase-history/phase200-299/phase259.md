# Phase 259 - Dev 库社区真实整治执行结果

## 执行时间
- 2026-03-13

## 背景
- Phase 257 已经做完只读快照和 dry-run。
- 用户明确要求先执行真实整治，先降噪，再统一口径。
- 原始 dry-run 结论：
  - 生效社区：141
  - 候选社区：126
  - `community_pool` 垃圾：190
  - `discovered_communities` 垃圾：39
  - 异常：0

## 执行前事实确认
- 当前数据库：`reddit_signal_scanner_dev`
- 本次没有改数据库表结构
- 本次没有新增 migration
- 本次执行的是 Dev 库业务数据清理

## 第一次真实删除时发现的阻塞
- 直接硬删 `community_pool` 垃圾行时，数据库报外键错误：
  - `posts_raw.community_id -> community_pool.id`
- 进一步核实后发现，`community_pool` 还被以下表引用：
  - `posts_raw`
  - `community_audit`
  - `community_category_map`

### 结论
- 不是治理逻辑错了
- 是部分垃圾社区下面还挂着历史帖子/历史引用
- 这类记录不能直接硬删，否则会把历史采集数据链掰断

## 追加修复
- 把 `cleanup_dev` 改成“部分真实清理”模式：
  - **可安全硬删的 pool 垃圾**：直接删
  - **仍被历史数据引用的 pool 垃圾**：保留，并标记为 `blocked`
  - **所有垃圾社区对应的 `community_cache`**：可安全删除，统一删掉
  - **`discovered_communities` 垃圾**：直接删

## 清理前后对比

### 清理前
| 指标 | 数量 |
| --- | ---: |
| 生效社区 | 141 |
| 候选社区 | 126 |
| Pool 垃圾 | 190 |
| Discovered 垃圾 | 39 |
| 异常 | 0 |

### 本次真实删除结果
| 删除对象 | 数量 |
| --- | ---: |
| 硬删 `community_pool` | 142 |
| 删除 `community_cache` | 190 |
| 硬删 `discovered_communities` | 39 |
| 因历史引用被阻塞的 pool 垃圾 | 48 |

### 清理后
| 指标 | 数量 |
| --- | ---: |
| 生效社区 | 141 |
| 候选社区 | 126 |
| Pool 垃圾 | 48 |
| Discovered 垃圾 | 0 |
| 异常 | 0 |

## 这次真正完成了什么

### 1. 39 条 discovered 垃圾已经清空
- 包括：
  - `pending_duplicate_in_effective_pool`
  - `status_blacklisted`
  - `approved_duplicate_in_effective_pool`

### 2. 190 条 pool 垃圾里，142 条已经真删
- 这些没有历史引用，可以安全删掉

### 3. 剩下 48 条 pool 垃圾删不掉，不是逻辑问题，是历史数据引用卡住
- 这 48 条社区下面仍然挂着 `posts_raw`
- 当前不能直接物理删除

## 剩余 48 条被阻塞的垃圾社区
- `r/aliexpressbr`
- `r/amazon_influencer`
- `r/amazonanswers`
- `r/amazonargentina`
- `r/amazonecho`
- `r/amazonfba`
- `r/amazonfbaonlineretail`
- `r/amazonfbatips`
- `r/amazonmerch`
- `r/amazonprime`
- `r/amazonseller`
- `r/amazonsellercentral`
- `r/amazonvine`
- `r/amitheasshole`
- `r/askmen`
- `r/baking`
- `r/bbq`
- `r/beer`
- `r/bigseo`
- `r/breadit`
- `r/childfree`
- `r/climbing`
- `r/cocktails`
- `r/decorating`
- `r/digital_marketing`
- `r/fixedgearbicycle`
- `r/fulfillmentbyamazon`
- `r/geartrade`
- `r/matcha`
- `r/mechanicadvice`
- `r/mommit`
- `r/peopleofwalmart`
- `r/raisedbynarcissists`
- `r/seo_marketing_offers`
- `r/shopify`
- `r/shopifyappdev`
- `r/shopifydev`
- `r/shopifyecommerce`
- `r/shopifyseo`
- `r/sideproject`
- `r/spellcasterreviews`
- `r/stepparents`
- `r/teachers`
- `r/thrifty`
- `r/toolporn`
- `r/trueoffmychest`
- `r/walmart`
- `r/walmart_rx`

## 这 48 条的本质
- 它们已经不是“当前有效社区”
- 但它们仍然是“有历史帖子挂着的旧社区壳”
- 所以现在正确口径应该是：
  - **治理口径上把它们当垃圾**
  - **存储层上把它们当历史引用壳**
  - 不能再把它们当有效社区
  - 也不能直接物理删掉

## 输出文件
- 执行结果 JSON：
  - `reports/phase-log/phase259_governance_cleanup.json`
- 本报告：
  - `reports/phase-log/phase259.md`

## 回归验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_governance_service.py tests/api/test_admin_community_pool.py -q`
  - `13 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 当前统一结论
- Dev 库社区噪音已经被实质性打掉一大块
- 当前真正生效社区仍然是 141 个
- 候选池仍然是 126 个
- `discovered_communities` 垃圾已经清零
- 社区黑盒没有完全结束，但已经从“整池混乱”收缩成“48 个有历史引用的残留旧壳”

## 下一步建议
1. 先不要再纠缠“全删光”
2. 下一步改做“48 个历史引用壳”的统一口径治理：
   - 明确它们不是有效社区
   - 单独输出为 `historical_shells` / `blocked_garbage`
3. 然后再统一“社区分类真相源”和治理视图口径
