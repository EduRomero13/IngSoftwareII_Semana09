-- Base de datos ficticia para la demo de carga (SOC-Lite).
-- Requiere el esquema y los usuarios creados por `python -m app.seed`.
-- Uso: psql "$DATABASE_URL" -f db/load_data.sql   (DATABASE_URL en formato postgres://...)
-- Genera 100.000 alertas en 90 días + triajes, enriquecimiento, auditoría e incidentes.
-- Determinista: mismos datos en cada ejecución.

\set ON_ERROR_STOP on

BEGIN;

TRUNCATE TABLE triage_results, enrichment_data, incidents, audit_log, report_exports, alerts
  RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------- alertas (100k)
INSERT INTO alerts (source, rule_id, severity, title, description, src_ip, dst_ip,
                    raw_payload, dedup_hash, status, created_at)
SELECT
  (ARRAY['wazuh', 'opnsense', 'suricata'])[1 + (i % 3)],
  (ARRAY['5710', '31103', '2502', '5763', '40111', '80790'])[1 + (i % 6)],
  CASE WHEN i % 10 < 2 THEN 'alta' WHEN i % 10 < 7 THEN 'media' ELSE 'baja' END,
  (t.titles)[1 + (i % 12)],
  (t.descriptions)[1 + (i % 12)],
  CASE WHEN i % 7 = 0
       THEN '10.' || (i % 250) || '.' || ((i / 250) % 250) || '.' || (1 + i % 200)
       ELSE (ARRAY['185.220.101.', '45.155.205.', '193.32.162.', '91.240.118.', '103.75.201.'])[1 + (i % 5)]
            || (1 + i % 250)
  END,
  '10.0.' || (i % 50) || '.' || (1 + i % 200),
  jsonb_build_object('rule', 'demo-' || (i % 50), 'level', 3 + (i % 13), 'agent', 'soc-demo-' || (i % 60)),
  md5('soc-lite-load-' || i),
  CASE WHEN i % 100 < 12 THEN 'pending' ELSE 'triaged' END,
  now() - make_interval(days => (i % 90), secs => (i * 37) % 86400)
FROM generate_series(1, 100000) AS i
CROSS JOIN (
  SELECT
    ARRAY[
      'Multiple failed SSH logins',
      'Port scan detected from external host',
      'Malware C2 beacon to known bad IP',
      'SQL injection attempt blocked',
      'Brute force on RDP',
      'Suspicious PowerShell execution',
      'Web shell upload attempt',
      'DNS query to malicious domain',
      'Lateral movement via SMB',
      'TLS certificate with weak cipher',
      'Outbound connection to Tor exit node',
      'Repeated 404 errors on admin panel'
    ] AS titles,
    ARRAY[
      'Se detectaron 25 intentos fallidos de autenticación SSH en menos de 5 minutos.',
      'Escaneo de puertos TCP SYN desde una IP externa hacia el perímetro.',
      'Conexión periódica cada 60 s hacia una IP asociada a infraestructura C2.',
      'Petición HTTP con patrones UNION SELECT sobre el portal público.',
      'Múltiples intentos de inicio de sesión RDP con credenciales inválidas.',
      'Proceso PowerShell con codificación Base64 y descarga remota.',
      'Archivo PHP sospechoso creado en el directorio de subidas del servidor web.',
      'Resolución DNS hacia un dominio reportado en listas de amenazas.',
      'Autenticaciones SMB entre estaciones del mismo segmento fuera de horario.',
      'Negociación TLS con cifrados obsoletos desde un servidor interno.',
      'Conexión saliente hacia un nodo de salida de Tor documentado.',
      'Ráfaga de errores 404 sobre /wp-admin desde una única IP.'
    ] AS descriptions
) AS t;

-- ---------------------------------------------------------------- triajes (~53k)
INSERT INTO triage_results (alert_id, llm_verdict, predicted_severity, confidence, summary,
                            recommended_actions, model_name, engine, tokens_used, latency_ms, created_at)
SELECT
  a.id,
  CASE WHEN a.severity = 'alta' THEN 'verdadero_positivo'
       WHEN a.id % 10 < 4 THEN 'falso_positivo'
       ELSE 'sospechoso' END,
  a.severity,
  round((0.55 + (a.id % 40) / 100.0)::numeric, 2),
  'Triaje sintético de la alerta ' || a.id || ': ' || a.title,
  '["Revisar el origen en el firewall", "Correlacionar con eventos de las últimas 24 h"]'::jsonb,
  'heuristic', 'heuristic', NULL,
  20 + (a.id % 180),
  a.created_at + make_interval(secs => 30 + (a.id % 120))
FROM alerts a
WHERE a.status = 'triaged' AND a.id % 10 < 6;

-- ---------------------------------------------------------------- enriquecimiento (~240k)
INSERT INTO enrichment_data (alert_id, tool, key, value, queried_at)
SELECT
  a.id,
  tool.name,
  COALESCE(a.src_ip, ''),
  jsonb_build_object('tool', tool.name, 'ip', a.src_ip, 'score', (a.id % 100), 'malicious', a.id % 3 = 0),
  a.created_at + interval '5 seconds'
FROM alerts a
CROSS JOIN (VALUES ('virustotal'), ('abuseipdb'), ('geoip')) AS tool(name)
WHERE a.id % 5 < 4;

-- ---------------------------------------------------------------- auditoría (300k)
INSERT INTO audit_log (user_id, username, module, action, method, path, details, ip, status_code, created_at)
SELECT
  1 + (i % (SELECT count(*) FROM users)),
  (ARRAY['admin', 'analyst', 'viewer'])[1 + (i % 3)],
  (ARRAY['alerts', 'metrics', 'incidents', 'triage', 'audit'])[1 + (i % 5)],
  (ARRAY['READ', 'CREATE', 'UPDATE', 'EXECUTE', 'EXPORT'])[1 + (i % 5)],
  (ARRAY['GET', 'POST', 'PATCH'])[1 + (i % 3)],
  (ARRAY['/api/v1/alerts', '/api/v1/metrics/overview', '/api/v1/incidents',
         '/api/v1/triage/1', '/api/v1/reports'])[1 + (i % 5)],
  jsonb_build_object('demo', true, 'seq', i),
  '127.0.0.1',
  (ARRAY[200, 200, 200, 201, 403])[1 + (i % 5)],
  now() - make_interval(days => (i % 90), secs => (i * 53) % 86400)
FROM generate_series(1, 300000) AS i;

-- ---------------------------------------------------------------- incidentes (5k)
INSERT INTO incidents (alert_id, title, severity, status, assignee_id, ticket_id, notes,
                       opened_at, closed_at)
SELECT
  a.id,
  'Incidente: ' || a.title,
  a.severity,
  CASE WHEN a.id % 5 = 0 THEN 'closed' ELSE 'open' END,
  NULL,
  'TCK-' || a.id,
  'Escalado desde el triaje automático (datos ficticios).',
  a.created_at + interval '10 minutes',
  CASE WHEN a.id % 5 = 0 THEN a.created_at + interval '2 days' END
FROM (
  SELECT id, title, severity, created_at
  FROM alerts
  WHERE severity = 'alta'
  ORDER BY created_at DESC
  LIMIT 5000
) AS a;

ANALYZE;

COMMIT;

SELECT 'alerts' AS tabla, count(*) FROM alerts
UNION ALL SELECT 'triage_results', count(*) FROM triage_results
UNION ALL SELECT 'enrichment_data', count(*) FROM enrichment_data
UNION ALL SELECT 'audit_log', count(*) FROM audit_log
UNION ALL SELECT 'incidents', count(*) FROM incidents;
