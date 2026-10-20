"""Generación de reportes operacionales y de gestión en PDF, Word y Excel."""


from docx import Document
from docx.shared import Inches
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, AuditLog, Incident, ReportExport, TriageResult, User
from app.core.timeutils import utcnow
from app.services.metrics import overview

HEADER_FILL = PatternFill("solid", fgColor="1F3A5F")
HEADER_FONT = Font(color="FFFFFF", bold=True)


async def build_report_data(db: AsyncSession, report_type: str, days: int = 30) -> dict:
    metrics = await overview(db, days=min(days, 7))

    alert_rows = (
        await db.execute(
            select(Alert, TriageResult)
            .outerjoin(TriageResult, TriageResult.alert_id == Alert.id)
            .order_by(Alert.created_at.desc())
            .limit(200)
        )
    ).all()
    alerts = [
        {
            "id": a.id,
            "fecha": a.created_at.strftime("%Y-%m-%d %H:%M"),
            "fuente": a.source,
            "severidad": a.severity,
            "titulo": a.title,
            "origen": a.src_ip or "-",
            "estado": a.status,
            "veredicto": t.llm_verdict if t else "pendiente",
            "severidad_final": t.predicted_severity if t else "-",
            "confianza": f"{round((t.confidence or 0) * 100)}%" if t else "-",
            "motor": t.engine if t else "-",
        }
        for a, t in alert_rows
    ]

    incidents = (
        await db.execute(select(Incident).order_by(Incident.opened_at.desc()).limit(100))
    ).scalars().all()
    incident_list = [
        {
            "id": i.id,
            "titulo": i.title,
            "severidad": i.severity,
            "estado": i.status,
            "abertura": i.opened_at.strftime("%Y-%m-%d %H:%M"),
            "cierre": i.closed_at.strftime("%Y-%m-%d %H:%M") if i.closed_at else "-",
            "ticket": i.ticket_id or "-",
        }
        for i in incidents
    ]

    audit_total = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    audit_by_module = (
        await db.execute(select(AuditLog.module, func.count(AuditLog.id)).group_by(AuditLog.module))
    ).all()
    recent_audit = (
        await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50))
    ).scalars().all()
    audit_list = [
        {
            "fecha": e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": e.username or "-",
            "modulo": e.module,
            "accion": e.action,
            "ip": e.ip or "-",
        }
        for e in recent_audit
    ]

    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0

    verdict_rows = (
        await db.execute(
            select(TriageResult.llm_verdict, func.count(TriageResult.id)).group_by(
                TriageResult.llm_verdict
            )
        )
    ).all()
    verdicts = {r[0]: r[1] for r in verdict_rows}

    compliance = [
        {
            "control": "NIST CSF DE.AE — Análisis de anomalías",
            "estado": "Implementado",
            "evidencia": f"Triaje automático de {metrics['triaged_alerts']} alertas; MTTT promedio {metrics['avg_mttt_seconds']} s",
        },
        {
            "control": "ISO 27001 A.8.15 — Registro de eventos",
            "estado": "Implementado",
            "evidencia": f"Bitácora con {audit_total} eventos en {len(audit_by_module)} módulos",
        },
        {
            "control": "ISO 27001 A.5.24 — Respuesta a incidentes",
            "estado": "Implementado" if incident_list else "Parcial",
            "evidencia": f"{len([i for i in incident_list if i['estado'] == 'open'])} incidentes abiertos / {len(incident_list)} totales",
        },
        {
            "control": "ISO 27001 A.5.15 — Control de acceso (RBAC)",
            "estado": "Implementado",
            "evidencia": f"{users_count} usuarios con roles y permisos granulares",
        },
        {
            "control": "ISO 27001 A.8.16 — Monitoreo de redes",
            "estado": "Implementado" if metrics["total_alerts"] else "Parcial",
            "evidencia": f"{metrics['total_alerts']} alertas ingeridas desde Wazuh/OPNsense",
        },
    ]

    data = {
        "meta": {
            "title": "Reporte Operacional SOC-Lite" if report_type == "operational" else "Reporte de Gestión SOC-Lite",
            "type": report_type,
            "generated_at": utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "period_days": days,
        },
        "kpis": {
            "Total alertas": metrics["total_alerts"],
            "Alertas pendientes": metrics["pending_alerts"],
            "Alertas triadas": metrics["triaged_alerts"],
            "MTTT promedio (s)": metrics["avg_mttt_seconds"],
            "Tasa falsos positivos (%)": metrics["false_positive_rate"],
            "Incidentes abiertos": metrics["open_incidents"],
            "Verdaderos positivos": verdicts.get("verdadero_positivo", 0),
            "Sospechosos": verdicts.get("sospechoso", 0),
        },
        "alerts_table": alerts,
        "top_sources": metrics["top_sources"],
        "trend": metrics["trend"],
        "incidents_table": incident_list,
        "audit_table": audit_list,
        "compliance": compliance,
        "audit_total": audit_total,
        "audit_by_module": [{"modulo": m, "eventos": c} for m, c in audit_by_module],
    }
    return data


