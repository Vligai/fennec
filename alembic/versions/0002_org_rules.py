"""add org_rules table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_rules",
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("pattern", sa.String(), nullable=False),
        sa.Column("taint_type", sa.String(), nullable=False),
        sa.Column("scope_glob", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("rule_id"),
    )
    op.create_index("ix_org_rules_org_id", "org_rules", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_org_rules_org_id", table_name="org_rules")
    op.drop_table("org_rules")
