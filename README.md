# SOC-Lite · Triaje automático de alertas SOC para PYMES

Aplicación de ciberseguridad que reduce la fatiga de alertas (70–90 % falsos positivos)
combinando **orquestación low-code (n8n)**, **enriquecimiento contextual** y
**razonamiento LLM local (LangChain + Ollama)** con dashboard, reportes, RBAC y bitácora de auditoría.

- **NIST CSF:** DE.AE (análisis de anomalías)
- **ISO 27001:** A.8.15 (registro de eventos), A.5.24 (respuesta a incidentes), A.5.15 (control de acceso)

---

## 🚀 Inicio rápido (otra PC · lo mínimo)

Necesitas **solo 3 cosas**: **Python 3.11+**, **Node.js 20+** y **PostgreSQL (14+)** corriendo.
Nada más es obligatorio (ver tabla de abajo).

```bash
# 0) Clonar y configurar entorno
git clone <url-del-repo> && cd SEMANA09
cp .env.example .env

# 1) Base de datos (una sola vez)
psql -U postgres <<'SQL'
CREATE ROLE soclite LOGIN PASSWORD 'soclite' CREATEDB;
CREATE DATABASE soclite OWNER soclite;
SQL

# 2) Backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
python -m app.seed                   # crea el esquema + datos demo (idempotente)
uvicorn app.main:app --port 8000     # API en http://127.0.0.1:8000
```

```bash
# 3) Frontend (otra terminal, desde la raíz del repo)
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

**Verificación en 30 segundos**

1. `curl http://127.0.0.1:8000/api/v1/health` → `{"api":"ok","database":"ok",...}`
2. Abre `http://localhost:5173` y entra con **`admin` / `Admin123!`** (o `analyst` / `Analyst123!`).
3. Verás el dashboard con 60 alertas demo, ~12 pendientes de triar y bitácora con eventos.

> **Windows:** los mismos pasos, pero activa el venv con `.venv\Scripts\activate` y usa
> `py -3 -m venv .venv`. PostgreSQL: instalador oficial o `docker run -e POSTGRES_PASSWORD=... -p 5432:5432 postgres:16`.
> Si no puedes crear la BD con tu usuario, ejecuta el `CREATE ROLE/DATABASE` con un superusuario.

> **Migraciones:** `python -m app.seed` crea el esquema automáticamente. Como mantenedor puedes
> usar Alembic en su lugar: `alembic upgrade head` (historial en `backend/alembic/versions/`).

### ❌ Lo que NO necesitas para que funcione

Todo lo siguiente es **opcional**. Sin ello el sistema arranca y opera completo
(triaje, dashboard, reportes, auditoría, RBAC):

