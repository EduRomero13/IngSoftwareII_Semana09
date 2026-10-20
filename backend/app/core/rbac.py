"""RBAC: mapa de permisos por rol (roles persistidos en DB, permisos versionados en código)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db
from app.models import User

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "alerts.read", "alerts.write", "triage.execute", "incidents.read", "incidents.write",
        "metrics.read", "reports.export", "audit.read", "audit.write", "users.read", "users.manage",
    },
    "analyst": {
        "alerts.read", "alerts.write", "triage.execute", "incidents.read", "incidents.write",
        "metrics.read", "reports.export", "audit.read",
    },
    "viewer": {
        "alerts.read", "metrics.read", "incidents.read", "reports.export", "audit.read",
    },
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def permissions_for_role(role: str) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())


class CurrentUser:
    def __init__(self, user: User, role: str, permissions: set[str]):
        self.user = user
        self.id = user.id
        self.username = user.username
        self.role = role
        self.permissions = permissions

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def can(self, permission: str) -> bool:
        return permission in self.permissions


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token sin sujeto")
    result = await db.execute(select(User).where(User.username == username, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inexistente o inactivo")
    role = payload.get("role") or "viewer"
    return CurrentUser(user, role, permissions_for_role(role))


def require_permission(permission: str):
    async def checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current.can(permission):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Permiso requerido: {permission}"
            )
        return current

    return checker
