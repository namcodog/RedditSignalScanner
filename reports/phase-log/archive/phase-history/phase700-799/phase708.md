# phase708

## 发现了什么

- `爆贴热点 V1` 现在已经不是只有 lane 结构，评审规则也已经并入现有工作流。
- 当前最对的做法不是新建 `hot-ops`，而是让 `signal-ops` 继续兼容：
  - `lane=signal` -> `信号快报`
  - `lane=hot` -> `爆贴热点`
- hotpost 存储拆桶后的真相源也已经写进启动口径：
  - 工作集：`categories / candidates / drafts`
  - 发布集：`releases/latest.json` + `releases/<release_id>/cards/*.json`
  - 小程序只读发布快照，不碰内部状态

## 本次改动

- 更新 [signal-ops/SKILL.md](/Users/hujia/Desktop/RedditSignalScanner/.agents/skills/signal-ops/SKILL.md)
  - 加入 `爆贴热点` 的 lane 判定和 review 补充规则
- 更新 [日常产卡SOP.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2026-04-08-%E6%97%A5%E5%B8%B8%E4%BA%A7%E5%8D%A1SOP.md)
  - 写死 `validate` 下的 `signal / hot` 双 lane
  - 明确热点卡的人工评审边界
- 更新 [评审与发布SOP.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2026-04-08-%E8%AF%84%E5%AE%A1%E4%B8%8E%E5%8F%91%E5%B8%83SOP.md)
  - 增加 `爆贴热点` 的发布标准和禁入规则
- 更新 [AGENTS.md](/Users/hujia/Desktop/RedditSignalScanner/AGENTS.md)
  - 补充拆桶后的存储真相源和“小程序只读发布快照”的启动说明

## 结论

- `爆贴热点` 已经制度化，但仍然是 `signal` 主链下的一条 lane，不是第三套系统。
- 现阶段最重要的是继续按现有 `signal-ops` 跑真实卡，观察 `hot lane` 的量和前台差异，而不是继续扩新的 skill / workflow。
