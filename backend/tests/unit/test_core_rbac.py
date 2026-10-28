"""RBAC: matriz de permisos por rol y dependencia require_permission."""

import pytest
from fastapi import HTTPException

from app.core.rbac import (
    ROLE_PERMISSIONS,
    CurrentUser,
    permissions_for_role,
    require_permission,
)


class _User:
    id = 1
    username = "tester"


def _current(role: str) -> CurrentUser:
    return CurrentUser(_User(), role, permissions_for_role(role))


def test_admin_tiene_todos_los_permisos():
    assert permissions_for_role("admin") == {
        "alerts.read",
        "alerts.write",
        "triage.execute",
        "incidents.read",
        "incidents.write",
        "metrics.read",
        "reports.export",
        "audit.read",
        "audit.write",
        "users.read",
        "users.manage",
    }


def test_viewer_solo_lectura():
    perms = permissions_for_role("viewer")
    assert "alerts.read" in perms
    assert "triage.execute" not in perms
    assert "users.manage" not in perms
    assert "audit.write" not in perms


def test_analyst_no_gestiona_usuarios():
    perms = permissions_for_role("analyst")
    assert "triage.execute" in perms
    assert "users.read" not in perms
    assert "users.manage" not in perms


def test_rol_desconocido_no_tiene_permisos():
    assert permissions_for_role("root") == set()
    assert permissions_for_role("") == set()


def test_current_user_flags():
    admin = _current("admin")
    viewer = _current("viewer")
    assert admin.is_admin is True
    assert admin.can("users.manage") is True
    assert viewer.is_admin is False
    assert viewer.can("users.manage") is False


async def test_require_permission_permite():
    checker = require_permission("alerts.read")
    assert await checker(current=_current("viewer")) is not None


async def test_require_permission_deniega_con_403():
    checker = require_permission("users.manage")
    with pytest.raises(HTTPException) as exc:
        await checker(current=_current("analyst"))
    assert exc.value.status_code == 403
