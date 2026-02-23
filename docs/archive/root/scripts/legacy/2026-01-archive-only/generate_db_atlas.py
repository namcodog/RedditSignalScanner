#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Callable, Iterable, TypeVar

import psycopg2


@dataclass(frozen=True)
class ColumnRow:
    table_name: str
    column_name: str
    data_type: str
    is_nullable: str
    column_default: str | None


@dataclass(frozen=True)
class ConstraintRow:
    table_name: str
    constraint_name: str
    constraint_type: str
    constraint_def: str


@dataclass(frozen=True)
class IndexRow:
    table_name: str
    index_name: str
    index_def: str


def _iter_chunks(lines: Iterable[str], *, chunk_size: int) -> Iterable[list[str]]:
    chunk: list[str] = []
    for line in lines:
        chunk.append(line)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _default_database_url() -> str:
    return (
        os.getenv("DB_ATLAS_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://postgres:postgres@localhost:5432/reddit_signal_scanner"
    )


def _query_one(cur, sql: str, params: tuple[object, ...] = ()) -> object | None:
    cur.execute(sql, params)
    row = cur.fetchone()
    if not row:
        return None
    return row[0]


def _fetch_tables(cur, *, schema: str) -> list[str]:
    cur.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = %s
        ORDER BY tablename
        """,
        (schema,),
    )
    return [r[0] for r in cur.fetchall()]


def _fetch_columns(cur, *, schema: str) -> list[ColumnRow]:
    cur.execute(
        """
        SELECT
          table_name,
          column_name,
          data_type,
          is_nullable,
          column_default
        FROM information_schema.columns
        WHERE table_schema = %s
        ORDER BY table_name, ordinal_position
        """,
        (schema,),
    )
    rows: list[ColumnRow] = []
    for table_name, column_name, data_type, is_nullable, column_default in cur.fetchall():
        rows.append(
            ColumnRow(
                table_name=str(table_name),
                column_name=str(column_name),
                data_type=str(data_type),
                is_nullable=str(is_nullable),
                column_default=str(column_default) if column_default is not None else None,
            )
        )
    return rows


def _fetch_constraints(cur, *, schema: str) -> list[ConstraintRow]:
    cur.execute(
        """
        SELECT
          c.relname AS table_name,
          con.conname AS constraint_name,
          CASE con.contype
            WHEN 'p' THEN 'PRIMARY KEY'
            WHEN 'u' THEN 'UNIQUE'
            WHEN 'f' THEN 'FOREIGN KEY'
            WHEN 'c' THEN 'CHECK'
            ELSE con.contype::text
          END AS constraint_type,
          pg_get_constraintdef(con.oid, true) AS constraint_def
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s
        ORDER BY table_name, constraint_type, constraint_name
        """,
        (schema,),
    )
    rows: list[ConstraintRow] = []
    for table_name, constraint_name, constraint_type, constraint_def in cur.fetchall():
        rows.append(
            ConstraintRow(
                table_name=str(table_name),
                constraint_name=str(constraint_name),
                constraint_type=str(constraint_type),
                constraint_def=str(constraint_def),
            )
        )
    return rows


def _fetch_indexes(cur, *, schema: str) -> list[IndexRow]:
    cur.execute(
        """
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = %s
        ORDER BY tablename, indexname
        """,
        (schema,),
    )
    rows: list[IndexRow] = []
    for table_name, indexname, indexdef in cur.fetchall():
        rows.append(
            IndexRow(
                table_name=str(table_name),
                index_name=str(indexname),
                index_def=str(indexdef),
            )
        )
    return rows


T = TypeVar("T")


def _group_by_table(rows: Iterable[T], table_name_of: Callable[[T], str]) -> dict[str, list[T]]:
    grouped: dict[str, list[T]] = {}
    for row in rows:
        table = str(table_name_of(row))
        grouped.setdefault(table, []).append(row)
    return grouped


def _render_table_section(
    *,
    table_name: str,
    columns: list[ColumnRow],
    constraints: list[ConstraintRow],
    indexes: list[IndexRow],
) -> list[str]:
    lines: list[str] = []
    lines.append(f"## `{table_name}`")
    lines.append("")
    lines.append("### 字段")
    lines.append("")
    lines.append("| 字段 | 类型 | 可空 | 默认值 |")
    lines.append("|---|---|---:|---|")
    for col in columns:
        default = (col.column_default or "").replace("\n", " ").strip()
        nullable = "YES" if col.is_nullable.upper() == "YES" else "NO"
        lines.append(
            f"| `{col.column_name}` | `{col.data_type}` | {nullable} | `{default}` |"
        )
    lines.append("")

    if constraints:
        lines.append("### 约束")
        lines.append("")
        for c in constraints:
            lines.append(f"- `{c.constraint_name}` ({c.constraint_type})：`{c.constraint_def}`")
        lines.append("")

    if indexes:
        lines.append("### 索引")
        lines.append("")
        for idx in indexes:
            lines.append(f"- `{idx.index_name}`：`{idx.index_def}`")
        lines.append("")

    return lines


def _render_id_glossary(columns: list[ColumnRow]) -> list[str]:
    id_cols = [
        c
        for c in columns
        if c.column_name == "id"
        or c.column_name.endswith("_id")
        or c.column_name.endswith("_run_id")
        or c.column_name.endswith("_target_id")
    ]
    if not id_cols:
        return []

    lines: list[str] = []
    lines.append("## ID 字段总表（速查）")
    lines.append("")
    lines.append("| 表 | 字段 | 类型 |")
    lines.append("|---|---|---|")
    for c in sorted(id_cols, key=lambda x: (x.table_name, x.column_name)):
        lines.append(f"| `{c.table_name}` | `{c.column_name}` | `{c.data_type}` |")
    lines.append("")
    lines.append("说明：这里只是“长得像 ID 的字段”速查；真正语义请看抓取SOP的“ID口径”章节。")
    lines.append("")
    return lines


def _render_json_fields(columns: list[ColumnRow]) -> list[str]:
    json_cols = [c for c in columns if c.data_type.lower() in {"json", "jsonb"}]
    if not json_cols:
        return []
    lines: list[str] = []
    lines.append("## JSON/JSONB 字段总表（速查）")
    lines.append("")
    lines.append("| 表 | 字段 | 类型 |")
    lines.append("|---|---|---|")
    for c in sorted(json_cols, key=lambda x: (x.table_name, x.column_name)):
        lines.append(f"| `{c.table_name}` | `{c.column_name}` | `{c.data_type}` |")
    lines.append("")
    return lines


def generate_db_atlas(*, database_url: str, schema: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            db_name = str(_query_one(cur, "SELECT current_database()") or "unknown")
            alembic_version = str(_query_one(cur, "SELECT version_num FROM alembic_version") or "unknown")
            table_count = int(_query_one(cur, "SELECT count(*) FROM pg_tables WHERE schemaname=%s", (schema,)) or 0)

            tables = _fetch_tables(cur, schema=schema)
            columns = _fetch_columns(cur, schema=schema)
            constraints = _fetch_constraints(cur, schema=schema)
            indexes = _fetch_indexes(cur, schema=schema)

    cols_by_table = _group_by_table(columns, lambda r: r.table_name)
    constraints_by_table = _group_by_table(constraints, lambda r: r.table_name)
    indexes_by_table = _group_by_table(indexes, lambda r: r.table_name)

    lines: list[str] = []
    lines.append("# Database Architecture Atlas（本地生产库 / 唯一参照）")
    lines.append("")
    lines.append("这份文档回答一句话：**现在这个库里，表/字段/约束到底长什么样？**")
    lines.append("")
    lines.append(f"- 数据库：`{db_name}`")
    lines.append(f"- Schema：`{schema}`")
    lines.append(f"- Alembic 版本：`{alembic_version}`")
    lines.append(f"- 表数量：`{table_count}`")
    lines.append(f"- 生成时间（UTC）：`{generated_at}`")
    lines.append("")
    lines.append("## 怎么重新生成（强烈建议每次 DB 升级后跑一次）")
    lines.append("")
    lines.append("```bash")
    lines.append("# 1) 指定 DATABASE_URL（不要把密码写进文档）")
    lines.append("export DB_ATLAS_DATABASE_URL='postgresql://USER:***@HOST:5432/DBNAME'")
    lines.append("")
    lines.append("# 2) 生成/覆盖本文件")
    lines.append("python scripts/generate_db_atlas.py \\")
    lines.append("  --database-url \"$DB_ATLAS_DATABASE_URL\" \\")
    lines.append(f"  --out \"docs/2025-12-14-database-architecture-atlas.md\"")
    lines.append("```")
    lines.append("")
    lines.extend(_render_id_glossary(columns))
    lines.extend(_render_json_fields(columns))

    lines.append("## 表清单")
    lines.append("")
    lines.append("```")
    for name in tables:
        lines.append(name)
    lines.append("```")
    lines.append("")

    lines.append("## 表结构（逐表）")
    lines.append("")

    for table in tables:
        lines.extend(
            _render_table_section(
                table_name=table,
                columns=cols_by_table.get(table, []),
                constraints=constraints_by_table.get(table, []),
                indexes=indexes_by_table.get(table, []),
            )
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DB schema atlas in Markdown.")
    parser.add_argument("--database-url", default=_default_database_url())
    parser.add_argument("--schema", default="public")
    parser.add_argument(
        "--out",
        default="docs/2025-12-14-database-architecture-atlas.md",
        help="Output markdown file path.",
    )
    args = parser.parse_args()

    output = generate_db_atlas(database_url=str(args.database_url), schema=str(args.schema))
    out_path = Path(str(args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
