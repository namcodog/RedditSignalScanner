# phase1107

## 这轮达到的目的

- Hotpost 探索社区 probe 已补上真隔离：实验候选不再复用正式候选池写入口。

## 当前状态变化

- 新增 `backend/data/hotpost/experimental_candidates/<scope>.json` 作为探索候选独立存储。
- `probe_community_discovery.py` 固定 `persist=False`，只写实验候选文件，并在输出里汇报 `item_count / candidate_count / experimental_candidate_path`。
- `community_discovery_audit` 只读实验候选与正式 draft / release 结果，继续保持 `auto_promote=false / writes_db=false`。

## 还没完成什么

- 当前实验候选文件保存的是每个 scope 的最新 probe 结果，不是按时间保留的历史运行流水。

## 下一步做什么

- 后续如果要看连续 2-3 天晋级趋势，应追加 timestamped 探索报告或 JSONL 历史，不要写入正式候选池。
