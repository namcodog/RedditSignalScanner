from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class SequenceRepairResult:
    """Result of a sequence repair for a serial/identity integer PK."""

    sequence_regclass: str
    table_max_id: int
    sequence_previous_next: int
    sequence_new_next: int


async def repair_serial_pk_sequence(
    session: AsyncSession,
    *,
    table_regclass: str,
    pk_column: str = "id",
) -> SequenceRepairResult:
    """
    Repair a PostgreSQL sequence used by a serial/identity primary key.

    Safety rules (to avoid impacting normal business):
    - Never decreases the sequence (avoids ID reuse).
    - Only moves the next value forward so it is > current MAX(id).
    - Does NOT touch table data.
    """
    seq_name = (
        await session.execute(
            text("SELECT pg_get_serial_sequence(:table_regclass, :pk_column)"),
            {"table_regclass": table_regclass, "pk_column": pk_column},
        )
    ).scalar_one_or_none()

    if not seq_name:
        raise RuntimeError(
            f"No serial/identity sequence found for {table_regclass}.{pk_column}"
        )

    table_schema, table_name = _split_qualified_name(table_regclass)
    _validate_ident(table_schema, "schema")
    _validate_ident(table_name, "table")
    _validate_ident(pk_column, "pk_column")

    schema, sequence = _split_qualified_name(seq_name)
    _validate_ident(schema, "sequence schema")
    _validate_ident(sequence, "sequence name")

    table_max_id = int(
        (
            await session.execute(
                text(
                    f'SELECT COALESCE(MAX("{pk_column}"), 0) FROM "{table_schema}"."{table_name}"'
                )
            )
        ).scalar_one()
    )

    last_value, is_called = (
        await session.execute(
            text(f'SELECT last_value, is_called FROM "{schema}"."{sequence}"')
        )
    ).one()
    last_value_int = int(last_value)
    is_called_bool = bool(is_called)

    current_next = last_value_int + 1 if is_called_bool else last_value_int
    target_next = max(table_max_id + 1, current_next)

    await session.execute(
        text("SELECT setval(CAST(:seq AS regclass), :target_next, false)"),
        {"seq": seq_name, "target_next": target_next},
    )

    return SequenceRepairResult(
        sequence_regclass=seq_name,
        table_max_id=table_max_id,
        sequence_previous_next=current_next,
        sequence_new_next=target_next,
    )


def _split_qualified_name(value: str) -> tuple[str, str]:
    """
    Split pg_get_serial_sequence output into (schema, name).

    Examples:
    - public.community_pool_id_seq -> ("public", "community_pool_id_seq")
    - "public"."WeirdSeq" -> ("public", "WeirdSeq")
    """
    raw = value.strip()
    if "." not in raw:
        return "public", raw.strip('"')
    left, right = raw.split(".", 1)
    return left.strip('"'), right.strip('"')


def _validate_ident(value: str, label: str) -> None:
    if not _IDENT_RE.match(value):
        raise ValueError(f"Invalid {label}: {value!r}")
