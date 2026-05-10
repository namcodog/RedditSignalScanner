# Signal Judge Calibration V1

## 批次说明

- 批次：`v1`
- 样本量：`8`
- 结构：`4 pass / 4 fail`
- 来源：创始人人工判定

这轮校准的目的不是追求覆盖全样本，而是先钉住 judge 最容易跑偏的边界：

- 什么叫“判断前移”
- 什么叫“只是把 Reddit 翻成中文”
- 什么叫“证据虽弱但收得住”
- 什么叫“引用已经反过来拖累可读性”

## 人工判定结果

### Pass

1. `signal-eval-clue-notion-ai-fluff`
   - 结论：`pass`
   - 理由：title 和 summary 已经把“信息密度被磨没”压成清晰信号，why_now 虽有模板味，但没有空掉。

2. `signal-eval-card-group-ai-automation-ab7fdc5eb9`
   - 结论：`pass`
   - 理由：从“报错”推进到“silent failure”，判断增量明确。

3. `signal-eval-card-cand-ecommerce-sellers-1seeom8-validate`
   - 结论：`pass`
   - 理由：症状和替代方向都压出来了，整卡已经能帮用户判断值不值得追。

4. `signal-eval-card-cand-ai-automation-1sdv3lo-validate`
   - 结论：`pass`
   - 理由：标题和 summary 都把“功能炫不炫”推进成“失控风险”，证据虽弱但收得住。

### Fail

5. `signal-eval-card-cand-ai-automation-1se2nxm-validate`
   - 结论：`fail`
   - tags：`reddit_restatement`, `no_judgment_gain`
   - 理由：基本就是把评论翻译成中文，没有新的判断。

6. `signal-eval-card-cand-business-growth-ops-1s1lelq-validate`
   - 结论：`fail`
   - tags：`reddit_restatement`, `audience_not_who_is_talking`
   - 理由：复述评论，且 audience 更像营销画像，不像真实在聊的人。

7. `signal-eval-card-cand-ai-automation-1sem20t-validate`
   - 结论：`fail`
   - tags：`no_judgment_gain`, `why_now_not_actionable`, `reddit_restatement`
   - 理由：输入证据极弱，输出却硬写成一张卡，整体没有判断增量。

8. `signal-eval-card-cand-ai-automation-1se6nq5-validate`
   - 结论：`fail`
   - tags：`quote_not_used_well`, `why_now_not_actionable`
   - 理由：长英文原话直接搬进 summary，还混进 bot quote，读感像 issue 记录。

## 本轮校准后的硬边界

### 1. `pass` 不等于“每个字段都完美”

这轮人工判定明确给了一个重要边界：

- 如果 title 和 summary 已经完成判断前移
- audience 贴着真实说话的人
- why_now 虽有模板味，但不空

那么这张卡仍然可以 `pass`。

也就是说：

**`why_now` 轻微模板化，不足以单独把整卡打成 fail。**

### 2. `reddit_restatement` 的门槛要收紧

不是只要有原话就算复述。

真正命中是：

- summary 主体几乎就是原帖/评论翻译
- 读完没有新的判断压缩

所以 judge 不应该把“带短引用的好卡”误杀成 `reddit_restatement`。

### 3. `no_judgment_gain` 是整卡级硬伤

这轮 4 个 fail 里，有 3 个都直接或间接碰到这个问题。

一张卡只要：

- 读完还是“知道了，然后呢”
- 没有帮用户完成轻量判断

就该优先挂 `no_judgment_gain`。

### 4. `quote_not_used_well` 不是“用了英文就错”

命中点不是语言，而是：

- quote 太长
- quote 成了正文主体
- quote 里混进了 bot / 自动回复 / 无信息价值内容

### 5. 弱证据样本可以 pass，但必须“收得住”

这轮 pass 样本里已经出现弱证据 case：

- `signal-eval-card-cand-ai-automation-1sdv3lo-validate`

它能过，不是因为证据强，而是因为输出没越界。

所以 judge 不能把“单帖弱证据”机械判死。
真正该判 fail 的是：

- 弱证据
- 还写成趋势 / 共识 / 宽口径结论

## 对 judge 的直接约束

judge 第一轮必须优先学会这 4 件事：

1. 区分“短引用锚点” vs “整段复述 Reddit”
2. 区分“why_now 有点模板” vs “why_now 完全没有判断”
3. 区分“弱证据但收住了” vs “弱证据却写重了”
4. 把 `no_judgment_gain` 当成整卡级主失败，而不是次级标签

## 当前结论

这 8 条样本已经足够把 judge 从抽象 spec 推进到可执行 prompt。

下一步应直接写：

- `signal_judge_prompt_v1`

而不是继续扩充 taxonomy。
