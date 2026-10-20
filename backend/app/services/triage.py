"""Servicio de triaje: agente LangChain (tools de enriquecimiento + LLM local Ollama)
con fallback heurístico determinista cuando el LLM no está disponible."""

import asyncio
import time
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.audit import write_audit
from app.models import Alert, EnrichmentData, TriageResult
from app.services import enrichment as intel

SYSTEM_PROMPT = """Eres un analista SOC senior de nivel L1/L2 trabajando en un SOC-Lite para PYMES.
Tu tarea es triar (priorizar y clasificar) alertas de seguridad recibidas de Wazuh/OPNsense.

Reglas:
1. Usa las herramientas para enriquecer la IP/IOC sospechosa (VirusTotal, AbuseIPDB, GeoIP, inteligencia local).
2. Determina si la alerta es un VERDADERO positivo, FALSO positivo o sospechoso.
3. Asigna la severidad final: alta, media o baja (puede subir o bajar la severidad original).
4. Resume la alerta en máximo 3 frases en español, orientado a la acción.
5. Propón entre 2 y 5 acciones concretas y ejecutables por un analista de PYME.
6. Responde SIEMPRE con el esquema JSON solicitado. Confianza entre 0 y 1.
Criterios: un escaneo de puertos desde una IP interna suele ser falso positivo; tráfico hacia IPs
de inteligencia pública conocida, C2 o fuerza bruta es verdadero positivo; tráfico no bloqueado
sin contexto suficiente es sospechoso.
"""


class TriageDecision(BaseModel):
    verdict: str = Field(description="verdadero_positivo | falso_positivo | sospechoso")
    severity: str = Field(description="alta | media | baja")
    confidence: float = Field(description="confianza entre 0 y 1")
    summary: str = Field(description="resumen ejecutivo en español, max 3 frases")
    recommended_actions: list[str] = Field(description="2 a 5 acciones concretas en español")


def build_tools() -> list:
    @tool("virustotal_lookup")
    async def virustotal_lookup(ioc: str) -> dict[str, Any]:
        """Consulta reputación de una IP o hash en VirusTotal (modo simulado sin API key)."""
        return await intel.virustotal_lookup(ioc)

    @tool("abuseipdb_lookup")
    async def abuseipdb_lookup(ip: str) -> dict[str, Any]:
        """Consulta reportes de abuso de una IP pública en AbuseIPDB (modo simulado sin API key)."""
        return await intel.abuseipdb_lookup(ip)

    @tool("geoip_lookup")
    def geoip_lookup(ip: str) -> dict[str, Any]:
        """Obtiene país/ciudad/continente de una IP."""
        return intel.geoip_lookup(ip)

    @tool("threat_intel_local")
    def threat_intel_local(ip: str) -> dict[str, Any]:
        """Verifica la IP en la lista local de inteligencia de amenazas (maliciosas/benignas conocidas)."""
        if ip in intel.KNOWN_MALICIOUS_IPS:
            return {"ip": ip, "known_malicious": True, "context": intel.KNOWN_MALICIOUS_IPS[ip]}
        if ip in intel.KNOWN_BENIGN_IPS:
            return {"ip": ip, "known_malicious": False, "context": intel.KNOWN_BENIGN_IPS[ip]}
        return {"ip": ip, "known_malicious": False, "context": "sin coincidencias en inteligencia local"}

    return [virustotal_lookup, abuseipdb_lookup, geoip_lookup, threat_intel_local]


