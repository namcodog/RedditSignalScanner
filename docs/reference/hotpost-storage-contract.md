# Hotpost Storage Contract

更新日期：2026-04-09

这份协议只管一件事：
**hotpost 拆桶之后，哪些 JSON 是什么性质，谁能改，怎么改，哪些绝对不能碰。**

## 1. 先记住一句话

不要把这些 JSON 当成“一堆差不多的文件”。
它们不是一个层级：

- `candidates` 是原料池
- `drafts` 是工作区
- `releases` 是正式资产
- `published` 只是 `latest release` 的运行时投影
- `mini_snapshots` 和 `cloudfunctions/*/data` 只是分发缓存

如果这个层级混了，后面一定会重新长乱。

## 2. 当前磁盘布局

```text
backend/data/hotpost/
  categories.json
  candidates/
    <source_scope_id>.json
  drafts/
    <draft_id>.json
  releases/
    latest.json
    <release_id>/
      index.json
      cards/
        <card_id>.json
  mini_snapshots/
    latest.json
    manifest.json
    releases/
      <release_id>.json
```

## 3. 状态边界

| 状态 | 磁盘位置 | 性质 | 谁能写 | 维护原则 |
| --- | --- | --- | --- | --- |
| `categories` | `categories.json` | 低频配置 | 明确的配置修改入口 | 少改，人工 review |
| `candidates` | `candidates/*.json` | 原料池 / 短生命周期 | collect / candidate store | 允许按 scope 覆盖，不当正式资产 |
| `drafts` | `drafts/*.json` | 工作区 / 待评审半成品 | draft store / review 流程 | 只能按 `draft_id` 精确改，不准整桶替换 |
| `releases` | `releases/latest.json` + `releases/<release_id>/...` | 正式发布资产 | 只有 publish / release 写入链 | release 不可变，回滚只改 `latest` 指针 |
| `published` | 不单独落文件；由 `latest release` 运行时加载 | 当前线上视图 | 不直接写磁盘 | 不当编辑区，只能通过 release 变更 |
| `mini_snapshots` | `mini_snapshots/*` | 小程序发布快照 | `push_mini_snapshot.py` | 派生产物，坏了就重推 |
| 小程序 `cloudfunctions/*/data` | `hotpost-mini/.../cloudfunctions/*/data/*` | 云函数打包缓存 | `push_mini_snapshot.py` | 派生产物，绝不手改 |

## 4. 唯一允许的共享入口

### 4.1 状态编排层

只有这两个文件可以直接编排状态 JSON：

- [card_storage_layout.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_storage_layout.py)
- [card_payload_store.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_payload_store.py)

其他代码不允许绕开共享入口，自己去拼路径、直接读写 JSON。

### 4.2 读入口

业务层现在只应该用这些窄读入口：

- `load_categories()`
- `load_candidates()`
- `load_drafts()`
- `load_published_cards()`

### 4.3 写入口

业务层现在只应该用这些命名写入口：

- `mutate_candidates()`
- `mutate_drafts()`
- `mutate_drafts_and_published()`
- `mutate_published_cards()`
- `merge_published_cards()`
- `replace_published_cards()`

`mutate_cards_payload()` 只允许留在状态编排层内部，不允许业务代码继续直接用。

## 5. 每一类文件怎么维护

### 5.1 candidates

把它当“原料池”，不要当“资产库”。

- 允许按 `source_scope_id` 替换
- 允许按 `candidate_id` upsert
- 允许被下一轮 collect 覆盖
- 不建议人工直接打开 JSON 手改

一句话：
**候选要敢于覆盖，不要试图永久保存。**

### 5.2 drafts

把它当“工作单”。

- 一份 draft 对应一个 `draft_id`
- 只允许按 `draft_id` 更新 / 删除
- publish 时把它移出 draft 区，再进入 release
- 不允许整桶替换所有 drafts

一句话：
**draft 可以改，但只能精确改单张。**

### 5.3 releases

把它当“正式资产账本”。

- 每次发布都生成新的 `release_id`
- 历史 release 不允许就地 patch
- 回滚方式只改 `latest.json`
- 旧 release 保留，方便回看和回滚

一句话：
**release 必须不可变。**

### 5.4 published

`published` 只是运行时为了兼容和读取方便，对 `latest release` 的展开结果。

- 它不是独立文件
- 它不该被理解成长期编辑区
- polish / backfill 如果改的是线上内容，本质上还是在生成新的发布视图

一句话：
**published 是视图，不是资产层。**

### 5.5 mini snapshots

这是分发缓存，不是真相源。

- 小程序只读它
- 内容错了，回源修 release，再重新 push
- 绝不在 snapshot 里手补内容
- 当前 `snapshot.cards` 允许同时承载两层表面：
  - `surface_bucket = main`
  - `surface_bucket = supplement`
- 当前 `snapshot meta` 还会带：
  - `main_card_count`
  - `supplement_card_count`
  - `surface_contracts`

理解方式固定为：

- `main` = 主前台 freshness 面
- `supplement` = 15 天内仍有价值的补充面
- `surface_bucket` 只用于后台选择和审计，不是前端分类字段

它们共用一份 snapshot，是为了分发简单；
但它们的**选择规则和展示规则必须解耦**。

一句话：
**派生产物只重推，不手修。**

## 6. 绝对禁止

下面这些做法一律算违规：

1. 业务代码自己拼 `backend/data/hotpost/...` 路径直接改 JSON
2. 只想改 `published`，却 `load_cards_payload() -> write_cards_payload()` 整桶回写
3. 手改旧 `release` 文件
4. 手改 `mini_snapshots` 或 `cloudfunctions/*/data`
5. 把 `candidates` 当长期资产保养
6. 把 `published` 当人工编辑区

## 7. 正常生命周期

```text
collect
  -> candidates
seed / materialize
  -> drafts
review / publish
  -> releases/<release_id>
  -> releases/latest.json
push mini snapshot
  -> mini_snapshots/*
  -> cloudfunctions/*/data/*
```

## 8. 每次改存储前的检查清单

任何改动 hotpost 存储前，先问这 6 个问题：

1. 这次改的是哪一层：原料、工作区、正式资产，还是派生缓存？
2. 这次写入是不是走了命名共享入口？
3. 有没有把不该改的状态顺手一起覆盖掉？
4. 如果要回滚，这次改动能不能只靠 `latest` 指针回滚？
5. 这次改的是内容真相源，还是分发缓存？
6. 需要补什么测试来防回潮？

## 9. 当前结论

当前最重要的不是继续换存储技术，而是守住这 3 条：

1. `candidates` 允许脏、允许覆盖
2. `drafts` 允许改，但只能精确改
3. `releases` 不允许改；`snapshots` 也不允许手改

只要这 3 条不破，hotpost 的 JSON 维护成本就还能控住。
