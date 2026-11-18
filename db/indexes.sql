-- Índices que faltan en el esquema base; se crean entre la corrida A y la B
-- para demostrar la mejora de las consultas del dashboard.
-- Uso: psql "$DATABASE_URL" -f db/indexes.sql

CREATE INDEX IF NOT EXISTS ix_alerts_status ON alerts (status);
CREATE INDEX IF NOT EXISTS ix_alerts_severity_created ON alerts (severity, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_created_at ON audit_log (created_at);

ANALYZE;
