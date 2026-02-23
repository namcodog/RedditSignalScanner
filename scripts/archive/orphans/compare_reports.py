#!/usr/bin/env python3
"""Compare report headings with reference report."""
import sys
from pathlib import Path


def extract_headings(path: Path) -> list[str]:
    headings: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            headings.append(line.strip("# ").strip())
    return headings


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: compare_reports.py <generated.md> <reference.md>")
        return 1
    generated = Path(sys.argv[1])
    reference = Path(sys.argv[2])
    gen_heads = extract_headings(generated)
    ref_heads = extract_headings(reference)
    missing = [h for h in ref_heads if h not in gen_heads]
    extra = [h for h in gen_heads if h not in ref_heads]
    overlap = len(set(gen_heads) & set(ref_heads))
    sim = int(overlap / max(1, len(ref_heads)) * 100)
    print(f"结构相似度: {sim}%")
    print(f"缺失章节: {len(missing)} -> {missing}")
    print(f"新增章节: {len(extra)} -> {extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
