from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import CurrentUser, require_permission
from app.database import get_db
from app.services.reports import build_report_data, record_export, render_docx, render_pdf, render_xlsx

router = APIRouter(prefix="/reports", tags=["reports"])

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
EXTENSIONS = {"pdf": "pdf", "docx": "docx", "xlsx": "xlsx"}


@router.get("")
async def generate_report(
    type: str = Query(default="operational", pattern="^(operational|management)$"),
    format: str = Query(default="pdf", pattern="^(pdf|docx|xlsx)$"),
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("reports.export")),
):
    """Reportes exportables: operacional (alertas/MTTT/FP) y de gestión (KPIs/incidentes/cumplimiento)."""
    data = await build_report_data(db, report_type=type, days=days)
    if format == "pdf":
        payload = render_pdf(data)
    elif format == "docx":
        payload = render_docx(data)
    else:
        payload = render_xlsx(data)

    await record_export(
        db,
        user_id=current.id,
        username=current.username,
        report_type=type,
        fmt=format,
        rows=len(data["alerts_table"]),
    )
    filename = f"soclite_{type}_{data['meta']['generated_at'].replace(':', '').replace(' ', '_')}.{EXTENSIONS[format]}"
    return Response(
        content=payload,
        media_type=MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/types")
async def report_types(_: CurrentUser = Depends(require_permission("reports.export"))):
    return {
        "types": [
            {"id": "operational", "label": "Reporte operacional", "sections": ["KPIs", "tendencia", "top orígenes", "alertas y triaje", "auditoría reciente"]},
            {"id": "management", "label": "Reporte de gestión", "sections": ["KPIs", "incidentes", "cumplimiento ISO 27001 / NIST CSF", "recomendaciones"]},
        ],
        "formats": ["pdf", "docx", "xlsx"],
    }
