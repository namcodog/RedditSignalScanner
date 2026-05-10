# Phase 456 - live 数据噪音治理第三轮根治：evidence_chain 收成可点击硬合同

## 发现了什么？

这轮把上一轮剩下的最大尾巴继续打穿了，结论比 Phase 455 更扎实：

1. `evidence_chain` 为空，不只是前端渲染问题，而是后端 canonical 没把证据合同补完整
   - pain 可以从 `facts_slice.sample_posts_db` 找回真实 Reddit 原帖
   - 但旧逻辑没有稳定保留 `subreddit/community`
   - 机会卡在 `source_examples` 为空时，也不会自动继承同一条 pain 的证据链

2. `saas-collaboration` 这类题材已经证明：
   - 新分析链里 `sample_posts_db` 现在能带 `url/permalink`
   - 所以 evidence 不再只能停留在“用户原话”
   - 但 token hint 还不够宽，`推进情况并不清楚` 这种 pain 仍可能漏掉匹配

## 是否需要修复？

需要，而且这轮已经完成第三轮系统级修复。

## 精确修复方法？

### 1. `structured_report_fallback.py`

- `evidence_chain` 现在优先保留 `community / subreddit`
- 新增对 `推进情况` 单独命中 `tracking / progress / project / status`
- 机会卡在 `source_examples` 为空时，会回退继承同索引 pain 的 `evidence_chain`

### 2. URL 归一化

- `normalize_reddit_url()` 继续保底：
  - 媒体资源 URL 优先回退 permalink
  - 保证前端拿到的是可点击 Reddit 原帖，而不是 `i.redd.it` 资源地址

### 3. 回归测试

- `backend/tests/services/report/test_structured_report_fallback.py`
  - 新增 `facts_slice.sample_posts_db` 恢复 evidence 的测试
  - 新增 `推进情况并不清楚` 能从事实样本命中证据的测试
  - 新增“机会卡继承 pain evidence”测试

## 验证

- `pytest tests/services/report/test_structured_report_fallback.py -q`
  - `21 passed`
- `python -m py_compile app/services/report/structured_report_fallback.py`
  - passed

### 真实 live 复验

- `saas_collaboration_v1`
  - `task_id=e76d06eb-b9f4-48c4-a486-15d13f6636bc`
  - 首轮 `A_full`
  - 结果页：`http://127.0.0.1:3006/report/e76d06eb-b9f4-48c4-a486-15d13f6636bc`

抽检结果：

- pain 1 / pain 2 / pain 3 都已带真实 Reddit URL
- opportunity 1 / opportunity 2 都已带真实 Reddit URL
- 这次不再出现：
  - `evidence_chain=[]`
  - “pain 有证据，机会没证据”
  - “只剩用户原话，没有外部原帖”

## 下一步系统性的计划是什么？

1. 继续把同一套 `evidence_chain` 合同打到其余领域
2. 按 8 大领域抽不同正式题做横向复验
3. 把“题眼过滤 + partial pain supplement + evidence_chain contract”正式沉淀成 SOP

## 这次执行的价值是什么？

- `live 数据噪音治理` 现在已经不只是在“标题像不像真的”
- pain / opportunity / evidence 终于开始成为同一条可点击、可对位的硬合同
- 这为后续 8 大领域横向验证提供了真正可复用的根部规则
