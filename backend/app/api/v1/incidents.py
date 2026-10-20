from app.core.timeutils import utcnow

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import CurrentUser, require_permission
from app.database import get_db
from app.models import Alert, Incident
from app.schemas import IncidentCreate, IncidentOut, IncidentUpdate, Paginated

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=Paginated)
async def list_incidents(
    page: int = 1,
    page_size: int = 20,
    status_: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("incidents.read")),
):
    query = select(Incident)
    count_query = select(func.count(Incident.id))
    if status_:
        query = query.where(Incident.status == status_)
        count_query = count_query.where(Incident.status == status_)
    total = (await db.execute(count_query)).scalar() or 0
    rows = (
        await db.execute(
            query.order_by(Incident.opened_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return Paginated(total=total, page=page, page_size=page_size,
                     items=[IncidentOut.model_validate(i) for i in rows])


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
async def create_incident(
    body: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("incidents.write")),
):
    if body.alert_id is not None:
        alert = (await db.execute(select(Alert).where(Alert.id == body.alert_id))).scalar_one_or_none()
        if not alert:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "alert_id inexistente")
        alert.status = "escalated"
    incident = Incident(
        alert_id=body.alert_id,
        title=body.title,
        severity=body.severity,
        assignee_id=body.assignee_id,
        ticket_id=body.ticket_id,
        notes=body.notes,
    )
    db.add(incident)
    await db.flush()
    await db.commit()
    await db.refresh(incident)
    return IncidentOut.model_validate(incident)


@router.patch("/{incident_id}", response_model=IncidentOut)
async def update_incident(
    incident_id: int,
    body: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("incidents.write")),
):
    incident = (
        await db.execute(select(Incident).where(Incident.id == incident_id))
    ).scalar_one_or_none()
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidente no encontrado")
    changes = {}
    for field in ("status", "severity", "assignee_id", "notes", "ticket_id"):
        value = getattr(body, field)
        if value is not None:
            changes[field] = value
            setattr(incident, field, value)
    if incident.status == "closed" and not incident.closed_at:
        incident.closed_at = utcnow()
    if incident.status != "closed":
        incident.closed_at = None
    await db.commit()
    await db.refresh(incident)
    return IncidentOut.model_validate(incident)


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("incidents.read")),
):
    incident = (await db.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidente no encontrado")
    return IncidentOut.model_validate(incident)
