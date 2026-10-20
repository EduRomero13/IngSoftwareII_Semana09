from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import alerts, audit, auth, health, incidents, metrics, reports, triage, users
from app.config import settings
from app.core.audit import audit_request, resolve_module
from app.core.security import decode_token
from app.database import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import init_db

    await init_db()
    yield


app = FastAPI(
    title="SOC-Lite API",
    description="Triaje automático de alertas SOC para PYMES (NIST CSF DE.AE / ISO 27001 A.8.15, A.5.24)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefijos auditados por los propios routers (con detalle de dominio)
ROUTER_AUDITED_PREFIXES = ("/api/v1/auth", "/api/v1/triage")
# Módulos donde el GET solo genera ruido/recursión en la bitácora
SKIP_GET_MODULES = {"audit", "metrics"}


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Bitácora de auditoría: registra entrada/salida por módulo con usuario, fecha, hora y acción."""
    response: Response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/v1"):
        module = resolve_module(path)
        skip = any(path.startswith(p) for p in ROUTER_AUDITED_PREFIXES) or module == "health"
        if request.method == "GET" and module in SKIP_GET_MODULES:
            skip = True
        if not skip:
            user_id, username = _identity_from_request(request)
            if username is None and "/webhook" in path:
                username = "webhook"
            try:
                async with SessionLocal() as session:
                    await audit_request(
                        session,
                        request,
                        user_id=user_id,
                        username=username,
                        status_code=response.status_code,
                    )
            except Exception:  # noqa: BLE001 - la auditoría nunca debe romper la respuesta
                pass
    return response


def _identity_from_request(request: Request) -> tuple[int | None, str | None]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None
    try:
        payload = decode_token(auth_header.removeprefix("Bearer ").strip())
        uid = payload.get("uid")
        return (int(uid) if uid is not None else None), payload.get("sub")
    except Exception:  # noqa: BLE001
        return None, None


API_ROUTER = "/api/v1"
app.include_router(health.router, prefix=API_ROUTER)
app.include_router(auth.router, prefix=API_ROUTER)
app.include_router(users.router, prefix=API_ROUTER)
app.include_router(alerts.router, prefix=API_ROUTER)
app.include_router(triage.router, prefix=API_ROUTER)
app.include_router(incidents.router, prefix=API_ROUTER)
app.include_router(metrics.router, prefix=API_ROUTER)
app.include_router(reports.router, prefix=API_ROUTER)
app.include_router(audit.router, prefix=API_ROUTER)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/api/v1/health",
        "version": "1.0.0",
    }
