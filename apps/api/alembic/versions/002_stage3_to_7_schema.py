"""Stage 3-7 schema additions.

Revision ID: 002_stage3_7
Revises: 001_initial
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_stage3_7"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("checks", sa.Column("deploy_hint", sa.Text()))
    op.add_column("checks", sa.Column("fix_before", sa.Text()))
    op.add_column("checks", sa.Column("fix_after", sa.Text()))
    op.add_column("sites", sa.Column("read_only", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("sites", sa.Column("logo_url", sa.String(2048)))
    op.add_column("llm_usage", sa.Column("simulation_id", postgresql.UUID(as_uuid=True)))
    op.add_column("llm_usage", sa.Column("purpose", sa.String(64)))
    op.add_column("alerts", sa.Column("read_at", sa.DateTime(timezone=True)))
    op.add_column("public_scans", sa.Column("share_slug", sa.String(64)))
    op.add_column("public_scans", sa.Column("is_shared", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("scans", sa.Column("correlation_id", sa.String(64)))
    op.add_column("scans", sa.Column("llm_tokens_used", sa.Integer(), server_default="0", nullable=False))

    op.create_table(
        "fix_applied",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("check_key", sa.String(64), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("site_id", "check_key", name="uq_fix_applied_site_check"),
    )

    op.create_table(
        "api_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "stripe_events",
        sa.Column("event_id", sa.String(255), primary_key=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("stripe_events")
    op.drop_table("api_tokens")
    op.drop_table("fix_applied")
    op.drop_column("scans", "llm_tokens_used")
    op.drop_column("scans", "correlation_id")
    op.drop_column("public_scans", "is_shared")
    op.drop_column("public_scans", "share_slug")
    op.drop_column("alerts", "read_at")
    op.drop_column("llm_usage", "purpose")
    op.drop_column("llm_usage", "simulation_id")
    op.drop_column("sites", "logo_url")
    op.drop_column("sites", "read_only")
    op.drop_column("checks", "fix_after")
    op.drop_column("checks", "fix_before")
    op.drop_column("checks", "deploy_hint")
