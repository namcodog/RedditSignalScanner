# Phase I-Full: scripts/ 73 文件域分家执行记录

日期: 2026-03-05
执行人: Codex

## 1) 发现了什么？
- `backend/scripts/` 已按 9 个业务域完成目录拆分。
- 目标脚本已按映射完成 `git mv`，`hunt_rant_posts.py` 与 `hunt_rant_focused.py` 也已移入 `scoring/`。
- 全仓库 `.mk/.sh/.py/.yml/.yaml/.md` 的目标路径引用已完成替换，并排除了 `docs/archive/`。
- `backend/scripts/README.md` 已按指定内容创建。
- 验证结果：
  - scripts 根目录无 `.py/.sh/.sql` 残留（输出 `CLEAN`）。
  - 子目录文件数：`crawl=9, semantic=10, import=10, report=7, scoring=7, community=10, monitor=6, seed=7, infra=7`。
  - Makefile 残留检查显示的是其他未纳入本次映射的脚本（如 `trigger_incremental_crawl.py` 等），不在本次迁移范围。
  - 额外自检确认：目标扩展名范围内无旧路径残留；`docs/archive/` 未被修改。

## 2) 是否需要修复？
- 本次映射范围内不需要额外修复。
- 非映射脚本路径（例如 `makefiles/*.mk` 中仍引用的其它 `scripts/*.py`）如需继续域分家，需单独开下一轮迁移任务。

## 3) 精确修复方法
- 本次已执行，未改业务逻辑，仅做结构迁移与引用更新：
  - `mkdir -p backend/scripts/{crawl,semantic,import,report,scoring,community,monitor,seed,infra}`
  - 按清单执行 `git mv`
  - 批量替换 `scripts/<base>` -> `scripts/<subdir>/<base>`（排除 `docs/archive/`）

## 4) 下一步系统性的计划是什么？
- 若要继续收口，可新增 Phase I-补充：
  - 梳理并迁移 `makefiles` 中未纳入本次映射的脚本（如 `trigger_incremental_crawl.py`、`check_breaking_changes.py` 等）。
  - 再跑一次全仓库路径一致性巡检，形成最终收口清单。

## 5) 这次执行的价值是什么？达到了什么目的？
- 达成了脚本按业务域归档，显著提升了定位效率，后续 AI 与人工排障/运维查找路径更直接。
- 在不改业务逻辑、不触库、不跑 Python 的前提下完成结构化重组，风险可控。
