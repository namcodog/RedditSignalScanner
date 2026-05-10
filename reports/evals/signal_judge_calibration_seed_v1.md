# Signal Judge Calibration Seed V1

## 用法

- 这份种子包只服务于 judge calibration 第一轮。
- 先让人独立判断 `pass/fail + failure_tags`，不要先看“为什么挑它”。
- 校准时重点看“人和 judge 会不会在这些样本上分歧”。

## 推荐校准量

- 第一轮：`16` 条
- 结构：
  - `8` 条相对稳的 pass 候选
  - `8` 条相对稳的 fail 候选

## Pass 候选

### 1. `signal-eval-clue-notion-ai-fluff`
- 理由：信号句短、判断前移清楚、读感自然。

### 2. `signal-eval-card-group-ai-automation-ab7fdc5eb9`
- 理由：从“报错”往“错了还继续跑”推进了一层，判断增量明显。

### 3. `signal-eval-card-group-ai-automation-bc36ca8551`
- 理由：从演示好不好看，推进到企业真正卡在“追责”。

### 4. `signal-eval-card-group-ai-automation-e5752464a4`
- 理由：权限和责任边界说得清，why_now 也不算空。

### 5. `signal-eval-card-cand-ecommerce-sellers-1seeom8-validate`
- 理由：症状、替代方向和购买判断都比较集中。

### 6. `signal-eval-card-cand-ecommerce-sellers-1se4dnt-validate`
- 理由：服务体验被翻译成品牌判断，信号感够强。

### 7. `signal-eval-card-cand-ecommerce-sellers-1s94inc-validate`
- 理由：把“袜子耐用”推进成“品牌信任溢价”，有轻量判断。

### 8. `signal-eval-card-cand-ai-automation-1sdv3lo-validate`
- 理由：对手机 Agent 的担心点说得清楚，场景和风险都贴脸。

## Fail 候选

### 9. `signal-eval-card-cand-ai-automation-1se2nxm-validate`
- 理由：典型 `reddit_restatement`，几乎就是把评论换成中文。

### 10. `signal-eval-card-cand-business-growth-ops-1s1lelq-validate`
- 理由：复述长评论，像帖子摘要，不像信号卡。

### 11. `signal-eval-card-cand-business-growth-ops-1s9b8s5-validate`
- 理由：标题和摘要都偏报告腔，用户要花力气翻译才知道在说什么。

### 12. `signal-eval-card-cand-ecommerce-sellers-1saj0xa-validate`
- 理由：更像论坛求助索引，不像产品信号；`audience` 也偏论坛身份。

### 13. `signal-eval-card-cand-ai-automation-1sdwgvg-validate`
- 理由：单帖弱证据，却写成宽口径趋势判断。

### 14. `signal-eval-card-cand-ai-automation-1sem20t-validate`
- 理由：没有真正的判断增量，why_now 也是模板化时间句。

### 15. `signal-eval-card-cand-ai-automation-1se8175-validate`
- 理由：标题、summary 和 quote 用法都偏 reporty/raw，容易误判成“有信息密度所以算 pass”。

### 16. `signal-eval-card-cand-ai-automation-1se6nq5-validate`
- 理由：quote 过长，还混进机器人回复，是 `quote_not_used_well` 的典型。

## 当前最该校准的分歧点

- 短引用和原帖复述的边界
- 弱证据样本到底算“保守”还是“空”
- `audience` 什么时候算“谁在聊”，什么时候已经滑成 persona
- `why_now` 什么时候只是时间句，什么时候已经完成了信号读数


case_id: signal-eval-clue-notion-ai-fluff
  - overall_pass: pass
  - failure_tags: []
  - note: 这张卡已经把“Notion AI 把内容磨空”这个判断说清楚了，不只是转述帖子。