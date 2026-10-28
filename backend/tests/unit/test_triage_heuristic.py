"""Fallback heurístico del triaje: umbrales, veredicto y acciones."""

import pytest

from app.models import Alert
from app.services.triage import TriageDecision, _heuristic

VERDICTS = {"verdadero_positivo", "falso_positivo", "sospechoso"}
SEVERITIES = {"alta", "media", "baja"}


def _alert(*, severity: str = "media", src_ip: str | None = "45.33.32.156") -> Alert:
    return Alert(
        source="wazuh",
        severity=severity,
        title="Alerta de prueba",
        rule_id="100101",
        src_ip=src_ip,
    )


def _decision(alert: Alert, enrichment: dict | None = None) -> TriageDecision:
    return _heuristic(alert, enrichment or {})


def test_ip_maliciosa_con_severidad_alta_es_verdadero_positivo():
    result = _decision(_alert(severity="alta", src_ip="185.220.101.1"))
    assert result.verdict == "verdadero_positivo"
    assert result.severity == "alta"
    assert result.confidence == pytest.approx(0.83)


def test_ip_benigna_y_severidad_baja_es_falso_positivo():
    result = _decision(_alert(severity="baja", src_ip="8.8.8.8"))
    assert result.verdict == "falso_positivo"
    assert result.severity == "baja"
    assert result.confidence == pytest.approx(0.65)


def test_origen_privado_resta_puntaje():
    result = _decision(_alert(severity="media", src_ip="192.168.1.45"))
    assert result.verdict == "falso_positivo"
    assert result.severity == "baja"


def test_abuseipdb_en_umbral_30_es_sospechoso():
    result = _decision(
        _alert(severity="baja"),
        {"abuseipdb": {"abuse_confidence_score": 75}},
    )
    assert result.verdict == "sospechoso"
    assert result.severity == "media"
    assert result.confidence == pytest.approx(0.55)


def test_virustotal_mas_severidad_media_es_sospechoso():
    result = _decision(
        _alert(severity="media"),
        {"virustotal": {"malicious_detections": 1}},
    )
    assert result.verdict == "sospechoso"
    assert result.severity == "media"


def test_score_exacto_60_es_verdadero_positivo():
    result = _decision(
        _alert(severity="alta"),
        {"virustotal": {"malicious_detections": 1}},
    )
    assert result.verdict == "verdadero_positivo"
    assert result.severity == "alta"


def test_score_55_sigue_siendo_sospechoso():
    result = _decision(
        _alert(severity="alta"),
        {"abuseipdb": {"abuse_confidence_score": 75}},
    )
    assert result.verdict == "sospechoso"
    assert result.severity == "media"


def test_origen_privado_sin_intel_es_falso_positivo():
    result = _decision(_alert(severity="baja", src_ip="192.168.1.10"))
    assert result.verdict == "falso_positivo"


@pytest.mark.parametrize("severity", ["alta", "media", "baja"])
@pytest.mark.parametrize("src_ip", ["185.220.101.1", "8.8.8.8", "192.168.1.5", None])
def test_contrato_de_salida(severity: str, src_ip: str | None):
    result = _decision(_alert(severity=severity, src_ip=src_ip))
    assert result.verdict in VERDICTS
    assert result.severity in SEVERITIES
    assert 0 <= result.confidence <= 1
    assert 2 <= len(result.recommended_actions) <= 5
    assert "Alerta de prueba" in result.summary


def test_resumen_incluye_razones_de_inteligencia():
    result = _decision(_alert(severity="alta", src_ip="193.32.162.229"))
    assert "inteligencia local" in result.summary
    assert "Verdadero positivo" in result.summary or "verdadero positivo" in result.summary
