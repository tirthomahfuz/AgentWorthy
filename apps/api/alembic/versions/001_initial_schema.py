"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-07-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    plan_enum = postgresql.ENUM("free", "starter", "pro", "agency", name="plan", create_type=False)
    scan_status_enum = postgresql.ENUM(
        "queued", "crawling", "simulating", "scoring", "complete", "failed",
        name="scan_status", create_type=False,
    )
    scan_trigger_enum = postgresql.ENUM(
        "manual", "scheduled", "free_public", name="scan_trigger", create_type=False,
    )
    check_category_enum = postgresql.ENUM(
        "discoverability", "machine_readability", "actionability",
        "trust_freshness", "performance", name="check_category", create_type=False,
    )
    check_status_enum = postgresql.ENUM(
        "pass", "warn", "fail", "not_applicable", name="check_status", create_type=False,
    )
    simulation_outcome_enum = postgresql.ENUM(
        "success", "partial", "fail", name="simulation_outcome", create_type=False,
    )
    alert_type_enum = postgresql.ENUM(
        "score_drop", "check_regression", "simulation_regression",
        name="alert_type", create_type=False,
    )

    op.execute("CREATE TYPE plan AS ENUM ('free', 'starter', 'pro', 'agency')")
    op.execute(
        "CREATE TYPE scan_status AS ENUM "
        "('queued', 'crawling', 'simulating', 'scoring', 'complete', 'failed')"
    )
    op.execute(
        "CREATE TYPE scan_trigger AS ENUM ('manual', 'scheduled', 'free_public')"
    )
    op.execute(
        "CREATE TYPE check_category AS ENUM "
        "('discoverability', 'machine_readability', 'actionability', "
        "'trust_freshness', 'performance')"
    )
    op.execute(
        "CREATE TYPE check_status AS ENUM ('pass', 'warn', 'fail', 'not_applicable')"
    )
    op.execute(
        "CREATE TYPE simulation_outcome AS ENUM ('success', 'partial', 'fail')"
    )
    op.execute(
        "CREATE TYPE alert_type AS ENUM "
        "('score_drop', 'check_regression', 'simulation_regression')"
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255)),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("plan", plan_enum, nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("root_url", sa.String(2048), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verification_token", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id")),
        sa.Column("status", scan_status_enum, nullable=False, server_default="queued"),
        sa.Column("trigger", scan_trigger_enum, nullable=False),
        sa.Column("overall_score", sa.Integer()),
        sa.Column("letter_grade", sa.String(2)),
        sa.Column("site_type", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id"), nullable=False),
        sa.Column("category", check_category_enum, nullable=False),
        sa.Column("check_key", sa.String(64), nullable=False),
        sa.Column("status", check_status_enum, nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("plain_explanation", sa.Text()),
        sa.Column("fix_code", sa.Text()),
        sa.Column("fix_language", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "simulations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id"), nullable=False),
        sa.Column("task_key", sa.String(64), nullable=False),
        sa.Column("task_description", sa.Text(), nullable=False),
        sa.Column("outcome", simulation_outcome_enum, nullable=False),
        sa.Column("steps", postgresql.JSONB()),
        sa.Column("failure_point", sa.Text()),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "journeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("task_template", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id"), nullable=False),
        sa.Column("type", alert_type_enum, nullable=False),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("emailed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "public_scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("score", sa.Integer()),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "llm_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id")),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_checks_scan_id", "checks", ["scan_id"])
    op.create_index("ix_public_scans_ip_hash", "public_scans", ["ip_hash"])


def downgrade() -> None:
    op.drop_index("ix_public_scans_ip_hash")
    op.drop_index("ix_checks_scan_id")
    op.drop_table("llm_usage")
    op.drop_table("public_scans")
    op.drop_table("alerts")
    op.drop_table("journeys")
    op.drop_table("simulations")
    op.drop_table("checks")
    op.drop_table("scans")
    op.drop_table("sites")
    op.drop_table("users")
    op.execute("DROP TYPE alert_type")
    op.execute("DROP TYPE simulation_outcome")
    op.execute("DROP TYPE check_status")
    op.execute("DROP TYPE check_category")
    op.execute("DROP TYPE scan_trigger")
    op.execute("DROP TYPE scan_status")
    op.execute("DROP TYPE plan")
