# phase840

## 时间
- 2026-04-15

## 主题
- SOP 同步到新发布口径
- 今日 30 张发卡前置检查

## 本轮动作
1. 更新 SOP 文档，统一到 `value-threshold publishing`
   - `docs/sop/2026-04-09-稳态运营成功SOP.md`
   - `docs/sop/2026-04-08-评审与发布SOP.md`
2. 按新口径启动今日 30 张发卡前置：
   - `make hotpost-workflow-dry-run`
   - `run_intake_freshness_gate.py --limit 30`
   - `run_offline_publish_plan.py --limit 30`
   - `review_cards.py queue --type validate --limit 30`
   - `review_cards.py queue --type write --limit 20`
   - `daily_collect.py --mode harvest`

## SOP 口径同步结果
- 已明确写入：
  - 主合同从 `fixed-count programming` 切到 `value-threshold publishing`
  - `15` 现在只是默认窗口，不再是 growth 回灌的硬 veto
  - 旧 `9/4/2`、`5/5/5` 只保留为默认参考，不再压制已验证的新 winner
  - 发布前优先看：
    - freshness
    - named topic budget
    - 发布链 / 显示链稳定性
    - 新 winner 是否增强 `candidate -> publish` 穿透

## 今日 30 张前置结果
- `offline_publish_plan-30` 已生成
- 当前 30 窗口库存是够开的，但 freshness 仍未正式放行
- 直接从当前 30 计划反推年龄，可见明显超龄项：
  - `organic-discovery` hot:
    - `cand-business-growth-ops-1sinaiq` 约 `95h`
    - `cand-business-growth-ops-1shhhzo` 约 `126h`
  - `signal` 也有超过 `120h` 的项
- 说明：
  - 今天这轮 30 张**不能直接发**
  - 正确动作仍是先补采集，再重跑 freshness / publish

## 当前真实阻塞
- 不是发布规则冲突
- 不是旧 `15-baseline` 否决
- 是 Reddit API quota 顶住了 `daily_collect --mode harvest`
- 运行中已出现：
  - `429 rate limit`
  - 多个 subreddit search retry / skip

## 当前队列信号
- validate 队列里已有强位：
  - growth hot:
    - `cand-business-growth-ops-1skg672`
    - `cand-business-growth-ops-1sinaiq`
    - `cand-business-growth-ops-1shhhzo`
    - `cand-business-growth-ops-1slqavn`
    - `cand-business-growth-ops-1skd0vb`
  - growth signal:
    - `cand-business-growth-ops-1sij4bv`
    - `cand-business-growth-ops-1sh739c`
    - `cand-business-growth-ops-1sm2jgu`
- write 队列里已有可用 draft，但今天是否正式发出仍以 freshness 过线为前提

## 结论
- SOP 已完成同步
- 今日 30 张发卡已按新口径启动
- 当前还不能直接进入正式发布
- 下一步必须等 harvest collect 结束，或等 Reddit quota 恢复后重跑 freshness gate，再决定最终发布批次