async def _persist_enrichment(db: AsyncSession, alert_id: int, ip: str, data: dict) -> None:
    for tool_name, value in data.items():
        existing = (
            await db.execute(
                select(EnrichmentData).where(
                    EnrichmentData.alert_id == alert_id,
                    EnrichmentData.tool == tool_name,
                    EnrichmentData.key == ip,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                EnrichmentData(alert_id=alert_id, tool=tool_name, key=ip, value=value)
            )
    await db.flush()


def _heuristic(alert: Alert, enrichment: dict) -> TriageDecision:
    """Fallback determinista cuando Ollama no responde (o LLM deshabilitado)."""
    vt = enrichment.get("virustotal", {}) or {}
    abuse = enrichment.get("abuseipdb", {}) or {}
    score = 0
    reasons: list[str] = []

    src = alert.src_ip or ""
    if src in intel.KNOWN_MALICIOUS_IPS:
        score += 45
        reasons.append(f"IP {src} en inteligencia local: {intel.KNOWN_MALICIOUS_IPS[src]}")
    if (vt.get("malicious_detections") or 0) > 0:
        score += 35
        reasons.append(f"VirusTotal: {vt.get('malicious_detections')} detecciones maliciosas")
    if (abuse.get("abuse_confidence_score") or 0) >= 75:
        score += 30
        reasons.append(f"AbuseIPDB: {abuse['abuse_confidence_score']}% confianza de abuso")
    if alert.severity == "alta":
        score += 25
    elif alert.severity == "media":
        score += 10
    if intel._is_private(src) and score < 45:
        score -= 15
        reasons.append("origen en red privada (posible tráfico interno)")

    if score >= 60:
        verdict, severity = "verdadero_positivo", "alta"
        confidence = min(0.95, 0.6 + score / 300)
    elif score >= 30:
        verdict, severity = "sospechoso", "media"
        confidence = 0.55
    else:
        verdict, severity = "falso_positivo", "baja"
        confidence = 0.65

    summary = (
        f"Alerta '{alert.title}' ({alert.source}, severidad {alert.severity}). "
        + (" ".join(reasons) if reasons else "Sin indicios de amenaza en el enriquecimiento consultado.")
        + f" Veredicto: {verdict.replace('_', ' ')} con severidad final {severity}."
    )
    if verdict == "verdadero_positivo":
        actions = [
            f"Bloquear {src} en el firewall/IDS de perímetro",
            "Crear incidente y escalar al responsable de seguridad",
            "Revisar el host de destino en busca de indicadores de compromiso",
            "Correlacionar con alertas de las últimas 24 h del mismo origen",
        ]
    elif verdict == "sospechoso":
        actions = [
            "Solicitar contexto adicional (logs del host, tráfico asociado)",
            "Monitorear el origen durante las próximas 24 h",
            "Verificar si la actividad está asociada a un cambio o job conocido",
        ]
    else:
        actions = [
            "Marcar como falso positivo y documentar el motivo",
            "Evaluar afinar la regla para reducir ruido recurrente",
        ]
    return TriageDecision(
        verdict=verdict,
        severity=severity,
        confidence=round(confidence, 2),
        summary=summary,
        recommended_actions=actions,
    )


async def _llm_available() -> bool:
    if settings.llm_provider != "ollama":
        return False
    try:
        async with httpx_client() as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def httpx_client():
    import httpx

    return httpx.AsyncClient(timeout=5.0)


async def run_triage(db: AsyncSession, alert: Alert, *, username: str | None = None) -> TriageResult:
    start = time.perf_counter()
    ip = alert.src_ip or alert.dst_ip or ""

    # 1) Enriquecimiento persistente (caché por alerta+herramienta+clave)
    enrichment_data: dict = {}
    if ip:
        enrichment_data = await intel.enrich_ip(ip)
        await _persist_enrichment(db, alert.id, ip, enrichment_data)

    decision: TriageDecision | None = None
    engine = "heuristic"
    model_name = None
    tokens_used = None

    # 2) Intento con agente LangChain + Ollama
    if await _llm_available():
        try:
            model = ChatOllama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=0.1,
                timeout=settings.llm_timeout_seconds,
            )
            agent = create_agent(
                model,
                build_tools(),
                system_prompt=SYSTEM_PROMPT,
                response_format=TriageDecision,
            )
            user_prompt = (
                f"Alerta a triar:\n"
                f"- Título: {alert.title}\n"
                f"- Fuente: {alert.source} (regla {alert.rule_id or 'n/a'})\n"
                f"- Severidad original: {alert.severity}\n"
                f"- Origen: {ip} | Destino: {alert.dst_ip or 'n/a'}\n"
                f"- Descripción: {alert.description or 'sin descripción'}\n\n"
                f"Enriquecimiento ya obtenido:\n{enrichment_data}\n\n"
                f"Triara esta alerta. Usa herramientas si necesitas verificar más contexto."
            )
            result = await asyncio.wait_for(
                agent.ainvoke({"messages": [("user", user_prompt)]}),
                timeout=settings.llm_timeout_seconds + 15,
            )
            response = result.get("response")
            if isinstance(response, TriageDecision):
                decision = response
            elif isinstance(response, dict):
                decision = TriageDecision(**response)
            else:
                decision = TriageDecision.model_validate_json(str(response))
            engine = "llm"
            model_name = settings.ollama_model
            # intenta obtener usage de metadata
            for msg in result.get("messages", [])[::-1]:
                meta = getattr(msg, "usage_metadata", None)
                if meta:
                    tokens_used = meta.get("total_tokens")
                    break
        except Exception:  # noqa: BLE001 - cualquier fallo LLM cae al heurístico
            decision = None

    if decision is None:
        if not settings.triage_fallback_enabled:
            raise RuntimeError("Triaje LLM no disponible y fallback deshabilitado")
        decision = _heuristic(alert, enrichment_data)

    latency_ms = int((time.perf_counter() - start) * 1000)

    # 3) Persistencia
    existing = (
        await db.execute(select(TriageResult).where(TriageResult.alert_id == alert.id))
    ).scalar_one_or_none()
    if existing:
        row = existing
        row.llm_verdict = decision.verdict
        row.predicted_severity = decision.severity
        row.confidence = decision.confidence
        row.summary = decision.summary
        row.recommended_actions = decision.recommended_actions
        row.model_name = model_name
        row.engine = engine
        row.tokens_used = tokens_used
        row.latency_ms = latency_ms
    else:
        row = TriageResult(
            alert_id=alert.id,
            llm_verdict=decision.verdict,
            predicted_severity=decision.severity,
            confidence=decision.confidence,
            summary=decision.summary,
            recommended_actions=decision.recommended_actions,
            model_name=model_name,
            engine=engine,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )
        db.add(row)

    alert.status = "triaged"
    await db.flush()

    await write_audit(
        db,
        module="triage",
        action="EXECUTE",
        username=username,
        method="POST",
        path=f"/api/v1/triage/{alert.id}",
        details={
            "alert_id": alert.id,
            "verdict": decision.verdict,
            "severity": decision.severity,
            "engine": engine,
            "latency_ms": latency_ms,
        },
    )
    await db.commit()
    await db.refresh(row)
    return row
