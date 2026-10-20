"""Bitácora de auditoría: registra entradas/salidas por módulo con usuario, fecha, hora y acción."""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

# path primer segmento (después de /api/v1) -> módulo de negocio
PATH_MODULE_MAP = {
    "auth": "login",
    "users": "users",
    "alerts": "alerts",
    "webhook": "alerts",
    "triage": "triage",
    "incidents": "incidents",
    "metrics": "metrics",
    "reports": "reports",
    "audit": "audit",
}

METHOD_ACTION = {
    "POST": "CREATE",
    "PUT": "UPDATE",
    "PATCH": "UPDATE",
    "DELETE": "DELETE",
    "GET": "READ",
}

# Rutas que deben registrarse con una acción especial
SPECIAL_ACTIONS = {
    ("POST", "/api/v1/auth/login"): "IN",      # entrada al sistema
    ("POST", "/api/v1/auth/logout"): "OUT",    # salida del sistema
    ("GET", "/api/v1/reports"): "EXPORT",
    ("POST", "/api/v1/triage"): "EXECUTE",
    ("PATCH", "/api/v1/alerts"): "UPDATE",
}


def resolve_module(path: str) -> str:
    parts = [p for p in path.split("?")[0].split("/") if p]
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        segment = parts[2].split(".")[0]
        return PATH_MODULE_MAP.get(segment, segment)
    return "system"


def resolve_action(method: str, path: str, path_without_id: str) -> str:
    clean = path.split("?")[0]
    for (m, prefix), action in SPECIAL_ACTIONS.items():
        if m == method and (clean == prefix or clean.startswith(prefix)):
            return action
    return METHOD_ACTION.get(method, method)


async def write_audit(
    db: AsyncSession,
    *,
    module: str,
    action: str,
    user_id: int | None = None,
    username: str | None = None,
    method: str | None = None,
    path: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
    status_code: int | None = None,
    commit: bool = False,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        username=username,
        module=module,
        action=action,
        method=method,
        path=path,
        details=details,
        ip=ip,
        status_code=status_code,
    )
    db.add(entry)
    if commit:
        await db.commit()
    else:
        await db.flush()
    return entry


async def audit_request(
    db: AsyncSession,
    request: Request,
    *,
    user_id: int | None,
    username: str | None,
    status_code: int,
) -> None:
    method = request.method
    path = request.url.path
    if not path.startswith("/api/"):
        return
    # POST /alerts/{id}/triage  -> triage/EXECUTE ; GET /alerts/{id} -> alerts/READ
    segments = [p for p in path.split("/") if p]
    module = resolve_module(path)
    path_wo_id = path
    if len(segments) >= 4 and segments[1] == "v1":
        tail = segments[3:]
        # elimina ids numéricos para agrupar acciones por endpoint
        tail = [t for t in tail if not t.isdigit()]
        path_wo_id = "/".join(["", *segments[:3], *tail])
    action = resolve_action(method, path, path_wo_id)
    if path_wo_id.endswith("/triage") or "/triage/" in path_wo_id:
        action = "EXECUTE"
    if method == "GET" and module == "reports":
        action = "EXPORT"
    if method == "GET" and module == "auth" and path.endswith("/me"):
        return  # ruido, no auditar consulta de perfil
    ip = request.client.host if request.client else None
    await write_audit(
        db,
        module=module,
        action=action,
        user_id=user_id,
        username=username,
        method=method,
        path=path,
        ip=ip,
        status_code=status_code,
    )
    await db.commit()
