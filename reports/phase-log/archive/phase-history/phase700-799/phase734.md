# Phase 734

## 本轮目标

把已经跑通的 `hot` 实现正式固化成可执行的 SOP 和 skill，避免后续再回到旧的模糊口径。

## 实现

- 更新 `hot-ops`：
  - `.agents/skills/hot-ops/SKILL.md`
  - 明确稳定顺序：
    - `collect`
    - `audit_hot_lane`
    - `queue`
    - `seed`
    - `review`
    - `publish`
    - `push snapshot`
- 更新 `爆贴热点运营SOP`：
  - `docs/sop/2026-04-09-爆贴热点运营SOP.md`
  - 写死：
    - `search-based hot` 白名单 pack
    - 审计先于发布
    - 热点收稿口径
    - 已跑通的热点样本
- 更新 `稳态运营成功SOP`：
  - `docs/sop/2026-04-09-稳态运营成功SOP.md`
  - 把 `hot audit` 接进总工作流

## 结论

- `hot` 现在不只是规则稳了，也不只是前台能看到。
- 更重要的是：
  - 它已经有了独立 skill
  - 有了独立 SOP
  - 有了审计入口
  - 有了收稿口径
- 也就是说，`hot` 这条线现在已经从“靠人记得”变成“照流程就能复现”。

## 下一步

1. 继续按这套 `hot-ops` 跑，争取把 `published_hot_total` 往 `8+` 拉。
2. 继续提整体供卡吞吐，把单轮出卡稳定往上抬。
