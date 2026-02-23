# Phase 181 - 爆帖速递文档口径修订与复核

日期：2026-01-28

## 本阶段目标
- 按用户要求修订《Reddit爆帖速递_产品模块文档》中的口径不一致与歧义点，并完成复核。

## 修订要点
- 时间默认值统一为“随模式”（trending=week / rant=all / opportunity=month）。
- LLM 可选输出口径明确：未配置 LLM 走降级输出。
- API 限额口径统一为 100 QPM（≈1000/10min）官方，模块自限 90 QPM（900/10min）。
- 证据不足提示统一为“样本有限，仅供预览”。
- 深挖入口声明：报告由主系统 `/api/analyze` 生成，本模块仅传递种子。
- discovered_communities 明确仅 pending，不进入 community_pool。
- 词库示例声明“仅示例，不参与运行”。

## 影响文件
- `docs/Reddit爆帖速递_产品模块文档.md`

## 验证
- 无需运行测试（文档修订）。

