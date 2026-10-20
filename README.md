# SOC-Lite · Triaje automático de alertas SOC para PYMES

Aplicación de ciberseguridad que reduce la fatiga de alertas (70–90 % falsos positivos)
combinando **orquestación low-code (n8n)**, **enriquecimiento contextual** y
**razonamiento LLM local (LangChain + Ollama)** con dashboard, reportes, RBAC y bitácora de auditoría.

- **NIST CSF:** DE.AE (análisis de anomalías)
- **ISO 27001:** A.8.15 (registro de eventos), A.5.24 (respuesta a incidentes), A.5.15 (control de acceso)

---

## Stack

| Capa | Tecnología | Justificación |
|---|---|---|
| Orquestación | n8n (workflow exportable) | dominio del equipo, integraciones, reintentos |
| Backend / API | Python 3.11+ · FastAPI · Uvicorn | una sola API para dashboard y microservicio de triaje |
| ORM / migraciones | SQLAlchemy 2 async · Alembic · asyncpg | migraciones versionadas, JSONB para payloads |
| Agentes LLM | LangChain 1.x (`create_agent`) + ChatOllama | tools, memoria, `response_format` estructurado |
| LLM local | Ollama (`llama3.1` / `mistral`) | las alertas **nunca** salen hacia APIs externas de LLM |
| Base de datos | PostgreSQL 16+ | requisito obligatorio |
| Auth / RBAC | JWT (python-jose) + bcrypt + permisos por recurso | ligero para PYME |
| Reportes | ReportLab (PDF) · python-docx (Word) · openpyxl (Excel) | sin ofimática externa |
| Frontend | React 18 · Vite · Tailwind CSS v4 · Recharts | SPA de dashboard |
| Despliegue | Docker Compose | 1 servidor para PYME |
| Tests | pytest + pytest-asyncio + httpx | 11 tests de integración |

## Arquitectura (3 capas)

```
                        ┌─────────────────────────────────────────────┐
  Wazuh / OPNsense ───► │  n8n (workflow soc_lite_triage.json)        │
     webhook            │  1 Webhook → 2 IF → 3 PG( pending )        │
                        │  4 HTTP ─────────────┐                      │
                        │  6 Switch → 7 PG(triaje) → 8 Slack          │
                        │         └──────────→ 9 osTicket → 10 audit  │
                        └────────────┬───────────▲────────────────────┘
                                     ▼           │ POST /api/v1/audit
┌────────────────────────────────────────────────────────────────────┐
│  FASTAPI (backend/app)                                             │
│  · Presentación: API REST /api/v1/* (auth, alerts, triage,         │
│    metrics, reports, incidents, users, audit, health)              │
│  · Lógica: RBAC (JWT+permisos), middleware de auditoría,           │
│    servicios de triaje (LangChain+Ollama con fallback),            │
│    métricas y generadores de reportes PDF/Word/Excel               │
│  · Datos: SQLAlchemy async ───────────────► PostgreSQL 16          │
│      alerts · enrichment_data · triage_results · incidents ·       │
│      users · roles · audit_log · report_exports                    │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ REST + JWT
┌──────────────────────────▼─────────────────────────────────────────┐
│  FRONTEND React+Vite (frontend/)                                   │
│  Login · Dashboard(KPIs, MTTT, FP%, top orígenes) · Alertas ·      │
│  Detalle de alerta (resumen LLM + acciones) · Incidentes ·         │
│  Usuarios · Auditoría · Reportes                                   │
└────────────────────────────────────────────────────────────────────┘
```

Detalle completo: [`docs/architecture.md`](docs/architecture.md) · Datasets públicos: [`docs/datasets.md`](docs/datasets.md)

## Puesta en marcha (desarrollo local)

Requisitos: Python 3.11+, Node 20+, PostgreSQL en ejecución, Ollama (opcional).

