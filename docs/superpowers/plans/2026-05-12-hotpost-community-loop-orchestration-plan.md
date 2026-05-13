# Hotpost Community Loop Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 Hotpost 日常出卡补一个固定编排入口，让“探索计划 -> 小配额 probe -> 正常发卡 -> 发布后社区回流审计 -> R11.5 dry-run”变成可执行、可验收的流程。

**Architecture:** 不重写正式出卡主链，不让 experimental candidates 直接进入正式候选池。新增一个薄编排服务和 CLI：`pre` 阶段只生成探索计划并跑 probe；`post` 阶段只读发布结果，生成 audit 和 R11.5 dry-run。正式 collect / gate / review / publish / snapshot 仍走现有命令。

**Tech Stack:** Python, pytest, existing Hotpost services, existing JSON reports, Makefile targets.

---

## 文件结构

- Create: `backend/app/services/hotpost/community_exploration_orchestrator.py`
  - 责任：把已有 probe、audit、R11.5 dry-run 串起来；只编排，不写正式候选池，不发布卡，不写 DB。
- Create: `backend/scripts/hotpost/run_community_exploration_loop.py`
  - 责任：CLI 入口，支持 `--stage pre|post`，输出日报式 JSON。
- Create: `backend/tests/services/hotpost/test_community_exploration_orchestrator.py`
  - 责任：验证 pre/post 行为、隔离合同、输出字段。
- Modify: `Makefile`
  - 增加 `hotpost-community-exploration-pre` 和 `hotpost-community-exploration-post`。
- Modify: `docs/sop/2026-04-08-日常产卡SOP.md`
  - 把新入口写进日常顺序。
- Modify: `docs/sop/2026-05-10-Hotpost社区探索回流SOP.md`
  - 标准化 pre/post 汇报字段。

---

### Task 1: 编排服务骨架

**Files:**
- Create: `backend/app/services/hotpost/community_exploration_orchestrator.py`
- Test: `backend/tests/services/hotpost/test_community_exploration_orchestrator.py`

- [ ] **Step 1: 写失败测试：pre 阶段必须只跑 probe，不写正式候选池**

```python
import pytest

from app.services.hotpost.community_exploration_orchestrator import (
    ExplorationProbe,
    run_exploration_pre_stage,
)


@pytest.mark.asyncio
async def test_pre_stage_runs_probe_without_formal_persist(monkeypatch):
    calls = []

    async def fake_probe(scope_id, *, max_candidates=None, mode="safe"):
        calls.append((scope_id, max_candidates, mode))
        return {
            "scope_id": scope_id,
            "items": [{"candidate_id": f"cand-{scope_id}-1"}],
            "experimental_only": True,
            "persisted_to_formal_candidates": False,
            "experimental_candidate_store": {
                "path": f"backend/data/hotpost/experimental_candidates/{scope_id}.json",
                "candidate_count": 1,
            },
        }

    monkeypatch.setattr(
        "app.services.hotpost.community_exploration_orchestrator.collect_experimental_scope_probe",
        fake_probe,
    )

    result = await run_exploration_pre_stage(
        probes=[ExplorationProbe(scope_id="ai-automation", max_candidates=6)],
        report_date="2026-05-12",
    )

    assert calls == [("ai-automation", 6, "safe")]
    assert result["stage"] == "pre"
    assert result["contracts"]["writes_formal_candidates"] is False
    assert result["summary"]["probe_count"] == 1
    assert result["summary"]["experimental_candidate_count"] == 1
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/hotpost/test_community_exploration_orchestrator.py::test_pre_stage_runs_probe_without_formal_persist
```

Expected: FAIL，提示模块或函数不存在。

- [ ] **Step 3: 写最小实现**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.services.hotpost.community_probe_collect import collect_experimental_scope_probe


@dataclass(frozen=True)
class ExplorationProbe:
    scope_id: str
    max_candidates: int | None = None
    mode: str = "safe"
    direction: str = ""


