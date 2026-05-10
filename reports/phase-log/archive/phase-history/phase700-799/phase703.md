# phase703

## 本轮完成
- 对 `hotpost_clues.json` 的持续增长问题做了结构判断，不再把它当“只是文件变大”看。

## 现状
- 当前 `backend/data/hotpost_clues.json` 约：
  - `4666` 行
  - `282469` bytes
- 顶层同时包含：
  - `categories`
  - `candidates`
  - `drafts`
  - `published`
- 其中体量最大的是：
  - `published ~= 158 KB`
  - `candidates ~= 43 KB`
- 当前仓库里已有约 `35` 处代码/测试直接依赖这个单文件。

## 结论
- 当前问题不是“文件还没到 1MB 所以先忍着”。
- 真正的问题是：
  - 单文件承担了过多职责
  - 候选、草稿、发布、脚本回填、前台接口都绑在同一个总桶上
- 所以不建议继续维护单桶 `hotpost_clues.json` 作为长期真相源。

## 决策
- 改成三层：
  - 工作集：`categories / candidates / drafts`
  - 发布集：`releases/<release_id>/...`
  - 小程序分发集：云端 `latest + versioned snapshot`
- `hotpost_clues.json` 最多保留为过渡迁移文件，不再继续养大。
