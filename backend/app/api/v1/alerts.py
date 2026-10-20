import hashlib

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.rbac import CurrentUser, require_permission
from app.database import get_db
from app.models import Alert
from app.schemas import AlertCreate, AlertDetailOut, AlertOut, AlertStatusUpdate, Paginated

router = APIRouter(prefix="/alerts", tags=["alerts"])

VALID_SEVERITY = {"alta", "media", "baja"}
VALID_STATUS = {"pending", "triaged", "escalated", "closed", "discarded"}


def make_dedup_hash(source: str, rule_id: str | None, src_ip: str | None, dst_ip: str | None, title: str) -> str:
    raw = f"{source}|{rule_id}|{src_ip}|{dst_ip}|{title}".encode()
    return hashlib.sha256(raw).hexdigest()


@router.get("", response_model=Paginated)
async def list_alerts(
    page: int = 1,
    page_size: int = 20,
    severity: str | None = None,
    status_: str | None = Query(None, alias="status"),
    source: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("alerts.read")),
):
    query = select(Alert)
    count_query = select(func.count(Alert.id))
    if severity:
        query = query.where(Alert.severity == severity)
        count_query = count_query.where(Alert.severity == severity)
    if status_:
        query = query.where(Alert.status == status_)
        count_query = count_query.where(Alert.status == status_)
    if source:
        query = query.where(Alert.source == source)
        count_query = count_query.where(Alert.source == source)
    if q:
        pattern = f"%{q}%"
        cond = (Alert.title.ilike(pattern)) | (Alert.description.ilike(pattern)) | (Alert.src_ip.ilike(pattern))
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar() or 0
    rows = (
        await db.execute(
            query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return Paginated(
        total=total,
        page=page,
        page_size=page_size,
        items=[AlertOut.model_validate(a) for a in rows],
    )


@router.get("/{alert_id}", response_model=AlertDetailOut)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("alerts.read")),
):
    alert = (
        await db.execute(
            select(Alert)
            .options(
                selectinload(Alert.triage),
                selectinload(Alert.enrichments),
                selectinload(Alert.incidents),
            )
            .where(Alert.id == alert_id)
        )
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    return AlertDetailOut.model_validate(alert)


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("alerts.write")),
):
    alert = await _insert_alert(db, body, actor=current.username)
    await db.commit()
    await db.refresh(alert)
    return AlertOut.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert_status(
    alert_id: int,
    body: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("alerts.write")),
):
    if body.status not in VALID_STATUS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Estado inválido: {body.status}")
    alert = (await db.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    alert.status = body.status
    await db.commit()
    await db.refresh(alert)
    return AlertOut.model_validate(alert)


@router.post("/webhook", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def webhook_alert(
    body: AlertCreate,
    x_webhook_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Ingesta desde n8n/Wazuh/OPNsense (autenticado con X-Webhook-Token)."""
    if x_webhook_token != settings.webhook_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de webhook inválido")
    alert = await _insert_alert(db, body, actor="webhook")
    dedup = (await db.execute(select(func.count(Alert.id)).where(Alert.dedup_hash == alert.dedup_hash))).scalar()
    await db.commit()
    await db.refresh(alert)
    return {"id": alert.id, "status": alert.status, "duplicates_total": dedup}


async def _insert_alert(db: AsyncSession, body: AlertCreate, *, actor: str = "api") -> Alert:
    if body.severity not in VALID_SEVERITY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Severidad inválida: {body.severity}")
    dedup = make_dedup_hash(body.source, body.rule_id, body.src_ip, body.dst_ip, body.title)
    existing = (await db.execute(select(Alert).where(Alert.dedup_hash == dedup))).scalar_one_or_none()
    if existing:
        return existing  # filtrado de duplicados (n8n IF + unicidad en DB)
    alert = Alert(
        source=body.source,
        rule_id=body.rule_id,
        severity=body.severity,
        title=body.title,
        description=body.description,
        src_ip=body.src_ip,
        dst_ip=body.dst_ip,
        raw_payload=body.raw_payload or {},
        dedup_hash=dedup,
        status="pending",
    )
    db.add(alert)
    await db.flush()
    return alert