```bash
# 1) Base de datos
psql -U postgres -c "CREATE ROLE soclite LOGIN PASSWORD 'soclite' CREATEDB;"
psql -U postgres -c "CREATE DATABASE soclite OWNER soclite;"

# 2) Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
alembic upgrade head                 # crea el esquema
python -m app.seed --reset           # roles, usuarios, alertas, bitácora (idempotente)
uvicorn app.main:app --port 8000

# 3) Frontend (otra terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxy /api → :8000)

# 4) LLM local (opcional; sin él actúa el fallback heurístico)
ollama pull llama3.1 && ollama serve
```

### Docker Compose

```bash
docker compose up -d postgres api          # API + BD (siembra automática al arrancar)
docker compose --profile frontend up -d    # + nginx sirviendo el SPA en :5173
docker compose --profile n8n up -d         # + n8n en :5678
docker compose --profile llm up -d         # + ollama en :11434
```

## Credenciales semilla

| Usuario | Contraseña | Rol | Permisos |
|---|---|---|---|
| `admin` | `Admin123!` | admin | todo (usuarios, auditoría global, reportes) |
| `analyst` | `Analyst123!` | analyst | alertas, triaje, incidentes, reportes, auditoría |
| `viewer` | `Viewer123!` | viewer | solo lectura de dashboard/alertas/reportes (auditoría propia) |

## API principal (`/api/v1`)

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| POST | `/auth/login/json` | público | login → JWT + permisos |
| POST | `/auth/logout` | sesión | OUT en bitácora |
| GET | `/alerts` | alerts.read | listado con filtros/severidad/estado/paginación |
| GET | `/alerts/{id}` | alerts.read | detalle + triaje + enriquecimiento + payload |
| POST | `/alerts` | alerts.write | creación manual |
| POST | `/alerts/webhook` | `X-Webhook-Token` | ingesta desde Wazuh/OPNsense/n8n (dedup) |
| POST | `/triage/{id}` | triage.execute | ejecuta agente LangChain (LLM u Ollama) |
| GET | `/metrics/overview` | metrics.read | KPIs: MTTT, %FP, severidades, top orígenes, tendencia |
| GET | `/reports?type=&format=` | reports.export | PDF / Word / Excel (operacional o de gestión) |
| GET | `/audit` | audit.read | bitácora (admin: global · resto: propio) |
| POST | `/audit` | audit.write | entrada manual (nodo 10 de n8n) |
| CRUD | `/users`, `/incidents` | users.manage / incidents.* | RBAC e incidentes |
| GET | `/health` | público | estado API + BD + Ollama |

## Workflow n8n

Importar [`n8n/workflows/soc_lite_triage.json`](n8n/workflows/soc_lite_triage.json) en n8n
(*Workflows → Import from File*) y configurar:

1. Credencial **PostgreSQL** (`postgres:5432`, db/user/pass `soclite`).
2. Credencial **Header Auth** con `Authorization: Bearer <JWT>` (obtenerlo con `POST /api/v1/auth/login/json` como `admin`).
3. Variables de entorno: `SOC_API_URL`, `SOC_API_TOKEN`, `OSTICKET_URL`, `OSTICKET_API_KEY`.
4. Credencial Slack y canal `#soc-alertas` (notificación solo de severidad alta).

Los 10 nodos del flujo están documentados con notas (sticky notes) dentro del propio workflow.

## Tests

```bash
cd backend && python -m pytest -q     # requiere PostgreSQL (crea/dropea la BD soclite_test)
cd frontend && npm run build          # verificación de build del SPA
```

## Estructura del proyecto

```
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── alembic/                  # migraciones (initial schema)
│   ├── app/
│   │   ├── main.py               # FastAPI + middleware de auditoría
│   │   ├── models.py · schemas.py · database.py · config.py
│   │   ├── core/                 # security(JWT) · rbac · audit · timeutils
│   │   ├── api/v1/               # auth users alerts triage incidents metrics reports audit health
│   │   ├── services/             # triage(LangChain) · enrichment · metrics · reports
│   │   └── seed/__main__.py      # python -m app.seed [--reset]
│   └── tests/                    # 11 tests de integración
├── frontend/                     # React + Vite + Tailwind + Recharts
├── n8n/workflows/soc_lite_triage.json
└── docs/                         # architecture.md · datasets.md
```
