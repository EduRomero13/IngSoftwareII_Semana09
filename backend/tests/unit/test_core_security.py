"""Seguridad: hashing de contraseñas y emisión/validación de JWT."""

import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_no_guarda_texto_plano():
    hashed = hash_password("Secreta123!")
    assert hashed != "Secreta123!"
    assert hashed.startswith("$2")


def test_verify_password_acepta_correcta_y_rechaza_incorrecta():
    hashed = hash_password("Secreta123!")
    assert verify_password("Secreta123!", hashed) is True
    assert verify_password("otra", hashed) is False


def test_verify_password_hash_invalido_devuelve_false():
    assert verify_password("Secreta123!", "no-es-bcrypt") is False


def test_jwt_roundtrip_conserva_claims():
    token = create_access_token(username="analyst", user_id=7, role="analyst")
    payload = decode_token(token)
    assert payload["sub"] == "analyst"
    assert payload["uid"] == 7
    assert payload["role"] == "analyst"


def test_jwt_expirado_lanza_valueerror():
    token = create_access_token(username="analyst", user_id=7, role="analyst", expires_minutes=-1)
    with pytest.raises(ValueError):
        decode_token(token)


def test_jwt_alterado_lanza_valueerror():
    token = create_access_token(username="analyst", user_id=7, role="analyst")
    with pytest.raises(ValueError):
        decode_token(token + "x")
