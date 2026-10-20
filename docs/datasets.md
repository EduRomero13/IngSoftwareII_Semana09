# Datasets públicos recomendados para SOC-Lite

## 1. Para generar/sembrar alertas realistas

| Dataset | Fuente | Uso en la app |
|---|---|---|
| **Wazuh ruleset + example alerts** | [github.com/wazuh/wazuh-ruleset](https://github.com/wazuh/wazuh-ruleset) · docs.wazuh.com | Plantillas de reglas, niveles (0–16) y mensajes; alimenta el modelo `severity` y las plantillas del seed (`app/seed/__main__.py`) |
| **CICIDS2017** | [www.unb.ca/cic/datasets/ids-2017.html](https://www.unb.ca/cic/datasets/ids-2017.html) | Tráfico con ataques etiquetados (DDoS, port scan, brute force, botnet, infiltración) → simular alertas Wazuh con IPs de atacante/víctima reales |
| **CSE-CIC-IDS2018** | [www.unb.ca/cic/datasets/ids-2018.html](https://www.unb.ca/cic/datasets/ids-2018.html) | Versión ampliada de CICIDS2017, útil para volumen de alertas y pruebas de rendimiento |
| **Malware-Traffic-Analysis.net** | [malware-traffic-analysis.net](https://malware-traffic-analysis.net) | PCAPs + alertas Snort/Suricata de campañas reales → payloads crudos realistas en `raw_payload` |
| **AWID (Airodump-WIDS)** | [github.com/icalab/awid](https://github.com/icalab/awid) | Tráfico WiFi con ataques etiquetados → alertas de red inalámbrica |
| **UNSW-NB15** | [research.unsw.edu.au/projects/nbs-dataset](https://www.unb.ca/cic/datasets/nsl.html) | Características de flujo con 9 familias de ataque → escenarios de triaje |

### Cómo usarlos
- Extraer tickets de CICIDS2017/UNSW con la IP de atacante → mapear a `alerts.src_ip`, la víctima a `dst_ip`, y la familia de ataque a `severity`/`title`.
- Insertar vía `POST /api/v1/alerts/webhook` (con `X-Webhook-Token`) o con un script de carga masiva.
- Guardar el dataset crudo como referencia histórica para validar la tasa de falsos positivos real vs. la detectada por el triaje.

## 2. Para enriquecimiento (tools del agente)

| Fuente | Uso | Notas |
|---|---|---|
| **VirusTotal API v3** (free tier) | Detecciones por IP/hash | 4 req/min; sin key → modo simulado (`ENRICHMENT_MOCK=true`) |
| **AbuseIPDB API** (free tier) | Score de abuso por IP | 1.000 req/día en plan gratuito |
| **MaxMind GeoLite2** | GeoIP local (país/ciudad/ASN) | Registro gratuito; licencia CC-BY-SA — evita llamadas externas |
| **Firehol blocklists** ([firehol.org](https://firehol.org/#blocklists)) | Listas de IPs maliciosas (spam, proxies, tor, botnet) | Se puede cargar a una tabla `threat_intel` para reemplazar el mock |
| **Emerging Threats compromised IPs** | IPs comprometidas conocidas | Igual que arriba |
| **CINS Army list** ([cinsscore.com](https://cinsscore.com/list.php?score=33)) | IPs con scoring malicioso | Compatible con `known_threat_intel` |
| **John's BGP Abuse Contact DB** | Contacto de abuse del ASN | Para escalamiento hacia el ISP |

### Intel local ya incluida (mock determinista)
`backend/app/services/enrichment.py` incluye `KNOWN_MALICIOUS_IPS`, `KNOWN_BENIGN_IPS` y `GEO_DB`
(IPs de Tor/botnet/C2 documentadas públicamente + DNS públicos), usados por el modo simulado
y por la tool `threat_intel_local`. Amplíalos cargando blocklists reales.

## 3. Para cumplimiento y reportes

| Fuente | Uso |
|---|---|
| **NISTIR 7621 Rev. 2** (CSF subcategories) | Mapeo DE.AE-1…DE.AE-6 → sección de cumplimiento del reporte de gestión |
| **ISO/IEC 27001:2022 Anex A** (A.5.15, A.5.24, A.8.15, A.8.16) | Controles citados en `services/reports.py::build_report_data` |
| **MITRE ATT&CK** (enterprise) | Etiquetar reglas/plantillas de alerta con técnicas para enriquecer `raw_payload.technique` |
| **FIRST CSIRT services framework** | Plantilla de métricas operacionales (MTTT, MTTA, backlog) |

## 4. Datasets para pruebas de carga

- **MAWI Working Group** ([mawi.wide.ad.jp](https://mawi.wide.ad.jp/mawi/)) — tráfico anonimizado diario, útil para bombardear el webhook y validar el filtrado de duplicados (nodo 2) y la dedup de `alerts.dedup_hash`.
