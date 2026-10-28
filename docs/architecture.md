# Arquitectura del sistema SOC-Lite

## 1. Componentes e interacciones

| Componente | Responsabilidad | Tecnología |
|---|---|---|
| **Ingesta** | Recibe alertas crudas de Wazuh/OPNsense vía webhook | n8n (nodo Webhook) o `POST /api/v1/alerts/webhook` directo |
| **Orquestación** | Normaliza y valida, ingiere vía API, dispara el triaje, enruta por severidad y notifica | n8n (`n8n/workflows/soc_lite_triage.json`) |
| **API / lógica de negocio** | REST del dashboard + microservicio de triaje | FastAPI (`backend/app`) |
| **Triaje** | Enriquecimiento + clasificación + resumen + acciones | LangChain `create_agent` con tools y `response_format` (Pydantic) |
| **LLM local** | Inferencia sin exfiltrar datos de alertas | Ollama (`llama3.1`/`mistral`), fallback heurístico si no responde |
| **Datos** | Persistencia y auditoría | PostgreSQL 16 (SQLAlchemy async + Alembic) |
| **Presentación** | Dashboard, gestión y reportes | React + Vite + Tailwind + Recharts |

### Flujo completo

```
Wazuh/OPNsense ──webhook──► n8n ──► Code (normaliza) ──► IF (alerta válida)
                                                                  │
                                                                  ▼
                                        POST /api/v1/alerts/webhook (token, dedup SHA-256)
                                                                  │
                                                                  ▼
                                    POST /api/v1/auth/login/json (usuario de servicio)
                                                                  │
                                                                  ▼
                                    POST /api/v1/triage/{id}  (FastAPI)
                                                                  │
                                                  ┌───────────────┴────────────────┐
                                                  ▼                                ▼
                                       enrich_ip() → enrichment_data      LangChain agent (tools:
                                       (VT/AbuseIPDB/GeoIP/mock)           virustotal, abuseipdb,
                                                  │                        geoip, threat_intel_local)
                                                  │                        + ChatOllama (Ollama local)
                                                  │                                │
                                                  │                    si falla → _heuristic()
                                                  └───────────────┬────────────────┘
                                                                  ▼
                                                  triage_results (veredicto, severidad, confianza,
                                                                  resumen, acciones, motor, latencia)
                                                  + alert.status='triaged' + audit_log (EXECUTE)
                                                                  │
                                                                  ▼
                                                  Switch por severidad
                                                  ├─ alta   → Slack + ticket osTicket
                                                  ├─ media  → ticket osTicket
                                                  └─ baja   → fin sin notificación
                                                                  │
                                                                  ▼
                                                  Dashboard (React) lee /metrics/overview y /alerts
```

n8n no escribe en PostgreSQL: toda escritura pasa por FastAPI (RBAC, deduplicación y auditoría).

## 2. Capas

### Capa de presentación (frontend/)
- SPA con router protegido; cada ruta exige un permiso (`ProtectedRoute permission=`).
- Páginas: Login, Dashboard, Alertas, Detalle de alerta, Incidentes, Usuarios, Auditoría, Reportes.
- Cliente axios con interceptor JWT y redirección a `/login` ante 401.
- Gráficas Recharts: línea de tendencia (total/alta, 7 días), barras por severidad, dona de veredictos, top orígenes con barras relativas.

### Capa de lógica de negocio (backend/app)
- **Auth/RBAC:** JWT con `sub/uid/role`; permisos resueltos desde `ROLE_PERMISSIONS` (`core/rbac.py`); dependencia `require_permission("recurso.accion")`.
- **Auditoría:** middleware HTTP que registra toda petición `/api/v1` (usuario desde el JWT, módulo derivado del path, acción derivada del método, fecha/hora, IP, código). Excepciones: `auth` (lo registra el router con IN/OUT y usuario real), `triage` (registra detalle de dominio: alert_id, veredicto, motor, latencia), `health`, y `GET` de `audit`/`metrics` (evita ruido/recursión).
- **Triaje:** `services/triage.py` → enriquecimiento persistente, agente LangChain con 4 tools y salida estructurada; si Ollama no responde en el timeout → `_heuristic()` determinista (nunca bloquea la operación).
- **Métricas:** `services/metrics.py` → MTTT (promedio `triage.created_at - alert.created_at` en segundos), tasa de FP, distribuciones, top orígenes, tendencia diaria.
- **Reportes:** `services/reports.py` → `build_report_data()` + renderers PDF/Word/Excel; registro en `report_exports` + acción `EXPORT` en bitácora.

### Capa de datos (PostgreSQL)
Ver modelo en la sección 4. JSONB para `raw_payload`, `value` (enrichment), `recommended_actions` y `details` (auditoría).

## 3. Flujo de nodos n8n (8 pasos + fin de rama)

Versión validada: **n8n 2.45.5**. Versiones de nodo: Webhook `2.2`, Code `2`, IF `2.4`,
HTTP Request `4.5`, Switch `3.5`, Slack `2.7`, NoOp `1`.

