"""Configuración común de pytest: entorno determinista para todas las suites."""

import os

# Debe ejecutarse antes de importar app.config / app.database.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://soclite:soclite@localhost:5432/soclite_test"
)
os.environ.setdefault("ENRICHMENT_MOCK", "true")
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("TRIAGE_FALLBACK_ENABLED", "true")
