# Phase 191

## 目标
- 清理 `backend/.env` 中的 `OPENAI_API_KEY`，仅保留 `OPENROUTER_API_KEY`。
- 复跑中文查询“最近 AI 工具领域有什么热门讨论？”并输出结果。

## 变更
- `backend/.env` 删除 `OPENAI_API_KEY` 配置项。

## 验证
- 执行命令：
  - `PYTHONPATH=backend python - <<'PY' ... HotpostService.search(query="最近 AI 工具领域有什么热门讨论？", mode="trending") ... PY`
- 结果：
  - 查询返回：`evidence_count=30`，`confidence=high`，社区包含 `r/artificial` / `r/MachineLearning` / `r/singularity`。
  - Top 3 标题输出正常（见终端输出）。

## 结论
- 仅保留 `OPENROUTER_API_KEY` 可正常完成爆帖速递中文查询。

## 影响范围
- 仅 dev 环境 `.env` 配置。