| # | Nodo | Función | Entrada → Salida |
|---|---|---|---|
| 1 | Webhook | Recibe alerta Wazuh/OPNsense (`POST /webhook/soc-alert`) | JSON crudo → items |
| 2 | Code | Valida `X-Webhook-Token` y normaliza a `AlertCreate` (severidad numérica o texto, IPs, título, `raw_payload`) | JSON crudo → alerta normalizada |
| 3 | IF | Descarta alertas sin severidad válida o sin IP | alerta → booleano (false → fin) |
| 4 | HTTP Request | `POST /api/v1/alerts/webhook` con `X-Webhook-Token`; dedup SHA-256 en backend | alerta → `{id, status, duplicates_total}` |
| 5 | HTTP Request | `POST /api/v1/auth/login/json` del usuario de servicio (rol analyst) | credenciales de entorno → JWT |
| 6 | HTTP Request | `POST /api/v1/triage/{id}` con Bearer; enriquece, clasifica y **persiste** triaje + auditoría | JWT + id → JSON de triaje |
| 7 | Switch | Enruta por `predicted_severity` (alta/media/baja) | triaje → 3 ramas |
| 8 | Slack | Notifica **solo severidad alta** (nodo deshabilitado por defecto hasta configurar `slackApi`) | resumen → mensaje |
| 9 | HTTP Request | Crea ticket en osTicket (alta) | triaje → `ticket_id` |
| 10 | HTTP Request | Crea ticket en osTicket (media) | triaje → `ticket_id` |
| 11 | NoOp | Fin de la rama baja (sin notificación) | — |

Workflow exportable: `n8n/workflows/soc_lite_triage.json`; instrucciones en
[`n8n/README.md`](../n8n/README.md). No se versionan credenciales.

## 4. Modelo de datos (PostgreSQL)

```
roles 1───n users 1───n incidents(assignee)        alerts 1───1 triage_results
                                      │              │ 1───n enrichment_data
                                      │              │ 1───n incidents
users (user_id) ──┐                  audit_log       report_exports
                  └──────────────────┘
```

| Tabla | Campos clave | Índices / restricciones |
|---|---|---|
| `roles` | id, name (admin/analyst/viewer), description | unique(name) |
| `users` | id, username, email, password_hash (bcrypt), full_name, is_active, role_id FK | unique(username), unique(email) |
| `alerts` | id, source, rule_id, severity, title, description, src_ip, dst_ip, raw_payload JSONB, dedup_hash, status, created_at | **unique(dedup_hash)**, idx(created_at) |
| `enrichment_data` | id, alert_id FK, tool, key, value JSONB, queried_at | idx(alert_id, tool) |
| `triage_results` | id, alert_id FK unique, llm_verdict, predicted_severity, confidence, summary, recommended_actions JSONB, model_name, engine(llm/heuristic), tokens_used, latency_ms, created_at | idx(created_at) |
| `incidents` | id, alert_id FK, title, severity, status, assignee_id FK, ticket_id, notes, opened_at, closed_at | idx por status implícito en consultas |
| `audit_log` | id, user_id, username, module, action, method, path, details JSONB, ip, status_code, created_at | idx(created_at), idx(module) |
| `report_exports` | id, user_id, username, report_type, fmt, rows_count, generated_at | — |

**Estados de alerta:** `pending → triaged → escalated → closed | discarded`.

**Acciones de bitácora:** `IN` (entrada al sistema), `OUT` (salida), `CREATE`, `UPDATE`, `DELETE`, `READ`, `EXPORT`, `EXECUTE`.

### Permisos RBAC

| Permiso | admin | analyst | viewer |
|---|:--:|:--:|:--:|
| alerts.read / metrics.read / incidents.read | ✓ | ✓ | ✓ |
| alerts.write / triage.execute / incidents.write | ✓ | ✓ | – |
| reports.export | ✓ | ✓ | ✓ |
| audit.read | ✓ (global) | ✓ (global) | ✓ (solo propios) |
| audit.write, users.read, users.manage | ✓ | – | – |

## 5. Datos semilla (`python -m app.seed`)

- 3 roles + 3 usuarios (admin/analyst/viewer) + usuario de servicio `n8n` (solo si `N8N_SERVICE_PASSWORD` está definida).
- 60 alertas en 7 días con 20 plantillas estilo Wazuh/OPNsense (IPs maliciosas conocidas + IPs internas/benignas), ~80 % de las antiguas pre-triadas → ~12 pendientes para probar el flujo.
- 180 filas de `enrichment_data` (VT/AbuseIPDB/GeoIP en modo simulado determinista).
- 48 `triage_results` (motor heurístico) con veredictos mixtos → tasa de FP realista.
- 3 incidentes (2 abiertos, 1 cerrado con ticket osTicket ficticio).
- 180 eventos de auditoría distribuidos en los módulos.

Idempotente (`--reset` recrea el esquema).
