# Tools Efficiency Supply Fix V3

## 结论

`tools-efficiency` 这轮不是没抓到帖子，而是之前即使 `search-first` 了，低 quota 仍会被 `category` 宽 query 先吃满。
V3 做了两件更硬的事：

- 社区池继续收窄到：
  - `ChatGPT`
  - `ClaudeAI`
  - `OpenAI`
  - `cursor`
- `search-first` pack 的 bucket 顺序对 `tools-efficiency` 改成：
  - `problem -> change -> category`

目的不是抓更多帖子，而是先把“工具切换/订阅取舍/上下文丢失”这类真实摩擦顶到前面。

## 本轮实现

- 删掉会把 pack 拉回 builder 经验帖的入口：
  - `automation`
  - `ClaudeCode`
  - `ai tool stack`
  - `prompt workflow`
  - `which ai tools are worth paying for`
- 保留更贴近工具摩擦的 query：
  - `tool switching fatigue`
  - `copy paste context between tools`
  - `re explaining context to ai`
  - `which ai tool did you cancel`
  - `which ai subscription was worth keeping`
  - `which ai tool did you keep`
- 在 `reddit_search_spec_builder.py` 里给 `tools-efficiency` 加了独立的 bucket priority

## 测试

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_catalog.py \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py \
  backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`13 passed`

## 真实验证

### collect 结果

- `cand-ai-automation-1sc7byy`
  - subreddit: `ClaudeAI`
  - keyword: `tool switching fatigue`
  - title: `How much Claude Code can your brain actually handle before it breaks?`
- `cand-ai-automation-1scgwmc`
  - subreddit: `ChatGPT`
  - keyword: `copy paste context between tools`
  - title: `ChatGPT tricks I wish I knew earlier (not the usual ones)`
- `cand-ai-automation-1sestcy`
  - subreddit: `ClaudeAI`
  - keyword: `copy paste context between tools`
  - title: `asset manager and Claude... highly regulated environment`

### eval / judge 结果

- `case_count = 2`
- `generation_failure_count = 1`
  - 被 gate 挡掉的是 `cand-ai-automation-1scgwmc`
  - 原因：
    - `single_thread_weak_evidence`
    - `single_community_weak_evidence`
- judge：
  - `pass = 0`
  - `fail = 2`
  - `pass_rate = 0.0`
- 高频失败标签：
  - `reddit_restatement`
  - `why_now_not_actionable`
  - `quote_not_used_well`

## 判断

这轮结果比上一轮更干净，但还不能宣布 `tools-efficiency` 已经进入 pack 实验盘子。

真实变化是：

- 之前抓到的是：
  - 抽象 AI 观点
  - builder brag
  - 泛自动化经验
- 现在抓到的已经更像：
  - 工具使用负担
  - 工作流摩擦
  - 受监管环境里的上下文问题

但 judge 仍然 `0/2 fail`，说明这条线现在最多只能算：

**供给方向对了，但写法还没被证明。**

## 下一步

1. 不把 `tools-efficiency` 误判成“已准备好做正式 pack 实验”
2. 保留当前更窄的社区池和 bucket priority
3. 下一步如果继续，只做一个很小的定向 canary：
   - 专门打：
     - `reddit_restatement`
     - `why_now_not_actionable`
   - 不做大范围 pack prompt 实验
