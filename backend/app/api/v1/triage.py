from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rbac import CurrentUser, require_permission
from app.database import get_db
from app.models import Alert, TriageResult
from app.schemas import TriageOut
from app.services.triage import run_triage

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/{alert_id}", response_model=TriageOut)
async def triage_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("triage.execute")),
):
    """Ejecuta el agente LangChain (enriquecimiento + LLM Ollama) sobre una alerta."""
    alert = (
        await db.execute(
            select(Alert)
            .options(selectinload(Alert.triage))
            .where(Alert.id == alert_id)
        )
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    try:
        result = await run_triage(db, alert, username=current.username)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return TriageOut.model_validate(result)


@router.post("", response_model=list[TriageOut])
async def triage_pending(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("triage.execute")),
):
    """Triaje por lote de alertas pendientes (replay)."""
    pending = (
        await db.execute(
            select(Alert).where(Alert.status == "pending").order_by(Alert.created_at).limit(limit)
        )
    ).scalars().all()
    results = []
    for alert in pending:
        try:
            results.append(await run_triage(db, alert, username=current.username))
        except RuntimeError:
            continue
    return [TriageOut.model_validate(r) for r in results]


@router.get("/{alert_id}", response_model=TriageOut)
async def get_triage(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("alerts.read")),
):
    row = (
        await db.execute(select(TriageResult).where(TriageResult.alert_id == alert_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta sin triaje")
    return TriageOut.model_validate(row)
