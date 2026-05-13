#!/usr/bin/env python3
from __future__ import annotations

"""
File-length gate.

Default behavior checks changed/untracked code files and fails when any file
exceeds the configured max line count.
"""

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}
DEFAULT_SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "reports",
    "docs",
    "backups",
    ".specify",
}


def _load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    output: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        output.add(line)
    return output


def _run_git(args: list[str], cwd: Path) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _git_show(repo_root: Path, spec: str) -> str | None:
    completed = subprocess.run(
        ["git", "show", spec],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def _is_code_file(path: Path) -> bool:
    return path.suffix.lower() in DEFAULT_CODE_SUFFIXES


def _is_skipped(path: Path) -> bool:
    return any(part in DEFAULT_SKIP_DIRS for part in path.parts)


def _collect_all_files(repo_root: Path) -> list[Path]:
    files = _run_git(["ls-files"], cwd=repo_root)
    return [repo_root / item for item in files]


def _collect_changed_files(repo_root: Path, base_ref: str) -> list[Path]:
    tracked = _run_git(["diff", "--name-only", "--diff-filter=AM", base_ref], cwd=repo_root)
    untracked = _run_git(["ls-files", "--others", "--exclude-standard"], cwd=repo_root)
    merged = sorted({*tracked, *untracked})
    return [repo_root / item for item in merged]


def _line_count(path: Path) -> int:
    # splitlines() avoids counting a trailing newline as an extra empty line.
    return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check file-length gate")
    parser.add_argument("--scope", choices=("changed", "all"), default="changed")
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--max-lines", type=int, default=300)
    parser.add_argument(
        "--allowlist-file",
        default="backend/config/quality_gates/file_length_allowlist.txt",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    allowlist = _load_allowlist(repo_root / args.allowlist_file)

    if args.max_lines <= 0:
        print("max-lines must be > 0", file=sys.stderr)
        return 2

    if args.scope == "all":
        candidates = _collect_all_files(repo_root)
    else:
        candidates = _collect_changed_files(repo_root, args.base_ref)

    code_files = [
        path
        for path in candidates
        if path.exists() and _is_code_file(path) and not _is_skipped(path.relative_to(repo_root))
    ]

    violations: list[str] = []
    for path in code_files:
        rel_path = str(path.relative_to(repo_root))
        if rel_path in allowlist:
            continue
        lines = _line_count(path)
        if lines <= args.max_lines:
            continue

        # changed 模式走“非回归”门禁：
        # - 新文件超过上限：拦截
        # - 旧文件本来就超长：只有继续变长才拦截（避免一次性阻断历史债务）
        if args.scope == "changed":
            head_text = _git_show(repo_root, f"HEAD:{rel_path}")
            if head_text is None:
                violations.append(f"{rel_path}: {lines} (new file)")
                continue
            old_lines = len(head_text.splitlines())
            if lines > old_lines:
                violations.append(
                    f"{rel_path}: {old_lines} -> {lines} (+{lines - old_lines})"
                )
            continue

        violations.append(f"{rel_path}: {lines}")

    print(
        "file_length_gate scope={scope} max_lines={max_lines} checked={checked} violations={violations}".format(
            scope=args.scope,
            max_lines=args.max_lines,
            checked=len(code_files),
            violations=len(violations),
        )
    )

    if not violations:
        return 0

    print("Files exceeding max lines:", file=sys.stderr)
    for row in sorted(violations):
        print(f"  - {row}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
