# phase682 - workflow sop and ops skills

## 本阶段完成
- 新增 3 份收尾版本 SOP：
  - `docs/sop/2026-04-08-日常产卡SOP.md`
  - `docs/sop/2026-04-08-优化触发SOP.md`
  - `docs/sop/2026-04-08-评审与发布SOP.md`
- 新增 2 个薄 skill：
  - `.agents/skills/signal-ops/SKILL.md`
  - `.agents/skills/breakdown-ops/SKILL.md`
- 精简更新 `AGENTS.md`，把收尾版本启动初始化需要读取的 SOP 和 skill 写清。

## 关键结果
- 运行时主链继续保留在 backend 代码里，没有制造第二套业务真相源。
- 团队操作层已能通过 SOP + skill 直接调用：
  - signal 日常产卡
  - breakdown 日常产卡
  - 优化触发判断
  - 人审与发布
- 两个 skill 都保持为薄 orchestration 层，不复制 prompt、pack、gate 和 publish 逻辑。

## 验证
- `signal-ops`：39 行
- `breakdown-ops`：39 行
- `AGENTS.md` 已成功引用新 SOP 与 skill 入口

## 当前边界
- 这次只固化流程，不新增功能。
- 这次不把优化工作流做成自动自治系统。
- 下一步应按 SOP 做一次 workflow dry-run，而不是继续扩功能。
