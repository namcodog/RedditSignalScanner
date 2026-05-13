# phase685 - card autoresearch lab v1 contract

## 本阶段完成
- 新增 `card-autoresearch-lab v1` 小合同：
  - `docs/superpowers/specs/2026-04-08-card-autoresearch-lab-v1-contract.md`

## 关键结果
- 明确当前最合适的接法不是“全自动优化引擎”，而是“离线、受控、只优化卡片写法的实验室”。
- 锁定 V1 的优先级：
  1. 先优化 `card_content_prompts.py`
  2. 再优化 `card_content_polish.py`
  3. 最后才考虑 `card_content_rules.yaml` 的软规则
- 明确排除项：
  - 不碰 collect
  - 不碰 gate
  - 不碰 suggestion/materialize/publish 主链
  - 不改 judge 本身

## 当前边界
- 这次只落合同，不实现 runner。
- 这次不启动新一轮 autoresearch 实验。
