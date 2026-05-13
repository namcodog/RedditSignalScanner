# phase1017

1. 这轮达到的目的
- 把小程序快照数据治理从口头风险变成可检查、可合并的主线状态。

2. 当前状态变化
- 新增 `check:mini-snapshot-data`，用于检查 `latest / manifest / releases` 是否互相一致。
- PR #2 已合并到 `main`：`a65da7f chore: validate mini snapshot data (#2)`。
- `miniRelease` 和 `miniFavorites` 都已指向实际存在的 `release-6f282273ec9b`，不再引用缺失的 `release-cd596cdbafae` 文件。

3. 还没完成什么
- 这次只治理小程序仓库内快照一致性；没有改变发布生成脚本和云数据库同步链路。

4. 下一步做什么
- 后续凡是更新小程序快照，提交前先跑 `npm run check:mini-snapshot-data`，避免 manifest 再指向不存在的 release 文件。
