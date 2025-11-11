#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import yaml


def load_yaml(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"crawler.yml not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, Mapping):
        raise ValueError("crawler.yml must be a mapping")
    return data


def to_markdown(cfg: Mapping[str, Any]) -> str:
    g = cfg.get("global", {}) or {}
    tiers = cfg.get("tiers", []) or []
    fallback = (g.get("fallback_thresholds") or {})

    lines: list[str] = []
    lines.append("# Crawler Dry Run\n")
    lines.append("## Global\n")
    lines.append(f"- concurrency: {g.get('concurrency', '-')}")
    lines.append(f"- timeout_seconds: {g.get('timeout_seconds', '-')}")
    lines.append(f"- rate_limit_per_minute: {g.get('rate_limit_per_minute', '-')}")
    lines.append(f"- hot_cache_ttl_hours: {g.get('hot_cache_ttl_hours', '-')}")
    lines.append(f"- watermark_enabled: {g.get('watermark_enabled', '-')}")
    lines.append(f"- watermark_grace_hours: {g.get('watermark_grace_hours', '-')}")
    if fallback:
        lines.append("- fallback_thresholds:")
        for k, v in fallback.items():
            lines.append(f"  - {k}: {v}")
    lines.append("")

    lines.append("## Tiers\n")
    for t in tiers:
        lines.append(f"### {t.get('name','T?')}\n")
        lines.append(f"- match_tiers: {t.get('match_tiers', [])}")
        lines.append(f"- re_crawl_frequency: {t.get('re_crawl_frequency','-')}")
        lines.append(f"- time_filter: {t.get('time_filter','-')}")
        lines.append(f"- sort_mix: {json.dumps(t.get('sort_mix', {}))}")
        lines.append(f"- post_limit: {t.get('post_limit','-')}")
        lines.append(f"- hot_cache_ttl_hours: {t.get('hot_cache_ttl_hours','-')}")
        retry = t.get('retry') or {}
        if retry:
            lines.append(f"- retry.max_retries: {retry.get('max_retries','-')}")
        fb = t.get('fallback') or {}
        if fb:
            lines.append("- fallback:")
            for k, v in fb.items():
                lines.append(f"  - {k}: {v}")
        lines.append("")

    # Schedules
    lines.append("## Suggested Celery beat schedule\n")
    for t in tiers:
        name = str(t.get('name','T?'))
        freq = str(t.get('re_crawl_frequency','-'))
        lines.append(f"- {name}: every {freq} → tasks.crawler.crawl_seed_communities_incremental")
    lines.append("- low_quality_backfill: every 4h → tasks.crawler.crawl_low_quality_communities")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="backend/config/crawler.yml")
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    cfg = load_yaml(Path(args.config))
    md = to_markdown(cfg)
    print(md)

    out = args.output
    if not out:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = f"reports/local-acceptance/crawler-dryrun-{ts}.md"
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

