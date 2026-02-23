"""create semantic tables for unified lexicon

Revision ID: 20251116_000032
Revises: 20251114_000031
Create Date: 2025-11-16 00:00:00.000000
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
import yaml


revision: str = "20251116_000032"
down_revision: Union[str, None] = "20251114_000031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEMANTIC_LEXICON_ENV_VAR = "SEMANTIC_LEXICON_PATH"
SEMANTIC_LEXICON_DEFAULT = "backend/config/semantic_sets/unified_lexicon.yml"


def upgrade() -> None:
    """Create semantic_terms, semantic_candidates and semantic_audit_logs tables.

    This migration also seeds semantic_terms from unified_lexicon.yml when可用。
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "semantic_terms" not in tables:
        op.create_table(
            "semantic_terms",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("canonical", sa.String(length=128), nullable=False, unique=True),
            sa.Column("aliases", postgresql.ARRAY(sa.String(length=128)), nullable=True),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("layer", sa.String(length=8), nullable=True),
            sa.Column("precision_tag", sa.String(length=16), nullable=True),
            sa.Column("weight", sa.Numeric(10, 4), nullable=True),
            sa.Column("polarity", sa.String(length=16), nullable=True),
            sa.Column(
                "lifecycle",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'approved'"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_semantic_terms_canonical",
            "semantic_terms",
            ["canonical"],
            unique=True,
        )
        op.create_index(
            "ix_semantic_terms_category_layer",
            "semantic_terms",
            ["category", "layer"],
            unique=False,
        )
        op.create_index(
            "ix_semantic_terms_lifecycle",
            "semantic_terms",
            ["lifecycle"],
            unique=False,
        )

    if "semantic_candidates" not in tables:
        op.create_table(
            "semantic_candidates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("term", sa.String(length=128), nullable=False, unique=True),
            sa.Column("frequency", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("source", sa.String(length=16), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column(
                "reviewed_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reject_reason", sa.Text(), nullable=True),
            sa.Column("approved_category", sa.String(length=32), nullable=True),
            sa.Column("approved_layer", sa.String(length=8), nullable=True),
            sa.Column(
                "created_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "updated_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "status IN ('pending','approved','rejected')",
                name="ck_semantic_candidates_status_valid",
            ),
        )
        op.create_index(
            "ix_semantic_candidates_status",
            "semantic_candidates",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_semantic_candidates_frequency",
            "semantic_candidates",
            ["frequency"],
            unique=False,
        )
        op.create_index(
            "ix_semantic_candidates_first_seen_at",
            "semantic_candidates",
            ["first_seen_at"],
            unique=False,
        )

    if "semantic_audit_logs" not in tables:
        op.create_table(
            "semantic_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("entity_type", sa.String(length=32), nullable=False),
            sa.Column("entity_id", sa.BigInteger(), nullable=False),
            sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "operator_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("operator_ip", sa.String(length=45), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_semantic_audit_logs_entity",
            "semantic_audit_logs",
            ["entity_type", "entity_id"],
        )
        op.create_index(
            "ix_semantic_audit_logs_created_at",
            "semantic_audit_logs",
            ["created_at"],
        )
        op.create_index(
            "ix_semantic_audit_logs_operator_id",
            "semantic_audit_logs",
            ["operator_id"],
        )
        op.create_index(
            "idx_semantic_audit_logs_changes_gin",
            "semantic_audit_logs",
            ["changes"],
            postgresql_using="gin",
        )

    _import_yaml_to_semantic_terms()


def downgrade() -> None:
    op.drop_index("idx_semantic_audit_logs_changes_gin", table_name="semantic_audit_logs")
    op.drop_index("ix_semantic_audit_logs_operator_id", table_name="semantic_audit_logs")
    op.drop_index("ix_semantic_audit_logs_created_at", table_name="semantic_audit_logs")
    op.drop_index("ix_semantic_audit_logs_entity", table_name="semantic_audit_logs")
    op.drop_table("semantic_audit_logs")

    op.drop_index("ix_semantic_candidates_first_seen_at", table_name="semantic_candidates")
    op.drop_index("ix_semantic_candidates_frequency", table_name="semantic_candidates")
    op.drop_index("ix_semantic_candidates_status", table_name="semantic_candidates")
    op.drop_table("semantic_candidates")

    op.drop_index("ix_semantic_terms_lifecycle", table_name="semantic_terms")
    op.drop_index("ix_semantic_terms_category_layer", table_name="semantic_terms")
    op.drop_index("ix_semantic_terms_canonical", table_name="semantic_terms")
    op.drop_table("semantic_terms")


def _iter_yaml_terms(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Flatten unified_lexicon.yml 风格结构为语义术语记录。

    这里遵循“尽量稳妥”的策略：只在结构符合预期时插入数据，
    不抛异常阻塞迁移，避免因为 YAML 细节导致升级失败。
    """
    # 预期结构参考 backend/app/services/semantic/unified_lexicon.py
    # 这里做最小假设：payload["terms"] 为 list[dict]
    terms = payload.get("terms")
    if isinstance(terms, list):
        for item in terms:
            if not isinstance(item, dict):
                continue
            canonical = item.get("canonical")
            category = item.get("category")
            if not canonical or not category:
                continue
            yield {
                "canonical": str(canonical),
                "aliases": item.get("aliases") or [],
                "category": str(category),
                "layer": item.get("layer"),
                "precision_tag": item.get("precision_tag"),
                "weight": item.get("weight"),
                "polarity": item.get("polarity"),
                "lifecycle": item.get("lifecycle") or "approved",
            }


def _import_yaml_to_semantic_terms() -> None:
    """Import unified_lexicon.yml into semantic_terms if possible.

    约束：
    - 不依赖应用代码，只依赖环境变量 SEMANTIC_LEXICON_PATH
    - 出错时记录最小日志（通过 PRINT），但不阻塞迁移
    """
    import os

    path_str = os.getenv(SEMANTIC_LEXICON_ENV_VAR, SEMANTIC_LEXICON_DEFAULT)
    path = Path(path_str)
    if not path.exists():
        # 静默跳过：在部分环境中可能没有语义词典文件
        return

    try:
        with path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
    except Exception:
        # YAML 解析失败不阻塞架构迁移
        return

    rows = list(_iter_yaml_terms(payload))
    if not rows:
        return

    conn = op.get_bind()
    # idempotent：如果已经有数据则不重复导入
    existing = conn.execute(sa.text("SELECT COUNT(1) FROM semantic_terms")).scalar_one()
    if existing:
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO semantic_terms (
                canonical, aliases, category, layer,
                precision_tag, weight, polarity, lifecycle
            )
            VALUES (
                :canonical, :aliases, :category, :layer,
                :precision_tag, :weight, :polarity, :lifecycle
            )
            """
        ),
        rows,
    )
