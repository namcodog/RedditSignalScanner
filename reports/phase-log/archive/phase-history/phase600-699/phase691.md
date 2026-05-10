# phase691

## 本轮完成

1. 补齐最近 6 天的卡片缺口
- 已发布卡数量从 `43` 补到 `49`，净增 `6` 张。
- 本轮新发卡覆盖：
  - AI：`1`
  - 电商：`3`
  - 增长：`2`

2. 根治 hotpost 运营脚本不加载 `backend/.env` 的问题
- 新增统一入口：
  - `backend/app/scripts_support/env_loader.py`
- 已接入：
  - `backend/scripts/hotpost/review_cards.py`
  - `backend/scripts/hotpost/daily_collect.py`
  - `backend/scripts/hotpost/materialize_breakdown_drafts.py`
  - `backend/scripts/hotpost/workflow_dry_run.py`
- 现在 shell 就算先拿到占位 key，脚本也会优先加载 `backend/.env` 的真实配置。

3. 根治 `hotpost_clues.json` 并发写坏问题
- 根因：
  - `candidates / drafts / published` 共用一个 JSON 文件
  - 之前所有写操作都是“整文件读改写”，没有锁，也不是原子替换
  - 并发 publish 时会把 payload 写坏
- 修复：
  - `card_payload_store.py` 增加文件锁 + 原子写入
  - `card_candidate_store.py` 改成统一走 `mutate_cards_payload`
  - `card_draft_store.py` 改成统一走 `mutate_cards_payload`
  - `card_content_generator.py` 的 backfill 写入也改成统一走锁层
- 新增回归测试：
  - `backend/tests/services/hotpost/test_card_payload_store.py`
  - 验证并发 publish 后 payload 仍是合法 JSON，且两张卡都能成功落盘

4. workflow dry-run 已完成真实验证
- 命令：
  - `make hotpost-workflow-dry-run`
- 当前输出已能稳定返回：
  - collect 结果
  - signal queue
  - breakdown materialize 结果
  - write draft queue
  - overlap pair 数量

5. 客户端文案底线继续固化
- `人 -> 用户`
- `脑子 -> 思考`
- 后台黑话默认不直接暴露到客户端

## 本轮验证

### 代码验证

```bash
python -m py_compile \
  backend/app/services/hotpost/card_payload_store.py \
  backend/app/services/hotpost/card_candidate_store.py \
  backend/app/services/hotpost/card_draft_store.py \
  backend/app/services/hotpost/card_content_generator.py \
  backend/scripts/hotpost/review_cards.py \
  backend/scripts/hotpost/daily_collect.py \
  backend/scripts/hotpost/materialize_breakdown_drafts.py \
  backend/scripts/hotpost/workflow_dry_run.py
```

```bash
cd backend && SKIP_DB_RESET=1 pytest \
  tests/services/hotpost/test_card_payload_store.py \
  tests/services/hotpost/test_card_content_generator.py \
  tests/services/hotpost/test_review_card_ops.py -q
```

结果：
- `24 passed`

### 运行态验证

```bash
make hotpost-workflow-dry-run
```

结果：
- `collect_results` 三个 scope 都正常返回
- `signal_queue` 正常
- `breakdown_materialize.count = 0`
- `write_queue` 正常
- `overlap_pair_count = 0`

## 当前阶段结论

- 这轮不是继续做新功能，而是把最近补卡和日常运营这条线彻底跑稳了。
- 现在系统已经具备：
  - 可用的日常产卡 SOP
  - 可用的 ops skill
  - 可用的 Makefile 入口
  - 不会再被占位 key 和并发写文件卡住的运行底座

## 下一步

1. 回到稳态运营，继续按 SOP 更新 signal / breakdown
2. 观察真实读感和点击反馈，再决定下一轮优化开在哪里
3. 如果后续还开优化，优先开更窄的 pack / breakdown polish，而不是重开全局大改