| Componente | Sin él… | Si lo añades después |
|---|---|---|
| **Ollama + `llama3.1`** | El triaje usa el **fallback heurístico** determinista (motor `heuristic`) | Instala [ollama.com](https://ollama.com) → `ollama pull llama3.1` → el triaje usa LLM real (`engine: llm`). Config: `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| **API key VirusTotal** | Enriquecimiento en **modo simulado** determinista (`ENRICHMENT_MOCK=true`) | `VIRUSTOTAL_API_KEY=...` en `.env` y `ENRICHMENT_MOCK=false` |
| **API key AbuseIPDB** | Igual que arriba (respuestas simuladas con IPs de inteligencia local) | `ABUSEIPDB_API_KEY=...` en `.env` |
| **n8n** | El flujo low-code; la API ya recibe alertas por webhook y tría por endpoint/ UI | `docker compose --profile n8n up -d` e importar `n8n/workflows/soc_lite_triage.json` (ver [`n8n/README.md`](n8n/README.md)) |
| **Slack / osTicket / Redmine** | Notificaciones y tickets (solo del workflow n8n) | Credenciales dentro de n8n |
| **DeepSeek / OpenAI u otros LLM en la nube** | Nada: **no están integrados** (por diseño, las alertas no salen hacia APIs externas de LLM; solo Ollama local) | — |
| **Docker** | Usas la instalación manual de arriba | Alternativa completa: `docker compose up -d postgres api` (+ perfiles `frontend`, `n8n`, `llm`) |
| **Wazuh / OPNsense** | Las 60 alertas demo del seed + webhook vacío bastan para probar | Apunta el webhook de Wazuh/OPNsense/n8n a `POST /api/v1/alerts/webhook` con cabecera `X-Webhook-Token` |

### 🔑 Variables de entorno mínimas (`.env`)

Solo estas 3 importan para arrancar; **el resto tiene defaults funcionales** (ver `.env.example`):

| Variable | Valor por defecto | Para qué |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://soclite:soclite@localhost:5432/soclite` | conexión a PostgreSQL |
| `JWT_SECRET` | `change-me-in-production` | firma de tokens — **cámbiala en cualquier despliegue real** |
| `WEBHOOK_TOKEN` | `soclite-webhook-token` | autenticación de `POST /api/v1/alerts/webhook` |

### 🧪 Credenciales semilla

| Usuario | Contraseña | Rol | Permisos |
|---|---|---|---|
| `admin` | `Admin123!` | admin | todo (usuarios, auditoría global, reportes) |
| `analyst` | `Analyst123!` | analyst | alertas, triaje, incidentes, reportes, auditoría |
| `viewer` | `Viewer123!` | viewer | solo lectura de dashboard/alertas/reportes (auditoría propia) |

### 🐳 Alternativa: Docker Compose

```bash
docker compose up -d postgres api          # API + BD (siembra automática al arrancar)
docker compose --profile frontend up -d    # + nginx sirviendo el SPA en :5173
docker compose --profile n8n up -d         # + n8n en :5678 (opcional)
docker compose --profile llm up -d         # + ollama en :11434 (opcional)
```

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
| Tests | pytest + pytest-asyncio + httpx | unitarios sin servicios + integración |

## Arquitectura (3 capas)

```
                        ┌─────────────────────────────────────────────┐
  Wazuh / OPNsense ───► │  n8n (soc_lite_triage.json, 2.45.5)         │
     webhook            │  1 Webhook → 2 Code normaliza → 3 IF        │
                        │  4 POST /alerts/webhook (X-Webhook-Token)   │
                        │  5 login servicio → 6 POST /triage/{id}     │
                        │  7 Switch → 8 Slack (alta) → 9/10 osTicket  │
                        │         └─ baja → 11 fin                    │
                        └────────────┬────────────────────────────────┘
                                     ▼ REST (token webhook + JWT)
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

## Opcionales: LLM real y enriquecimiento real

**Ollama (LLM local, recomendado para privacidad total):**

```bash
# instalar desde https://ollama.com (Linux/macOS/Windows) y luego:
ollama pull llama3.1
ollama serve                            # default: http://localhost:11434
```
El backend lo detecta solo (`GET /api/v1/health` muestra `llm: ok`); si no responde,
el triaje cae al fallback heurístico sin romper el flujo. Config en `.env`:
`OLLAMA_BASE_URL`, `OLLAMA_MODEL=llama3.1`, `LLM_TIMEOUT_SECONDS`, `TRIAGE_FALLBACK_ENABLED=true`.

**Enriquecimiento real (opcional):** crear keys gratuitas en [VirusTotal](https://www.virustotal.com/gui/my-apikey)
y [AbuseIPDB](https://www.abuseipdb.com/account/api), ponerlas en `.env` y fijar `ENRICHMENT_MOCK=false`.
Con `ENRICHMENT_MOCK=true` (default) se usan respuestas simuladas deterministas +
una lista local de inteligencia (Tor/botnet/C2 conocidas).

## API principal (`/api/v1`)

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| POST | `/auth/login/json` | público | login → JWT + permisos |
| POST | `/auth/logout` | sesión | OUT en bitácora |
| GET | `/alerts` | alerts.read | listado con filtros/severidad/estado/paginación |
| GET | `/alerts/{id}` | alerts.read | detalle + triaje + enriquecimiento + payload |
| POST | `/alerts` | alerts.write | creación manual |
| POST | `/alerts/webhook` | `X-Webhook-Token` | ingesta desde Wazuh/OPNsense/n8n (dedup) |
| POST | `/triage/{id}` | triage.execute | ejecuta agente LangChain (Ollama o fallback) |
| GET | `/metrics/overview` | metrics.read | KPIs: MTTT, %FP, severidades, top orígenes, tendencia |
| GET | `/reports?type=&format=` | reports.export | PDF / Word / Excel (operacional o de gestión) |
| GET | `/audit` | audit.read | bitácora (admin/analyst: global · viewer: propio) |
| POST | `/audit` | audit.write | entrada manual (nodo 10 de n8n) |
| CRUD | `/users`, `/incidents` | users.manage / incidents.* | RBAC e incidentes |
| GET | `/health` | público | estado API + BD + Ollama |

## Workflow n8n (opcional)

n8n **orquesta** y FastAPI es la única ruta de escritura (RBAC, dedup SHA-256, triaje
persistido y auditoría). Versión validada: **n8n 2.45.5**.

1. Definir en `.env`: `N8N_SERVICE_USER`, `N8N_SERVICE_PASSWORD`, `N8N_ENCRYPTION_KEY`
   (`openssl rand -hex 32`), `WEBHOOK_TOKEN`, `SLACK_CHANNEL`, `OSTICKET_URL`, `OSTICKET_API_KEY`.
2. Ejecutar `python -m app.seed` para crear el usuario de servicio (rol `analyst`).
3. Importar [`n8n/workflows/soc_lite_triage.json`](n8n/workflows/soc_lite_triage.json):
   ```bash
   docker compose --profile n8n run --rm n8n import:workflow --input=/workflows/soc_lite_triage.json
   docker compose --profile n8n up -d n8n
   ```
4. En la UI de n8n crear solo dos credenciales: **Header Auth** del webhook
   (`X-Webhook-Token`, mismo valor que `WEBHOOK_TOKEN`) y **Slack API**.
5. Flujo: Webhook → Code (normaliza) → IF → `POST /alerts/webhook` → login de servicio →
   `POST /triage/{id}` → Switch por severidad → Slack (solo alta) → osTicket (alta/media).

Detalle, variables y prueba manual: [`n8n/README.md`](n8n/README.md).

## Tests

```bash
cd backend
python -m pytest -q              # unitarios: sin PostgreSQL ni red (< 15 s)
python -m pytest -m integration  # integración: requiere PostgreSQL (crea soclite_test)
cd ../frontend && npm run build  # verificación de build del SPA
```

La suite unitaria incluye el contrato del workflow de n8n
(`tests/unit/test_n8n_workflow.py`): versiones de nodo, conexiones, ramas de severidad,
ausencia de secretos y de escrituras directas a PostgreSQL.

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
│   └── tests/
│       ├── unit/                 # unitarios sin servicios externos
│       └── integration/          # requieren PostgreSQL
├── frontend/                     # React + Vite + Tailwind + Recharts
├── n8n/
│   ├── workflows/soc_lite_triage.json
│   └── README.md                 # importación, credenciales y variables
└── docs/                         # architecture.md · datasets.md
```
