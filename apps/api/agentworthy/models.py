"""SQLAlchemy ORM models."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentworthy.database import Base


class Plan(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    AGENCY = "agency"


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    SIMULATING = "simulating"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"


class ScanTrigger(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    FREE_PUBLIC = "free_public"


class CheckCategory(str, enum.Enum):
    DISCOVERABILITY = "discoverability"
    MACHINE_READABILITY = "machine_readability"
    ACTIONABILITY = "actionability"
    TRUST_FRESHNESS = "trust_freshness"
    PERFORMANCE = "performance"


class CheckStatus(str, enum.Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class SimulationOutcome(str, enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAIL = "fail"


class AlertType(str, enum.Enum):
    SCORE_DROP = "score_drop"
    CHECK_REGRESSION = "check_regression"
    SIMULATION_REGRESSION = "simulation_regression"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[Plan] = mapped_column(Enum(Plan, name="plan"), default=Plan.FREE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sites: Mapped[list["Site"]] = relationship(back_populates="user")


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    root_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="sites")
    scans: Mapped[list["Scan"]] = relationship(back_populates="site")
    journeys: Mapped[list["Journey"]] = relationship(back_populates="site")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="site")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"))
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status"), default=ScanStatus.QUEUED, nullable=False
    )
    trigger: Mapped[ScanTrigger] = mapped_column(Enum(ScanTrigger, name="scan_trigger"), nullable=False)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    letter_grade: Mapped[str | None] = mapped_column(String(2))
    site_type: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    site: Mapped["Site | None"] = relationship(back_populates="scans")
    checks: Mapped[list["Check"]] = relationship(back_populates="scan")
    simulations: Mapped[list["Simulation"]] = relationship(back_populates="scan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="scan")


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    category: Mapped[CheckCategory] = mapped_column(Enum(CheckCategory, name="check_category"), nullable=False)
    check_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus, name="check_status"), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    plain_explanation: Mapped[str | None] = mapped_column(Text)
    fix_code: Mapped[str | None] = mapped_column(Text)
    fix_language: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    scan: Mapped["Scan"] = relationship(back_populates="checks")


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[SimulationOutcome] = mapped_column(
        Enum(SimulationOutcome, name="simulation_outcome"), nullable=False
    )
    steps: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    failure_point: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    scan: Mapped["Scan"] = relationship(back_populates="simulations")


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_template: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    site: Mapped["Site"] = relationship(back_populates="journeys")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    type: Mapped[AlertType] = mapped_column(Enum(AlertType, name="alert_type"), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    site: Mapped["Site"] = relationship(back_populates="alerts")
    scan: Mapped["Scan"] = relationship(back_populates="alerts")


class PublicScan(Base):
    __tablename__ = "public_scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    score: Mapped[int | None] = mapped_column(Integer)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scans.id"))
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
