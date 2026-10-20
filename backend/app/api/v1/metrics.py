from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import CurrentUser, require_permission
from app.database import get_db
from app.schemas import MetricsOverview
from app.services.metrics import overview

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview)
async def metrics_overview(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("metrics.read")),
):
    return await overview(db, days=days)
