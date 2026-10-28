# n8n · Orquestación SOC-Lite

Workflow: [`workflows/soc_lite_triage.json`](workflows/soc_lite_triage.json)

Versión validada: **n8n 2.45.5** (`n8nio/n8n:2.45.5`). Versiones de nodo usadas:
Webhook `2.2`, Code `2`, IF `2.4`, HTTP Request `4.5`, Switch `3.5`, Slack `2.7`, NoOp `1`,
Sticky Note `1`.

## Arquitectura del flujo

n8n **no escribe en PostgreSQL**: solo orquesta llamadas a FastAPI. FastAPI es la única
ruta de escritura (RBAC, deduplicación SHA-256, triaje persistido y auditoría).

```
Wazuh / OPNsense
  └─ POST /webhook/soc-alert  (header auth)
       1. Webhook
       2. Code       normaliza el payload a AlertCreate
       3. IF         descarta alertas inválidas
       4. HTTP       POST /api/v1/alerts/webhook   (X-Webhook-Token)
       5. HTTP       POST /api/v1/auth/login/json  (usuario de servicio)
       6. HTTP       POST /api/v1/triage/{id}      (Bearer JWT)
       7. Switch     predicted_severity: alta | media | baja
       8. Slack      solo alta
       9/10. HTTP    osTicket (alta y media)
       11. NoOp      fin de la rama baja
```

Los nodos HTTP tienen reintentos (`retryOnFail`, `maxTries`, `waitBetweenTries`) en la raíz
del nodo, como exige n8n.

## Requisitos

1. **Backend arriba** con `WEBHOOK_TOKEN` definido.
2. **Usuario de servicio** creado por el seed (rol `analyst`):
   ```bash
   # .env
   N8N_SERVICE_USER=n8n
   N8N_SERVICE_PASSWORD=<password-fuerte>
   # luego
   python -m app.seed
   ```
   Sin `N8N_SERVICE_PASSWORD` el seed no crea el usuario y el nodo 5 fallará. Si la base ya
   estaba sembrada, el seed agrega solo el usuario de servicio (no reinicia datos).
3. **Clave de cifrado de n8n** en `.env`:
   ```bash
   openssl rand -hex 32   # N8N_ENCRYPTION_KEY
   ```

## Importar el workflow

```bash
# con Docker (el compose monta ./n8n/workflows en /workflows:ro)
docker compose --profile n8n run --rm n8n import:workflow --input=/workflows/soc_lite_triage.json
docker compose --profile n8n up -d n8n

# con instalación local de n8n 2.45.5
n8n import:workflow --input=n8n/workflows/soc_lite_triage.json
```

El workflow tiene `id` fijo (`SocLiteTriage001`): reimportar actualiza, no duplica.

> El compose no publica `5678` en el host (regla Dokploy/Traefik). Para abrir la UI en local
> sin editar el compose: `docker compose --profile n8n run --rm -p 5678:5678 n8n`.

## Credenciales a crear en la UI

| Nodo | Credencial | Configuración |
|---|---|---|
| 1. Webhook | Header Auth | nombre `X-Webhook-Token`, valor = `WEBHOOK_TOKEN` del backend |
| 8. Slack | Slack API | token del bot con permiso `chat:write` |

El resto usa variables de entorno del contenedor (`SOC_API_URL`, `SOC_WEBHOOK_TOKEN`,
`SOC_API_USER`, `SOC_API_PASSWORD`, `SLACK_CHANNEL`, `OSTICKET_URL`, `OSTICKET_API_KEY`).
No se versiona ningún secreto.

## Variables de entorno

| Variable | Uso |
|---|---|
| `SOC_API_URL` | base de FastAPI dentro de la red (`http://api:8000`) |
| `SOC_WEBHOOK_TOKEN` | header de ingesta; debe coincidir con el backend |
| `SOC_API_USER` / `SOC_API_PASSWORD` | login del usuario de servicio |
| `SLACK_CHANNEL` | canal de notificación de severidad alta |
| `OSTICKET_URL` / `OSTICKET_API_KEY` | endpoint y clave del helpdesk |
| `N8N_WEBHOOK_URL` | URL pública del webhook detrás de Traefik |
| `N8N_PROXY_HOPS` | `1` cuando hay un proxy delante |
| `N8N_ENCRYPTION_KEY` | cifrado de credenciales de n8n |

## Prueba manual

```bash
curl -X POST http://<n8n>/webhook/soc-alert \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: <WEBHOOK_TOKEN>" \
  -d '{"rule":{"id":"100101","level":12,"description":"Fuerza bruta SSH"},
       "data":{"srcip":"193.32.162.229","dstip":"192.168.1.60"},
       "full_log":"Failed password for root"}'
```

Esperado: `202` del webhook, alerta `pending` en la API, triaje persistido, Slack solo si la
severidad predicha es `alta` y ticket en osTicket para `alta`/`media`.

## Despliegue (Dokploy / Traefik)

El servicio no publica puertos al host. En Dokploy:

1. Container Port: `5678`.
2. Dominio HTTPS con `sslip.io` + Let's Encrypt.
3. `N8N_HOST`, `N8N_PROTOCOL=https` y `N8N_WEBHOOK_URL` con el dominio público.

## Pruebas del contrato

El JSON se valida sin ejecutar n8n:

```bash
cd backend && pytest -m unit tests/unit/test_n8n_workflow.py -q
```
