"""Auditoría: resolución de módulo/acción y escritura en base de datos."""

from sqlalchemy import select

from app.core.audit import resolve_action, resolve_module, write_audit
from app.models import AuditLog


def test_resolve_module_por_segmento():
    assert resolve_module("/api/v1/alerts/12") == "alerts"
    assert resolve_module("/api/v1/auth/login/json") == "login"
    assert resolve_module("/api/v1/webhook") == "alerts"
    assert resolve_module("/api/v1/incidents?status=open") == "incidents"


def test_resolve_module_fuera_de_api_es_system():
    assert resolve_module("/health") == "system"
    assert resolve_module("/") == "system"


def test_resolve_action_especiales():
    assert resolve_action("POST", "/api/v1/auth/login/json", "/api/v1/auth/login/json") == "IN"
    assert resolve_action("POST", "/api/v1/auth/logout", "/api/v1/auth/logout") == "OUT"
    assert resolve_action("POST", "/api/v1/triage/5", "/api/v1/triage") == "EXECUTE"
    assert resolve_action("GET", "/api/v1/reports?type=pdf", "/api/v1/reports") == "EXPORT"


def test_resolve_action_por_metodo():
    assert resolve_action("POST", "/api/v1/alerts", "/api/v1/alerts") == "CREATE"
    assert resolve_action("PATCH", "/api/v1/alerts/1", "/api/v1/alerts") == "UPDATE"
    assert resolve_action("DELETE", "/api/v1/users/1", "/api/v1/users") == "DELETE"
    assert resolve_action("GET", "/api/v1/alerts", "/api/v1/alerts") == "READ"


async def test_write_audit_persiste_campos(db_session):
    entry = await write_audit(
        db_session,
        module="triage",
        action="EXECUTE",
        user_id=3,
        username="analyst",
        method="POST",
        path="/api/v1/triage/1",
        details={"alert_id": 1, "engine": "heuristic"},
        ip="127.0.0.1",
        status_code=200,
    )
    await db_session.commit()

    stored = (await db_session.execute(select(AuditLog).where(AuditLog.id == entry.id))).scalar_one()
    assert stored.module == "triage"
    assert stored.action == "EXECUTE"
    assert stored.username == "analyst"
    assert stored.details == {"alert_id": 1, "engine": "heuristic"}
    assert stored.status_code == 200


async def test_write_audit_commit_opcional(db_session):
    entry = await write_audit(db_session, module="login", action="IN", commit=True)
    assert entry.id is not None