async def run_exploration_pre_stage(
    *,
    probes: list[ExplorationProbe],
    report_date: str | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for probe in probes:
        summary = await collect_experimental_scope_probe(
            probe.scope_id,
            max_candidates=probe.max_candidates,
            mode=probe.mode,
        )
        store = dict(summary.get("experimental_candidate_store") or {})
        rows.append(
            {
                "scope_id": probe.scope_id,
                "direction": probe.direction,
                "max_candidates": probe.max_candidates,
                "mode": probe.mode,
                "experimental_candidate_count": int(store.get("candidate_count") or 0),
                "experimental_candidate_path": str(store.get("path") or ""),
                "persisted_to_formal_candidates": bool(summary.get("persisted_to_formal_candidates")),
            }
        )
    return {
        "schema_version": "hotpost-community-exploration-loop/v1",
        "stage": "pre",
        "report_date": report_date or date.today().isoformat(),
        "contracts": {
            "probe_only": True,
            "writes_formal_candidates": False,
            "writes_db": False,
            "auto_promote": False,
        },
        "summary": {
            "probe_count": len(rows),
            "experimental_candidate_count": sum(int(row["experimental_candidate_count"]) for row in rows),
        },
        "probes": rows,
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/hotpost/test_community_exploration_orchestrator.py::test_pre_stage_runs_probe_without_formal_persist
```

Expected: PASS。

---

### Task 2: 发布后回流编排

**Files:**
- Modify: `backend/app/services/hotpost/community_exploration_orchestrator.py`
- Modify: `backend/tests/services/hotpost/test_community_exploration_orchestrator.py`

- [ ] **Step 1: 写失败测试：post 阶段必须只读并输出 audit + R11.5**

```python
@pytest.mark.asyncio
async def test_post_stage_builds_audit_and_feedback_without_db_write(monkeypatch):
    def fake_audit(report_date=None):
        return {
            "schema_version": "hotpost-community-discovery-audit/v1",
            "report_date": "2026-05-12",
            "contracts": {"writes_db": False, "auto_promote": False},
            "rows": [{"community": "r/aeo", "published_count": 1, "suggested_action": "keep_testing"}],
        }

    def fake_feedback(audit_payload, *, pool_community_keys):
        return {
            "schema_version": "hotpost-community-pool-feedback-dry-run/v1",
            "contracts": {"writes_db": False, "auto_promote": False, "requires_human_review": True},
            "summary": {"input_rows": 1, "already_in_pool": 0, "promote_candidate": 0, "keep_testing": 1, "reject": 0},
            "rows": [],
        }

    monkeypatch.setattr(
        "app.services.hotpost.community_exploration_orchestrator.build_current_community_discovery_audit",
        fake_audit,
    )
    monkeypatch.setattr(
        "app.services.hotpost.community_exploration_orchestrator.build_pool_feedback_dry_run",
        fake_feedback,
    )

    result = await run_exploration_post_stage(
        report_date="2026-05-12",
        pool_community_keys=set(),
    )

    assert result["stage"] == "post"
    assert result["contracts"]["writes_db"] is False
    assert result["summary"]["audit_rows"] == 1
    assert result["summary"]["promote_candidate"] == 0
    assert result["summary"]["keep_testing"] == 1
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/hotpost/test_community_exploration_orchestrator.py::test_post_stage_builds_audit_and_feedback_without_db_write
```

Expected: FAIL，提示 `run_exploration_post_stage` 不存在。

- [ ] **Step 3: 写最小实现**

```python
from datetime import date as DateType

from app.services.hotpost.community_discovery_audit import build_current_community_discovery_audit
from app.services.hotpost.community_pool_feedback_dry_run import build_pool_feedback_dry_run


async def run_exploration_post_stage(
    *,
    report_date: str | None = None,
    pool_community_keys: set[str],
) -> dict[str, Any]:
    parsed_date = DateType.fromisoformat(report_date) if report_date else None
    audit = build_current_community_discovery_audit(report_date=parsed_date)
    feedback = build_pool_feedback_dry_run(audit, pool_community_keys=pool_community_keys)
    feedback_summary = dict(feedback.get("summary") or {})
    return {
        "schema_version": "hotpost-community-exploration-loop/v1",
        "stage": "post",
        "report_date": report_date or DateType.today().isoformat(),
        "contracts": {
            "probe_only": True,
            "writes_formal_candidates": False,
            "writes_db": False,
            "auto_promote": False,
            "requires_human_review": True,
        },
        "summary": {
            "audit_rows": len(list(audit.get("rows") or [])),
            "already_in_pool": int(feedback_summary.get("already_in_pool") or 0),
            "promote_candidate": int(feedback_summary.get("promote_candidate") or 0),
            "keep_testing": int(feedback_summary.get("keep_testing") or 0),
            "reject": int(feedback_summary.get("reject") or 0),
        },
        "audit": audit,
        "feedback": feedback,
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/services/hotpost/test_community_exploration_orchestrator.py
```

Expected: PASS。

---

### Task 3: CLI 入口和报告落盘

**Files:**
- Create: `backend/scripts/hotpost/run_community_exploration_loop.py`
- Modify: `backend/tests/services/hotpost/test_community_exploration_orchestrator.py`

- [ ] **Step 1: 写测试：probe 参数解析成固定计划**

```python
from app.services.hotpost.community_exploration_orchestrator import parse_probe_arg


def test_parse_probe_arg_accepts_scope_count_and_direction():
    probe = parse_probe_arg("ai-automation:6:AI工具")
    assert probe.scope_id == "ai-automation"
    assert probe.max_candidates == 6
    assert probe.direction == "AI工具"


def test_parse_probe_arg_rejects_missing_scope():
    with pytest.raises(ValueError, match="probe must use"):
        parse_probe_arg("")
```

- [ ] **Step 2: 实现 parser helper**

```python
def parse_probe_arg(value: str) -> ExplorationProbe:
    parts = [part.strip() for part in value.split(":")]
    if not parts or not parts[0]:
        raise ValueError("probe must use scope[:max_candidates[:direction]]")
    max_candidates = int(parts[1]) if len(parts) >= 2 and parts[1] else None
    direction = parts[2] if len(parts) >= 3 else ""
    return ExplorationProbe(scope_id=parts[0], max_candidates=max_candidates, direction=direction)
```

- [ ] **Step 3: 写 CLI**

```python
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionFactory
from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.community_exploration_orchestrator import (
    parse_probe_arg,
    run_exploration_post_stage,
    run_exploration_pre_stage,
)
from app.services.hotpost.community_pool_feedback_dry_run import load_active_pool_community_keys


async def _run(args):
    if args.stage == "pre":
        return await run_exploration_pre_stage(
            probes=[parse_probe_arg(item) for item in args.probe],
            report_date=args.date,
        )
    async with SessionFactory() as session:
        pool_keys = await load_active_pool_community_keys(session)
    return await run_exploration_post_stage(report_date=args.date, pool_community_keys=pool_keys)


def main() -> None:
    load_backend_env()
    parser = argparse.ArgumentParser(description="Run Hotpost community exploration pre/post loop.")
    parser.add_argument("--stage", choices=["pre", "post"], required=True)
    parser.add_argument("--date", default=None)
    parser.add_argument("--probe", action="append", default=[])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.stage == "pre" and not args.probe:
        parser.error("--stage pre requires at least one --probe scope[:max_candidates[:direction]]")
    payload = asyncio.run(_run(args))
    output = args.output or PROJECT_ROOT / "reports" / "community-governance" / f"community-exploration-{payload['stage']}-{payload['report_date']}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": payload["summary"]}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑 CLI smoke**

Run:

```bash
PYTHONPATH=backend python backend/scripts/hotpost/run_community_exploration_loop.py --stage post --date 2026-05-12 --output backend/tmp/community-exploration-post-smoke.json
```

Expected: 生成 JSON，里面 `contracts.writes_db=false`。

---

### Task 4: Makefile 和 SOP 接入

**Files:**
- Modify: `Makefile`
- Modify: `docs/sop/2026-04-08-日常产卡SOP.md`
- Modify: `docs/sop/2026-05-10-Hotpost社区探索回流SOP.md`

- [ ] **Step 1: 增加 Makefile 入口**

```makefile
hotpost-community-exploration-pre:
	@/bin/sh -c 'set -a; [ -f "$(ENV_FILE)" ] && . "$(ENV_FILE)"; set +a; cd "$(ROOT_DIR)" && "$(PYTHON)" backend/scripts/hotpost/run_community_exploration_loop.py --stage pre $(foreach p,$(PROBES),--probe "$(p)")'

hotpost-community-exploration-post:
	@/bin/sh -c 'set -a; [ -f "$(ENV_FILE)" ] && . "$(ENV_FILE)"; set +a; cd "$(ROOT_DIR)" && "$(PYTHON)" backend/scripts/hotpost/run_community_exploration_loop.py --stage post'
```

- [ ] **Step 2: SOP 写成固定顺序**

日常顺序写成：

```markdown
1. 出卡前：确定 1-3 个探索方向。
2. 跑 `make hotpost-community-exploration-pre PROBES="ai-automation:6:AI工具 ecommerce-sellers:8:SKU选品"`。
3. 跑现有正式出卡链：`make hotpost-publish-until-exhausted`，人工 review / publish，`push_mini_snapshot.py`。
4. 出卡后：跑 `make hotpost-community-exploration-post`。
5. 日报必须写：probe 社区、item_count、draft/publish 结果、R11.5 action、是否有 R12 预审对象。
```

- [ ] **Step 3: 文档检查**

Run:

```bash
git diff --check
```

Expected: no output。

---

### Task 5: 验收

**Files:**
- Test only.

- [ ] **Step 1: 跑相关单测**

Run:

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/services/hotpost/test_community_exploration_orchestrator.py \
  backend/tests/services/hotpost/test_community_probe_collect.py \
  backend/tests/services/hotpost/test_community_discovery_audit.py \
  backend/tests/services/hotpost/test_community_pool_feedback_dry_run.py
```

Expected: PASS。

- [ ] **Step 2: 跑 post smoke**

Run:

```bash
PYTHONPATH=backend python backend/scripts/hotpost/run_community_exploration_loop.py \
  --stage post \
  --output backend/tmp/community-exploration-post-smoke.json
```

Expected:

```json
{
  "summary": {
    "audit_rows": 16
  }
}
```

`audit_rows` 可以随配置变化，但必须大于 0，且输出 JSON 的 `contracts.writes_db` 必须是 `false`。

- [ ] **Step 3: 确认没有污染正式候选池**

Run:

```bash
git diff -- backend/data/hotpost/candidates
```

Expected: pre/post smoke 不应该改正式 candidates 文件。

---

## 自审结论

- 不改 V13 出卡主链，避免把探索社区变成默认正式供给。
- 不自动 publish，不自动 R12 写库，保持人工确认边界。
- 只新增 1 个服务、1 个 CLI、2 个 Makefile 入口和对应测试，复杂度可控。
- 当前计划解决的是“固定入口缺失”，不是重做运营系统。
