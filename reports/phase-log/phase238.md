# Phase 238 — Brand Discovery 配置化收口 + Ad-hoc 口径统一（2026-03-10）

## 背景

上一轮先把两个阻塞问题止血了：

1. ad-hoc topic 在没有预配品牌名单时，`brand_pain` 容易直接归零  
2. `source_range` 对 `post_id` / `reddit_comment_id` 这类离线脚本字段不兼容

这轮在止血基础上，继续把“品牌自动发现”做成顺滑可配置，避免后续每次调阈值、调噪音词都要改代码。

---

## 发现了什么

### 1. 配置底座其实已经有了，不需要另起炉灶

仓库里已经有成熟的 YAML 配置体系：

- `backend/config/topic_profiles.yaml`
- `backend/config/domain_pain_points.yml`
- `backend/config/vertical_overrides.yaml`
- `backend/config/quality_gates/*`

所以最顺的方案不是再新造一套 `brand_discovery.yml`，而是直接接到 `topic_profiles.yaml`。

### 2. 上一轮的品牌自动发现还是“代码内规则”

虽然不是写死品牌名单，但 stopwords、阈值、正则都还在代码里。  
这意味着：

- 能止血
- 但不能方便调参
- 新题目要微调时，还是得动代码

### 3. ad-hoc 路径和 profile 路径的品牌发现口径还没完全统一

之前 ad-hoc fallback profile 是运行时临时构造的，只带 topic/community/keywords，不带品牌发现配置。  
如果不显式接默认配置，ad-hoc 走的还是代码默认值，不是系统统一配置值。

---

## 是否需要修复

需要，而且已经修完。

这次不是只修 bug，而是把“品牌发现”的入口、默认值、覆盖方式、ad-hoc fallback 全部统一到一套配置口径里。

---

## 精确修复方法

### 1. 在 `topic_profiles.py` 中新增品牌发现配置模型

新增 `BrandDiscoveryConfig`，统一管理：

- `enabled`
- `min_frequency`
- `max_candidates`
- `token_pattern`
- `stopwords`

并新增：

- `load_brand_discovery_defaults()`
- `_coerce_brand_discovery_config()`

作用：

- 先读 `topic_profiles.yaml` 顶层默认值
- 再把单个 topic 的 `brand_discovery` 覆盖合并进去
- 最终给每个 `TopicProfile` 一个完整可用的品牌发现配置

### 2. 在 `topic_profiles.yaml` 中增加顶层默认配置

新增顶层：

```yaml
brand_discovery:
  enabled: true
  min_frequency: 3
  max_candidates: 15
  token_pattern: "\\b([A-Z][a-zA-Z]{1,20})\\b"
```

并允许某个 topic 单独覆盖，例如：

```yaml
brand_discovery:
  min_frequency: 2
  max_candidates: 20
```

这次在 `shopify_ads_conversion_v1` 上补了一组更宽松的覆盖，方便窄题保住品牌候选。

### 3. 在 `midstream.py` 里统一消费这套配置

`_discover_brands_from_text()` 现在不再吃写死常量，而是吃：

- `profile.brand_discovery`
- 若拿不到 profile，再回退到 `load_brand_discovery_defaults()`

并且补了两层稳态保护：

1. `enabled=false` 时直接关闭自动发现  
2. 自定义正则写坏时，回退到默认正则，不让链路崩掉

### 4. 在 `generate_t1_market_report.py` 里把 ad-hoc fallback profile 也接到默认配置

ad-hoc topic 临时构造 `TopicProfile` 时，显式注入：

```python
brand_discovery=load_brand_discovery_defaults()
```

这样 ad-hoc 和预配置 profile 终于吃的是同一套品牌发现口径。

### 5. 保留上一轮止血逻辑，不回退

这一轮没有回退上一轮已经修好的两件事：

- `brand_sentiment_top` 作为候选回退仍然保留
- `source_range` 的 `post_id` / `reddit_comment_id` 兼容仍然保留

所以现在是：

