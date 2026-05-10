"""Seed canonical 8 business categories."""

from __future__ import annotations

from typing import Sequence

from alembic import op


revision: str = "20260330_000001"
down_revision: str | None = "20260327_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO business_categories (key, display_name, description, is_active)
        VALUES
          ('Ecommerce_Business', 'Ecommerce Business', 'Ecommerce operations, SaaS, sales and business systems', true),
          ('Family_Parenting', 'Family Parenting', 'Parenting, baby, kids and household family decisions', true),
          ('Food_Coffee_Lifestyle', 'Food Coffee Lifestyle', 'Coffee, kitchen, cooking, food tools and beverage lifestyle', true),
          ('Frugal_Living', 'Frugal Living', 'Budgeting, deals, saving money and low-cost living', true),
          ('Home_Lifestyle', 'Home Lifestyle', 'Home, cleaning, decor, appliances and living spaces', true),
          ('Minimal_Outdoor', 'Minimal Outdoor', 'Outdoor, travel, hiking, camping and minimal gear lifestyle', true),
          ('Tools_EDC', 'Tools EDC', 'Tools, knives, flashlights and everyday carry equipment', true),
          ('AI_Workflow', 'AI Workflow', 'AI workflow, automation and model-assisted productivity', true)
        ON CONFLICT (key) DO UPDATE
        SET display_name = EXCLUDED.display_name,
            description = EXCLUDED.description,
            is_active = true
        """
    )


def downgrade() -> None:
    # 分类字典是正式业务基线，降级时不自动删除。
    pass
