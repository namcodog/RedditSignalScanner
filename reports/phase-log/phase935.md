# phase935

1. 这轮达到的目的
- 审计“近期爆帖为什么只有 11 张”，把显示问题和真实库存问题拆清。

2. 当前状态变化
- 最新小程序真相源 [latest.json](/Users/hujia/Desktop/RedditSignalScanner/backend/data/hotpost/mini_snapshots/latest.json) 当前是 `release-433ac35919ac`，总卡数 `66`，其中 `hot=11`、`signal=30`、`breakdown=25`。
- `近期爆帖` 不是前端漏算；它本身只是按 `lane=hot` 过滤，见 [store.js](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js:170) 和 [index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx:56)。
- 当前这 `11` 张里，`4` 张在主面，`7` 张在补充面；所以用户看到 `11`，反映的是当前发布快照里的真实 hot 库存，不是首页渲染 bug。

3. 还没完成什么
- 还没有决定 `近期爆帖` 的产品定义到底是“当前 release 的 hot 库存”，还是“滚动 hot 档案池”；这会直接决定后面是补 hot 供给，还是改 tab 取数口径。

4. 下一步做什么
- 先按当前定义继续运营，不动前端筛选；如果想让 `近期爆帖` 更厚，下一步要么补发更多 hot 卡，要么单独设计 rolling hot archive，不再让它只吃当前 release。
