import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    status = {"api": "ok", "database": "unknown", "llm": "unknown"}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        status["database"] = f"error: {exc.__class__.__name__}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                status["llm"] = f"ok ({settings.ollama_model})" if any(
                    settings.ollama_model in (m or "") for m in models
                ) else f"ok (modelos: {models})"
            else:
                status["llm"] = "unreachable"
    except Exception:
        status["llm"] = "unreachable (fallback heurístico activo)"
    return status
