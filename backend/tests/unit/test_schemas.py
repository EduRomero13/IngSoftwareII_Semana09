"""Esquemas Pydantic: defaults y validaciones de entrada."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    AlertCreate,
    AuditCreate,
    LoginRequest,
    Paginated,
    UserCreate,
)


def test_alert_create_defaults():
    alert = AlertCreate(title="Sondeo")
    assert alert.source == "wazuh"
    assert alert.severity == "media"
    assert alert.raw_payload is None


def test_alert_create_requiere_titulo():
    with pytest.raises(ValidationError):
        AlertCreate()


def test_user_create_valida_email_username_y_password():
    with pytest.raises(ValidationError):
        UserCreate(username="ab", email="a@b.co", full_name="AB", password="123456")
    with pytest.raises(ValidationError):
        UserCreate(username="valido", email="no-email", full_name="Valido", password="123456")
    with pytest.raises(ValidationError):
        UserCreate(username="valido", email="a@b.co", full_name="Valido", password="123")


def test_login_request_requiere_ambos_campos():
    assert LoginRequest(username="admin", password="x").username == "admin"
    with pytest.raises(ValidationError):
        LoginRequest(username="admin")


def test_audit_create_opcionales():
    entry = AuditCreate(module="triage", action="EXECUTE")
    assert entry.username is None
    assert entry.details is None


def test_paginated_serializa_items():
    page = Paginated(total=1, page=1, page_size=20, items=[{"id": 1}])
    assert page.model_dump()["items"] == [{"id": 1}]
