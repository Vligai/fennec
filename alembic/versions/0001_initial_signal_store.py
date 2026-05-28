"""initial signal store tables

Revision ID: 0001
Revises:
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verdicts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("path_hash", sa.String(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("reviewer_id", sa.String(), nullable=False),
        sa.Column("repo_id", sa.String(), nullable=False),
        sa.Column("service_id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("pattern_fingerprint", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verdicts_path_hash", "verdicts", ["path_hash"])
    op.create_index("ix_verdicts_org_id", "verdicts", ["org_id"])
    op.create_index("ix_verdicts_pattern_fingerprint", "verdicts", ["pattern_fingerprint"])

    op.create_table(
        "sanitizer_trust",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("pattern", sa.String(), nullable=False),
        sa.Column("taint_type", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("verdict_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pattern", "org_id", name="uq_sanitizer_trust_pattern_org"),
    )
    op.create_index("ix_sanitizer_trust_org_id", "sanitizer_trust", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_sanitizer_trust_org_id", table_name="sanitizer_trust")
    op.drop_table("sanitizer_trust")
    op.drop_index("ix_verdicts_pattern_fingerprint", table_name="verdicts")
    op.drop_index("ix_verdicts_org_id", table_name="verdicts")
    op.drop_index("ix_verdicts_path_hash", table_name="verdicts")
    op.drop_table("verdicts")
