# Phase 854 - quota-aware winner 已压进项目侧实现

## 本轮目标
- 把 `discover_first_comment_late_adaptive_pacing_sociavault_assist_v3` 翻成项目侧默认调度行为。

## 当前状态变化
- Reddit API 已回到 freshest `hot / signal` 主采
- SociaVault 固定为 `assist + rescue`
- 调度摘要已返回 `winner / phase_order / providers / collect_stats_total`

## 还没完成什么
- 还没用真实运行数据验证 Reddit API 利用率和 `429` 压力变化

## 下一步做什么
- 跑真实 collect
- 看 `429` 压力、assist/rescue 触发和 publishable gain
