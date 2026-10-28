"""Enriquecimiento: modo simulado determinista, intel local y aislamiento de errores."""

from app.config import settings
from app.services import enrichment as intel


def test_mock_malicioso_es_determinista():
    first = intel._mock_virustotal("185.220.101.1")
    second = intel._mock_virustotal("185.220.101.1")
    assert first == second
    assert first["malicious_detections"] == 14
    assert first["mock"] is True


def test_mock_benigno_no_reporta_detecciones():
    result = intel._mock_virustotal("8.8.8.8")
    assert result["malicious_detections"] == 0
    assert result["reputation_score"] == 2


def test_abuseipdb_mock_distingue_maliciosa_benigna_y_privada():
    malicious = intel._mock_abuseipdb("193.32.162.229")
    benign = intel._mock_abuseipdb("1.1.1.1")
    private = intel._mock_abuseipdb("192.168.1.45")
    assert malicious["abuse_confidence_score"] == 92
    assert benign["abuse_confidence_score"] == 0
    assert private["abuse_confidence_score"] == 0
    assert private["country_code"] == "ZZ"


def test_geoip_privada_y_publica():
    private = intel._mock_geoip("10.0.0.8")
    public = intel._mock_geoip("185.220.101.1")
    assert private["is_private"] is True
    assert private["country"] == "Private"
    assert public["is_private"] is False
    assert public["country"] == "Germany"


def test_is_private_maneja_ip_invalida():
    assert intel._is_private("192.168.0.1") is True
    assert intel._is_private("8.8.8.8") is False
    assert intel._is_private("no-es-ip") is False


def test_use_mock_con_flag_global(monkeypatch):
    monkeypatch.setattr(settings, "enrichment_mock", True)
    assert intel.use_mock("virustotal") is True


def test_use_mock_sin_api_key(monkeypatch):
    monkeypatch.setattr(settings, "enrichment_mock", False)
    monkeypatch.setattr(settings, "virustotal_api_key", "")
    monkeypatch.setattr(settings, "abuseipdb_api_key", "clave")
    assert intel.use_mock("virustotal") is True
    assert intel.use_mock("abuseipdb") is False


async def test_enrich_ip_aisla_fallos_por_herramienta(monkeypatch):
    async def _explota(ioc: str) -> dict:
        raise RuntimeError("proveedor caido")

    monkeypatch.setattr(intel, "virustotal_lookup", _explota)
    result = await intel.enrich_ip("193.32.162.229")
    assert result["virustotal"]["error"] == "proveedor caido"
    assert result["abuseipdb"]["ip"] == "193.32.162.229"
    assert result["geoip"]["ip"] == "193.32.162.229"


async def test_enrich_ip_por_defecto_devuelve_tres_tools():
    result = await intel.enrich_ip("8.8.8.8")
    assert set(result) == {"virustotal", "abuseipdb", "geoip"}
