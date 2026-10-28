"""Generadores de reportes: PDF, Word y Excel sin base de datos."""

import pytest

from app.services.reports import render_docx, render_pdf, render_xlsx


def _data(report_type: str = "operational") -> dict:
    return {
        "meta": {
            "title": "Reporte de prueba SOC-Lite",
            "type": report_type,
            "generated_at": "2026-01-01 00:00 UTC",
            "period_days": 7,
        },
        "kpis": {
            "Total alertas": 3,
            "Alertas pendientes": 1,
            "Tasa falsos positivos (%)": 33.3,
        },
        "alerts_table": [
            {
                "id": 1,
                "fecha": "2026-01-01 10:00",
                "fuente": "wazuh",
                "severidad": "alta",
                "titulo": "Fuerza bruta SSH",
                "origen": "193.32.162.229",
                "estado": "triaged",
                "veredicto": "verdadero_positivo",
                "severidad_final": "alta",
                "confianza": "90%",
                "motor": "heuristic",
            }
        ],
        "top_sources": [{"ip": "193.32.162.229", "count": 1}],
        "trend": [{"day": "2026-01-01", "total": 1, "alta": 1}],
        "incidents_table": [
            {
                "id": 1,
                "titulo": "Incidente de prueba",
                "severidad": "alta",
                "estado": "open",
                "abertura": "2026-01-01 10:05",
                "cierre": "-",
                "ticket": "OST-1",
            }
        ],
        "audit_table": [
            {
                "fecha": "2026-01-01 10:06:00",
                "usuario": "analyst",
                "modulo": "triage",
                "accion": "EXECUTE",
                "ip": "127.0.0.1",
            }
        ],
        "compliance": [
            {
                "control": "NIST CSF DE.AE",
                "estado": "Implementado",
                "evidencia": "Triaje automatico",
            }
        ],
    }


@pytest.mark.parametrize("report_type", ["operational", "management"])
def test_pdf_tiene_firma_y_contenido(report_type: str):
    content = render_pdf(_data(report_type))
    assert content[:5] == b"%PDF-"
    assert len(content) > 1000


@pytest.mark.parametrize("report_type", ["operational", "management"])
def test_docx_es_zip_valido(report_type: str):
    content = render_docx(_data(report_type))
    assert content[:2] == b"PK"
    assert len(content) > 1000


@pytest.mark.parametrize("report_type", ["operational", "management"])
def test_xlsx_es_zip_valido(report_type: str):
    content = render_xlsx(_data(report_type))
    assert content[:2] == b"PK"
    assert len(content) > 1000


def test_reportes_vacios_no_fallan():
    data = _data("management")
    data["alerts_table"] = []
    data["incidents_table"] = []
    data["audit_table"] = []
    data["top_sources"] = []
    data["trend"] = []
    assert render_pdf(data)[:5] == b"%PDF-"
    assert render_xlsx(data)[:2] == b"PK"