# --------------------------------------------------------------------------- PDF
def render_pdf(data: dict) -> bytes:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#1F3A5F"))
    h_style = ParagraphStyle("H", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#1F3A5F"), spaceBefore=10)
    cell_style = ParagraphStyle("C", parent=styles["Normal"], fontSize=7, leading=9)

    doc = SimpleDocTemplate(
        "/tmp/_soclite_report.pdf",
        pagesize=landscape(A4),
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )
    story = [
        Paragraph(data["meta"]["title"], title_style),
        Paragraph(
            f"Generado: {data['meta']['generated_at']} · Período: últimos {data['meta']['period_days']} días",
            styles["Normal"],
        ),
        Spacer(1, 8),
        Paragraph("1. Indicadores clave (KPIs)", h_style),
    ]

    kpi_rows = [[k, str(v)] for k, v in data["kpis"].items()]
    kpi_table = Table(kpi_rows, colWidths=[9 * cm, 5 * cm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF3FA")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C7DD")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ]
        )
    )
    story.append(kpi_table)

    story.append(Paragraph("2. Tendencia de alertas (7 días)", h_style))
    trend_rows = [["Día", "Total", "Severidad alta"]] + [
        [t["day"], str(t["total"]), str(t["alta"])] for t in data["trend"]
    ] or [["Día", "Total", "Severidad alta"], ["-", "-", "-"]]
    story.append(_rl_table(trend_rows, [6 * cm, 4 * cm, 5 * cm]))

    story.append(Paragraph("3. Top orígenes de alertas", h_style))
    src_rows = [["IP origen", "Alertas"]] + [[s["ip"], str(s["count"])] for s in data["top_sources"]] or [
        ["IP origen", "Alertas"],
        ["-", "-"],
    ]
    story.append(_rl_table(src_rows, [8 * cm, 4 * cm]))

    if data["meta"]["type"] == "operational":
        story.append(Paragraph("4. Últimas alertas y triaje", h_style))
        header = ["ID", "Fecha", "Fuente", "Sev.", "Título", "Estado", "Veredicto", "Sev. final"]
        rows = [header] + [
            [str(a["id"]), a["fecha"], a["fuente"], a["severidad"], a["titulo"][:48],
             a["estado"], a["veredicto"], a["severidad_final"]]
            for a in data["alerts_table"][:40]
        ]
        story.append(_rl_table(rows, [1.5 * cm, 3.2 * cm, 2.4 * cm, 1.6 * cm, 8.5 * cm, 2.4 * cm, 4 * cm, 2.2 * cm], 6.5))

        story.append(Paragraph("5. Auditoría reciente (usuarios, fecha, hora, acción)", h_style))
        aud_rows = [["Fecha/hora", "Usuario", "Módulo", "Acción", "IP"]] + [
            [a["fecha"], a["usuario"], a["modulo"], a["accion"], a["ip"]] for a in data["audit_table"][:25]
        ]
        story.append(_rl_table(aud_rows, [4.5 * cm, 4 * cm, 4 * cm, 3.5 * cm, 4 * cm], 7))
    else:
        story.append(Paragraph("4. Incidentes", h_style))
        inc_rows = [["ID", "Título", "Severidad", "Estado", "Apertura", "Ticket"]] + [
            [str(i["id"]), i["titulo"][:50], i["severidad"], i["estado"], i["abertura"], i["ticket"]]
            for i in data["incidents_table"]
        ] or [["ID", "Título", "Severidad", "Estado", "Apertura", "Ticket"], ["-", "-", "-", "-", "-", "-"]]
        story.append(_rl_table(inc_rows, [1.5 * cm, 9 * cm, 2.5 * cm, 2.5 * cm, 4 * cm, 4 * cm]))

        story.append(Paragraph("5. Estado de cumplimiento (ISO 27001 / NIST CSF)", h_style))
        comp_rows = [["Control", "Estado", "Evidencia"]] + [
            [c["control"], c["estado"], c["evidencia"]] for c in data["compliance"]
        ]
        story.append(_rl_table(comp_rows, [9 * cm, 3.5 * cm, 14 * cm], 7))

        story.append(Paragraph("6. Recomendaciones de gestión", h_style))
        recs = [
            "Mantener el triaje automatizado 24/7 para sostener el MTTT en minutos y no en horas.",
            "Revisar semanalmente la tasa de falsos positivos y afinar reglas del SIEM (Wazuh).",
            "Capacitar al equipo sobre el procedimiento de respuesta a incidentes (ISO 27001 A.5.24).",
            "Auditar trimestralmente la bitácora y los roles RBAC.",
            "Reservar personal nocturno solo para alertas de severidad alta confirmadas.",
        ]
        for r in recs:
            story.append(Paragraph(f"• {r}", styles["Normal"]))

    doc.build(story)
    with open("/tmp/_soclite_report.pdf", "rb") as fh:
        return fh.read()


