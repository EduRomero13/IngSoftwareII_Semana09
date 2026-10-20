from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base

# JSONB en PostgreSQL, JSON como fallback (sqlite en tests)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)

    role: Mapped[Role] = relationship(back_populates="users")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="assignee")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("dedup_hash", name="uq_alerts_dedup_hash"),
        Index("ix_alerts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)  # wazuh | opnsense | suricata
    rule_id: Mapped[str | None] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(10), nullable=False)  # alta | media | baja
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    src_ip: Mapped[str | None] = mapped_column(String(60))
    dst_ip: Mapped[str | None] = mapped_column(String(60))
    raw_payload: Mapped[dict | None] = mapped_column(JSONType)
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    triage: Mapped["TriageResult | None"] = relationship(back_populates="alert", uselist=False)
    enrichments: Mapped[list["EnrichmentData"]] = relationship(back_populates="alert")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="alert")


class EnrichmentData(Base):
    __tablename__ = "enrichment_data"
    __table_args__ = (Index("ix_enrichment_alert_tool", "alert_id", "tool"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), nullable=False)
    tool: Mapped[str] = mapped_column(String(40), nullable=False)  # virustotal | abuseipdb | geoip
    key: Mapped[str] = mapped_column(String(80), nullable=False)  # ip o hash analizado
    value: Mapped[dict | None] = mapped_column(JSONType)
    queried_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    alert: Mapped[Alert] = relationship(back_populates="enrichments")


class TriageResult(Base):
    __tablename__ = "triage_results"
    __table_args__ = (Index("ix_triage_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), nullable=False, unique=True)
    llm_verdict: Mapped[str] = mapped_column(String(30), nullable=False)  # verdadero_positivo | falso_positivo | sospechoso
    predicted_severity: Mapped[str] = mapped_column(String(10), nullable=False)  # alta | media | baja
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_actions: Mapped[list | dict | None] = mapped_column(JSONType)
    model_name: Mapped[str | None] = mapped_column(String(80))
    engine: Mapped[str] = mapped_column(String(20), default="llm")  # llm | heuristic
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    alert: Mapped[Alert] = relationship(back_populates="triage")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    ticket_id: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    alert: Mapped[Alert | None] = relationship(back_populates="incidents")
    assignee: Mapped[User | None] = relationship(back_populates="incidents")


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_created_at", "created_at"), Index("ix_audit_module", "module"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(80))
    module: Mapped[str] = mapped_column(String(40), nullable=False)  # login | alerts | triage | users | reports | audit | incidents
    action: Mapped[str] = mapped_column(String(40), nullable=False)  # IN | OUT | CREATE | UPDATE | DELETE | READ | EXPORT | EXECUTE
    method: Mapped[str | None] = mapped_column(String(10))
    path: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict | None] = mapped_column(JSONType)
    ip: Mapped[str | None] = mapped_column(String(60))
    status_code: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(80))
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)  # operational | management
    fmt: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | docx | xlsx
    rows_count: Mapped[int | None] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
