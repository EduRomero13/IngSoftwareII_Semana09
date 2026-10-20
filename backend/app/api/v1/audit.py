from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit
from app.core.rbac import CurrentUser, require_permission
from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditCreate, AuditOut, Paginated

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Paginated)
async def list_audit(
    page: int = 1,
    page_size: int = 50,
    module: str | None = None,
    action: str | None = None,
    username: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("audit.read")),
):
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    # visibilidad: admin ve todo, el resto solo sus propias entradas
    if not current.is_admin:
        query = query.where(AuditLog.username == current.username)
        count_query = count_query.where(AuditLog.username == current.username)
    elif username:
        query = query.where(AuditLog.username == username)
        count_query = count_query.where(AuditLog.username == username)

    if module:
        query = query.where(AuditLog.module == module)
        count_query = count_query.where(AuditLog.module == module)
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
        count_query = count_query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)
        count_query = count_query.where(AuditLog.created_at <= date_to)

    total = (await db.execute(count_query)).scalar() or 0
    rows = (
        await db.execute(
            query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return Paginated(
        total=total, page=page, page_size=page_size,
        items=[AuditOut.model_validate(r) for r in rows],
    )


@router.get("/summary")
async def audit_summary(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("audit.read")),
):
    by_module = (
        await db.execute(select(AuditLog.module, AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.module, AuditLog.action))
    ).all()
    by_user = (
        await db.execute(
            select(AuditLog.username, func.count(AuditLog.id))
            .group_by(AuditLog.username)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
    ).all()
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    return {
        "total": total,
        "by_module": [{"module": m, "action": a, "count": c} for m, a, c in by_module],
        "top_users": [{"username": u, "count": c} for u, c in by_user if u],
    }


@router.post("", response_model=AuditOut, status_code=status.HTTP_201_CREATED)
async def create_audit_entry(
    body: AuditCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("audit.write")),
):
    """Entrada manual de bitácora (usada por el nodo 10 del workflow n8n)."""
    if not body.module or not body.action:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "module y action son obligatorios")
    entry = await write_audit(
        db,
        module=body.module,
        action=body.action,
        username=body.username,
        details=body.details,
        ip=body.ip,
    )
    await db.commit()
    await db.refresh(entry)
    return AuditOut.model_validate(entry)
