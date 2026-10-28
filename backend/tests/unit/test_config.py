"""Configuración: defaults y parseo de listas desde entorno."""

from app.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_defaults_seguros_para_desarrollo():
    settings = _settings()
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.jwt_algorithm == "HS256"
    assert settings.enrichment_mock is True
    assert settings.triage_fallback_enabled is True


def test_cors_origins_list_limpia_espacios_y_vacios():
    settings = _settings(cors_origins=" http://a , http://b ,, ")
    assert settings.cors_origins_list == ["http://a", "http://b"]


def test_cors_origins_vacio():
    assert _settings(cors_origins="").cors_origins_list == []


def test_override_por_entorno(monkeypatch):
    monkeypatch.setenv("WEBHOOK_TOKEN", "token-de-prueba")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    settings = Settings(_env_file=None)
    assert settings.webhook_token == "token-de-prueba"
    assert settings.ollama_model == "mistral"