1. 先吃显式品牌候选  
2. 再吃 `brand_sentiment_top`  
3. 最后才走配置化自动发现  

这条链路比上一轮更稳，也更容易解释。

---

## 改动文件

### 代码

- `backend/app/services/analysis/topic_profiles.py`
- `backend/app/services/facts_v2/midstream.py`
- `backend/scripts/report/generate_t1_market_report.py`

### 配置

- `backend/config/topic_profiles.yaml`

### 测试

- `backend/tests/services/analysis/test_topic_profiles.py`
- `backend/tests/services/analysis/test_facts_v2_midstream.py`

---

## 验证结果

### AST

通过：

- `backend/app/services/analysis/topic_profiles.py`
- `backend/app/services/facts_v2/midstream.py`
- `backend/scripts/report/generate_t1_market_report.py`

### 回归测试

执行命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/analysis/test_facts_v2_quality_gate.py \
  tests/services/analysis/test_facts_v2_midstream.py \
  tests/services/analysis/test_topic_profiles.py -v
```

结果：

- `32 passed`
- 其中原有 19 个测试全部通过
- 新增品牌发现配置/自动发现测试通过

### 额外确认

已确认以下入口全部存在：

- `backend/config/topic_profiles.yaml` 顶层 `brand_discovery`
- `TopicProfile.brand_discovery`
- `load_brand_discovery_defaults()`
- ad-hoc fallback profile 显式注入默认配置
- `midstream._discover_brands_from_text()` 统一消费配置

---

## 口径统一（这次最终定稿）

### 品牌发现统一口径

从现在开始，`brand_pain` 的品牌候选统一按下面顺序来：

1. `brand_candidates` 显式传入  
2. `profile.required_entities_any + soft_required_entities_any`  
3. `brand_sentiment_top` 回退  
4. 配置化自动发现（capitalized token + 频次阈值 + stopwords 过滤）

### ad-hoc topic 统一口径

ad-hoc topic 不再走“代码默认写死规则”，而是走：

- `topic_profiles.yaml` 顶层 `brand_discovery` 默认配置

### profile topic 统一口径

有预配置 profile 的题目走：

- 顶层默认配置
- 再叠加该 profile 的 `brand_discovery` 覆盖

### Source Range 统一口径

`compute_source_range()` 统一兼容：

- post id: `id / reddit_id / post_id`
- comment id: `id / comment_id / reddit_comment_id`
- subreddit: `subreddit / subreddit_name`

---

## 下一步系统性的计划

### 1. 继续把“规则参数”从代码搬到配置

这一轮先把品牌发现做了配置化。  
下一步最值得继续搬的是：

- ad-hoc topic 的品牌噪音词
- brand/channel/platform 分类边界
- 更细的正则策略（比如是否允许全大写缩写）

### 2. 给配置增加最小可观测性

建议下一步补两类日志：

- 当前生效的 `brand_discovery` 配置摘要
- 自动发现命中的品牌候选列表

这样将来排查“为什么这次扫到 Bose、没扫到 JBL”会更快。

### 3. 如需更进一步，再做 DB/运营侧可配置

当前已经能通过 YAML 调。  
如果未来产品经理要自己调，不想提代码 PR，再考虑做：

- Admin 配置入口
- DB 持久化配置
- 多环境配置版本管理

这一步现在还不是必须。

---

## 这次执行的价值

### 1. 从“能止血”升级到“能长期调”

上一轮只是把 ad-hoc 的 `brand_pain=0` 问题堵住。  
这轮把调节手柄也补出来了。

### 2. 让 ad-hoc 和 profile 两条路终于说同一种话

以前两条路径表面看都叫“品牌自动发现”，其实底层口径不完全一样。  
现在统一成：

- 默认配置一份
- profile 可覆盖
- ad-hoc 显式继承默认

### 3. 后续调参成本明显下降

以后如果发现某个题目：

- 品牌抓太多
- 品牌抓太少
- 噪音词太多
- 阈值太严

优先改 YAML，不必先改 Python。
