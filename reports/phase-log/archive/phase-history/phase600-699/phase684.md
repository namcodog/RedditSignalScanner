# phase684 - agents workflow init sync

## 本阶段完成
- 精简更新 `AGENTS.md`
- 将小程序收尾版本的 workflow dry-run 稳定入口补入启动初始化说明

## 关键结果
- 新会话启动时，除了 SOP 和两个 ops skill，现在还会明确看到：
  - `make hotpost-workflow-dry-run`
  - `make hotpost-breakdown-materialize`
  - `make hotpost-breakdown-overlap`
- 同时写清了 dry-run 的默认轻量配额：
  - `HOTPOST_DRY_RUN_MAX_CANDIDATES=1`
  - `HOTPOST_DRY_RUN_QUEUE_LIMIT=2`

## 验证
- `AGENTS.md` 已可检索到上述 4 个新增入口/变量说明

## 当前边界
- 这次只同步启动初始化口径，不新增业务规则，不改主链逻辑。
