# Signal Quality Gate Effect V1

## 结论

`signal input quality gate` 接进生产生成链之后，效果是：

- **挡脏样本有效**
- **但单靠这道闸，不足以把新生成链救回来**

这一步不是白做，但也不能误判成“主问题已经解决”。

## 接闸前

- sample_count: `36`
- pass: `14`
- fail: `22`
- pass_rate: `38.89%`

高频失败标签：

- `reddit_restatement = 18`
- `no_judgment_gain = 12`
- `why_now_not_actionable = 10`
- `quote_not_used_well = 6`

## 接闸后

- sample_count: `31`
- pass: `11`
- fail: `20`
- pass_rate: `35.48%`

高频失败标签：

- `reddit_restatement = 18`
- `no_judgment_gain = 10`
- `why_now_not_actionable = 9`
- `quote_not_used_well = 3`

## 关键变化

### 1. 闸门确实挡掉了最脏输入

- `real_count`: `36 -> 31`
- `generation_failure_count = 8`
- 这些被挡掉的样本，正是单帖弱证据 / bot 污染 / 公版废话那一类

### 2. `quote_not_used_well` 明显下降

- `6 -> 3`

这说明：

- 输入质量闸门对“机器人回复 / 寒暄废话污染正文”这类问题是有效的

### 3. 但主问题没被打掉

- `reddit_restatement` 仍然是 `18`
- `candidate_generated` 当前仍然是 `0 pass / 15 fail`

这说明：

**新生成链的主问题还是 signal skill 本身。**

输入质量闸门只是先把最脏样本挡掉，不会自动把剩下的卡写好。

## 当前判断

当前最准确的判断是：

1. `signal input quality gate` 必须保留
2. 但它只能当“垃圾输入过滤层”
3. 接下来必须回到：
   - 在更干净的输入盘子上继续改 `signal skill`

## 下一步

1. 保留质量闸门
2. 在接闸后的新盘子上，重新跑第二轮 signal skill 实验
3. 重点继续打：
   - `reddit_restatement`
   - `no_judgment_gain`
4. 优先处理 pack：
   - `business-growth-ops / paid-economics`
   - `ai-automation / tools-efficiency`
