"""Métricas e indicadores del dashboard (NIST CSF DE.AE)."""

from datetime import timedelta
from app.core.timeutils import utcnow

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, Incident, TriageResult


async def overview(db: AsyncSession, days: int = 7) -> dict:
    since = utcnow() - timedelta(days=days)

    total_alerts = (await db.execute(select(func.count(Alert.id)))).scalar() or 0
    pending = (
        await db.execute(select(func.count(Alert.id)).where(Alert.status == "pending"))
    ).scalar() or 0
    triaged = (
        await db.execute(select(func.count(TriageResult.id)))
    ).scalar() or 0
    open_incidents = (
        await db.execute(select(func.count(Incident.id)).where(Incident.status == "open"))
    ).scalar() or 0

    # Distribución por severidad (alertas de origen)
    sev_rows = await db.execute(
        select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)
    )
    by_severity = {r[0]: r[1] for r in sev_rows.all()}
    for key in ("alta", "media", "baja"):
        by_severity.setdefault(key, 0)

    status_rows = await db.execute(
        select(Alert.status, func.count(Alert.id)).group_by(Alert.status)
    )
    by_status = {r[0]: r[1] for r in status_rows.all()}

    # MTTT: tiempo medio entre ingesta de alerta y resultado de triaje (segundos)
    mttt = (
        await db.execute(
            select(
                func.avg(
                    func.extract("epoch", func.coalesce(TriageResult.created_at, Alert.created_at) - Alert.created_at)
                )
            )
            .select_from(Alert)
            .join(TriageResult, TriageResult.alert_id == Alert.id)
        )
    ).scalar()
    avg_mttt = round(float(mttt or 0), 2)

    # Tasa de falsos positivos
    fp_rows = await db.execute(
        select(TriageResult.llm_verdict, func.count(TriageResult.id)).group_by(
            TriageResult.llm_verdict
        )
    )
    verdicts = {r[0]: r[1] for r in fp_rows.all()}
    fp_total = sum(verdicts.values())
    fp_rate = round(verdicts.get("falso_positivo", 0) / fp_total * 100, 1) if fp_total else 0.0

    # Top orígenes (IPs de origen)
    top_rows = await db.execute(
        select(Alert.src_ip, func.count(Alert.id).label("count"))
        .where(Alert.src_ip.is_not(None))
        .group_by(Alert.src_ip)
        .order_by(func.count(Alert.id).desc())
        .limit(5)
    )
    top_sources = [{"ip": r[0], "count": r[1]} for r in top_rows.all()]

    # Tendencia diaria de alertas (últimos N días)
    trend_rows = await db.execute(
        select(
            func.date(Alert.created_at).label("day"),
            func.count(Alert.id),
            func.count(case((Alert.severity == "alta", 1))).label("alta_count"),
        )
        .where(Alert.created_at >= since)
        .group_by(func.date(Alert.created_at))
        .order_by(func.date(Alert.created_at))
    )
    trend = [
        {"day": str(r[0]), "total": r[1], "alta": int(r[2] or 0)}
        for r in trend_rows.all()
    ]

    # Últimos triajes para la tabla del dashboard
    recent_rows = await db.execute(
        select(TriageResult, Alert)
        .join(Alert, Alert.id == TriageResult.alert_id)
        .order_by(TriageResult.created_at.desc())
        .limit(8)
    )
    recent_triage = [
        {
            "alert_id": alert.id,
            "title": alert.title,
            "severity": alert.severity,
            "verdict": triage.llm_verdict,
            "predicted_severity": triage.predicted_severity,
            "confidence": triage.confidence,
            "engine": triage.engine,
            "created_at": triage.created_at.isoformat(),
        }
        for triage, alert in recent_rows.all()
    ]

    return {
        "total_alerts": total_alerts,
        "pending_alerts": pending,
        "triaged_alerts": triaged,
        "open_incidents": open_incidents,
        "avg_mttt_seconds": avg_mttt,
        "false_positive_rate": fp_rate,
        "by_severity": by_severity,
        "by_status": by_status,
        "top_sources": top_sources,
        "trend": trend,
        "recent_triage": recent_triage,
        "window_days": days,
    }
