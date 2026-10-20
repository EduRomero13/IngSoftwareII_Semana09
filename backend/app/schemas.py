from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    permissions: list[str]


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(ORMModel):
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    role_id: int
    role_name: str | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=6, max_length=128)
    role_name: str = "analyst"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None
    password: str | None = None
    role_name: str | None = None


# ---------- Alerts ----------
class AlertOut(ORMModel):
    id: int
    source: str
    rule_id: str | None
    severity: str
    title: str
    description: str | None
    src_ip: str | None
    dst_ip: str | None
    status: str
    created_at: datetime


class AlertDetailOut(AlertOut):
    raw_payload: dict | None
    triage: "TriageOut | None" = None
    enrichments: list["EnrichmentOut"] = []
    incidents: list["IncidentOut"] = []


class AlertCreate(BaseModel):
    source: str = "wazuh"
    rule_id: str | None = None
    severity: str = "media"
    title: str
    description: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    raw_payload: dict | None = None


class AlertStatusUpdate(BaseModel):
    status: str


# ---------- Triage ----------
class TriageOut(ORMModel):
    id: int
    alert_id: int
    llm_verdict: str
    predicted_severity: str
    confidence: float
    summary: str
    recommended_actions: list | dict | None
    model_name: str | None
    engine: str
    tokens_used: int | None
    latency_ms: int | None
    created_at: datetime


class EnrichmentOut(ORMModel):
    id: int
    tool: str
    key: str
    value: dict | None
    queried_at: datetime


# ---------- Incidents ----------
class IncidentCreate(BaseModel):
    alert_id: int | None = None
    title: str
    severity: str = "media"
    assignee_id: int | None = None
    ticket_id: str | None = None
    notes: str | None = None


class IncidentUpdate(BaseModel):
    status: str | None = None
    severity: str | None = None
    assignee_id: int | None = None
    notes: str | None = None
    ticket_id: str | None = None


class IncidentOut(ORMModel):
    id: int
    alert_id: int | None
    title: str
    severity: str
    status: str
    assignee_id: int | None
    ticket_id: str | None
    notes: str | None
    opened_at: datetime
    closed_at: datetime | None


# ---------- Metrics ----------
class MetricsOverview(BaseModel):
    total_alerts: int
    pending_alerts: int
    triaged_alerts: int
    open_incidents: int
    avg_mttt_seconds: float
    false_positive_rate: float
    by_severity: dict[str, int]
    by_status: dict[str, int]
    top_sources: list[dict]
    trend: list[dict]
    recent_triage: list[dict]


# ---------- Audit ----------
class AuditOut(ORMModel):
    id: int
    user_id: int | None
    username: str | None
    module: str
    action: str
    method: str | None
    path: str | None
    details: dict | None
    ip: str | None
    status_code: int | None
    created_at: datetime


class AuditCreate(BaseModel):
    module: str
    action: str
    username: str | None = None
    details: dict | None = None
    ip: str | None = None


class Paginated(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


AlertDetailOut.model_rebuild()