def _rl_table(rows, widths, fontsize=7):
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=fontsize, leading=fontsize + 2)
    wrapped = [
        [Paragraph(str(c).replace("&", "&amp;").replace("<", "&lt;"), cell) for c in row]
        for row in rows
    ]
    table = Table(wrapped, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B7C7DD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FC")]),
                ("FONTSIZE", (0, 0), (-1, -1), fontsize),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


# -------------------------------------------------------------------------- DOCX
def render_docx(data: dict) -> bytes:
    doc = Document()
    doc.add_heading(data["meta"]["title"], level=0)
    doc.add_paragraph(
        f"Generado: {data['meta']['generated_at']} · Período: últimos {data['meta']['period_days']} días"
    )

    doc.add_heading("1. Indicadores clave (KPIs)", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text = "Indicador", "Valor"
    for k, v in data["kpis"].items():
        row = table.add_row().cells
        row[0].text, row[1].text = str(k), str(v)

    doc.add_heading("2. Tendencia de alertas (7 días)", level=1)
    _docx_table(doc, ["Día", "Total", "Severidad alta"],
                [[t["day"], str(t["total"]), str(t["alta"])] for t in data["trend"]] or [["-", "-", "-"]])

    doc.add_heading("3. Top orígenes", level=1)
    _docx_table(doc, ["IP origen", "Alertas"],
                [[s["ip"], str(s["count"])] for s in data["top_sources"]] or [["-", "-"]])

    if data["meta"]["type"] == "operational":
        doc.add_heading("4. Alertas y triaje", level=1)
        cols = ["ID", "Fecha", "Fuente", "Sev.", "Título", "Estado", "Veredicto", "Sev. final"]
        _docx_table(
            doc, cols,
            [[str(a["id"]), a["fecha"], a["fuente"], a["severidad"], a["titulo"], a["estado"],
              a["veredicto"], a["severidad_final"]] for a in data["alerts_table"][:50]],
        )
        doc.add_heading("5. Auditoría reciente", level=1)
        _docx_table(
            doc, ["Fecha/hora", "Usuario", "Módulo", "Acción", "IP"],
            [[a["fecha"], a["usuario"], a["modulo"], a["accion"], a["ip"]] for a in data["audit_table"][:30]],
        )
    else:
        doc.add_heading("4. Incidentes", level=1)
        _docx_table(
            doc, ["ID", "Título", "Severidad", "Estado", "Apertura", "Ticket"],
            [[str(i["id"]), i["titulo"], i["severidad"], i["estado"], i["abertura"], i["ticket"]]
             for i in data["incidents_table"]] or [["-", "-", "-", "-", "-", "-"]],
        )
        doc.add_heading("5. Cumplimiento (ISO 27001 / NIST CSF)", level=1)
        _docx_table(
            doc, ["Control", "Estado", "Evidencia"],
            [[c["control"], c["estado"], c["evidencia"]] for c in data["compliance"]],
        )
        doc.add_heading("6. Recomendaciones de gestión", level=1)
        for r in [
            "Sostener el triaje automatizado 24/7 para mantener el MTTT en minutos.",
            "Revisar semanalmente la tasa de falsos positivos y afinar reglas del SIEM.",
            "Capacitar al equipo en el procedimiento de respuesta a incidentes (A.5.24).",
            "Auditar trimestralmente la bitácora y los roles RBAC.",
        ]:
            doc.add_paragraph(r, style="List Bullet")

    import io

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _docx_table(doc, header: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Light Grid Accent 1"
    for idx, name in enumerate(header):
        table.rows[0].cells[idx].text = str(name)
    for row_data in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row_data[: len(header)]):
            cells[idx].text = str(value)


# -------------------------------------------------------------------------- XLSX
def render_xlsx(data: dict) -> bytes:
    wb = Workbook()

    ws = wb.active
    ws.title = "KPIs"
    ws.append([data["meta"]["title"]])
    ws.append([f"Generado: {data['meta']['generated_at']} · Período: {data['meta']['period_days']} días"])
    ws.append([])
    ws.append(["Indicador", "Valor"])
    for cell in ws[4]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for k, v in data["kpis"].items():
        ws.append([k, v])
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 24

    ws_alerts = wb.create_sheet("Alertas")
    cols = ["ID", "Fecha", "Fuente", "Severidad", "Título", "Origen", "Estado", "Veredicto", "Sev. final", "Confianza", "Motor"]
    ws_alerts.append(cols)
    for cell in ws_alerts[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for a in data["alerts_table"]:
        ws_alerts.append([_col_map(c, a) for c in cols])
    widths = [6, 17, 10, 11, 45, 15, 11, 18, 11, 10, 10]
    for i, w in enumerate(widths, start=1):
        ws_alerts.column_dimensions[ws_alerts.cell(row=1, column=i).column_letter].width = w

    ws_src = wb.create_sheet("Top_Origenes")
    ws_src.append(["IP origen", "Alertas"])
    for cell in ws_src[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for s in data["top_sources"]:
        ws_src.append([s["ip"], s["count"]])

    ws_inc = wb.create_sheet("Incidentes")
    ws_inc.append(["ID", "Título", "Severidad", "Estado", "Apertura", "Cierre", "Ticket"])
    for cell in ws_inc[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for i in data["incidents_table"]:
        ws_inc.append([i["id"], i["titulo"], i["severidad"], i["estado"], i["abertura"], i["cierre"], i["ticket"]])

    ws_audit = wb.create_sheet("Auditoria")
    ws_audit.append(["Fecha/hora", "Usuario", "Módulo", "Acción", "IP"])
    for cell in ws_audit[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for a in data["audit_table"]:
        ws_audit.append([a["fecha"], a["usuario"], a["modulo"], a["accion"], a["ip"]])

    if data["meta"]["type"] == "management":
        ws_comp = wb.create_sheet("Cumplimiento")
        ws_comp.append(["Control", "Estado", "Evidencia"])
        for cell in ws_comp[1]:
            cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        for c in data["compliance"]:
            ws_comp.append([c["control"], c["estado"], c["evidencia"]])
        ws_comp.column_dimensions["A"].width = 45
        ws_comp.column_dimensions["B"].width = 14
        ws_comp.column_dimensions["C"].width = 70
        for row in ws_comp.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")

    for sheet in wb.worksheets:
        sheet.freeze_panes = "A2"
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=isinstance(cell.value, str) and len(str(cell.value)) > 40)

    import io

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _col_map(col: str, row: dict) -> str:
    mapping = {
        "ID": "id", "Fecha": "fecha", "Fuente": "fuente", "Severidad": "severidad",
        "Título": "titulo", "Origen": "origen", "Estado": "estado", "Veredicto": "veredicto",
        "Sev. final": "severidad_final", "Confianza": "confianza", "Motor": "motor",
    }
    return row[mapping[col]]


async def record_export(db: AsyncSession, *, user_id: int | None, username: str | None, report_type: str, fmt: str, rows: int) -> None:
    db.add(
        ReportExport(
            user_id=user_id, username=username, report_type=report_type, fmt=fmt, rows_count=rows
        )
    )
    await db.commit()
