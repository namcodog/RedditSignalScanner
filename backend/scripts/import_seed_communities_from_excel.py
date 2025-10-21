from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _load_mapping(path: Path) -> Dict[str, List[str]]:
    try:
        import yaml  # type: ignore
    except Exception:
        # Fallback: minimal default mapping if PyYAML is not installed
        return {
            "name": ["name", "社区", "社区名", "社区名称", "subreddit"],
            "tier": ["tier", "等级", "层级", "级别"],
            "categories": ["categories", "分类", "类别", "类目"],
            "description_keywords": ["description_keywords", "关键词", "关键字", "描述关键词"],
            "daily_posts": ["daily_posts", "日发帖", "日发帖数", "每日帖子数"],
            "avg_comment_length": ["avg_comment_length", "平均评论长度", "评论长度"],
            "quality_score": ["quality_score", "质量评分", "质量分"],
            "is_active": ["is_active", "启用", "活跃", "是否启用"],
        }

    if not path.exists():
        return {
            "name": ["name", "社区", "社区名", "社区名称", "subreddit"],
            "tier": ["tier", "等级", "层级", "级别"],
            "categories": ["categories", "分类", "类别", "类目"],
            "description_keywords": ["description_keywords", "关键词", "关键字", "描述关键词"],
            "daily_posts": ["daily_posts", "日发帖", "日发帖数", "每日帖子数"],
            "avg_comment_length": ["avg_comment_length", "平均评论长度", "评论长度"],
            "quality_score": ["quality_score", "质量评分", "质量分"],
            "is_active": ["is_active", "启用", "活跃", "是否启用"],
        }

    data = yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore
    mapping: Dict[str, List[str]] = {}
    for key, cfg in (data or {}).items():
        aliases = cfg.get("aliases") if isinstance(cfg, dict) else None
        mapping[key] = [a.lower() for a in (aliases or [])]
    return mapping


def _match_columns(columns: List[str], mapping: Dict[str, List[str]]) -> Dict[str, str]:
    lower_map = {c.lower().strip(): c for c in columns}
    result: Dict[str, str] = {}
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in lower_map:
                result[target] = lower_map[alias]
                break
    return result


def _to_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    if not s:
        return []
    # split by comma or Chinese comma
    parts = [p.strip() for p in s.replace("，", ",").split(",")]
    return [p for p in parts if p]


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    return s in {"1", "true", "yes", "y", "是", "真", "启用", "active"}


def convert_excel_to_seed(excel_path: Path, out_path: Path, mapping_path: Path) -> None:
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        print("[ERROR] pandas/openpyxl 未安装。请先执行: pip install pandas openpyxl pyyaml", file=sys.stderr)
        raise

    mapping = _load_mapping(mapping_path)
    df = pd.read_excel(excel_path, engine="openpyxl", header=1)
    if df.empty:
        raise RuntimeError("Excel 文件无数据")

    colmap = _match_columns(list(df.columns), mapping)
    required = ["name"]
    for r in required:
        if r not in colmap:
            raise RuntimeError(f"缺少必要列: {r} (请在 {mapping_path} 中配置映射或修改表头)")

    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        name_raw = str(row.get(colmap["name"], "")).strip()
        if not name_raw:
            continue

        # 只导入 is_active == True 的行（即"最终入选"=="是"）
        is_active = _to_bool(row.get(colmap.get("is_active", ""), True))
        if not is_active:
            continue

        # 跳过不符合 Reddit 社区名称格式的行（如分类标题）
        if not name_raw.startswith("r/"):
            # 如果不是以 r/ 开头，尝试添加前缀
            name = f"r/{name_raw}"
            # 验证是否符合格式 ^r/[a-zA-Z0-9_]+$
            import re
            if not re.match(r'^r/[a-zA-Z0-9_]+$', name):
                continue
        else:
            name = name_raw

        tier = str(row.get(colmap.get("tier", ""), "default") or "default").strip()
        categories = _to_list(row.get(colmap.get("categories", ""), []))
        keywords = _to_list(row.get(colmap.get("description_keywords", ""), []))
        try:
            daily_posts = int(row.get(colmap.get("daily_posts", ""), 0) or 0)
        except Exception:
            daily_posts = 0
        try:
            avg_comment_length = int(row.get(colmap.get("avg_comment_length", ""), 0) or 0)
        except Exception:
            avg_comment_length = 0
        try:
            quality_score = float(row.get(colmap.get("quality_score", ""), 0.5) or 0.5)
        except Exception:
            quality_score = 0.5

        item: Dict[str, Any] = {
            "name": name,
            "tier": tier or "default",
            "categories": categories,
            "description_keywords": keywords,
            "daily_posts": daily_posts,
            "avg_comment_length": avg_comment_length,
            "quality_score": quality_score,
        }
        if not is_active:
            # 保留数据但默认 loader 只加载 is_active==True 的，导入到 DB 时再使用 is_active
            item["is_active"] = False

        rows.append(item)

    payload = {"seed_communities": rows}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已生成种子文件: {out_path} ({len(rows)} 个社区)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert community Excel to seed_communities.json")
    parser.add_argument("excel", type=Path, help="Excel 文件路径 (.xlsx)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/config/seed_communities.json"),
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("backend/config/seed_communities_mapping.yml"),
        help="列名映射配置 (YAML)",
    )
    args = parser.parse_args()

    convert_excel_to_seed(args.excel, args.output, args.mapping)


if __name__ == "__main__":
    main()

