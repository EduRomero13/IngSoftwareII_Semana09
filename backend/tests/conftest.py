import os

import httpx
import pytest

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://soclite:soclite@localhost:5432/soclite_test"
)
os.environ.setdefault("ENRICHMENT_MOCK", "true")
os.environ.setdefault("LLM_PROVIDER", "ollama")

from app.core.security import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402

ROLES = ["admin", "analyst", "viewer"]
USERS = [
    ("admin", "Admin123!", "admin"),
    ("analyst", "Analyst123!", "analyst"),
    ("viewer", "Viewer123!", "viewer"),
]


async def _create_test_db() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    admin_engine = create_async_engine(
        "postgresql+asyncpg://soclite:soclite@localhost:5432/postgres",
        isolation_level="AUTOCOMMIT",
    )
    async with admin_engine.connect() as conn:
        exists = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'soclite_test'")
        )
        if not exists.first():
            await conn.execute(text("CREATE DATABASE soclite_test"))
    await admin_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        role_ids = {}
        for name in ROLES:
            role = Role(name=name, description=name)
            db.add(role)
            await db.flush()
            role_ids[name] = role.id
        for username, password, role in USERS:
            db.add(
                User(
                    username=username,
                    email=f"{username}@test.local",
                    full_name=username.title(),
                    password_hash=hash_password(password),
                    role_id=role_ids[role],
                )
            )
        await db.commit()


async def _drop_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    await _create_test_db()
    yield
    await _drop_all()


@pytest.fixture(scope="session")
async def client():
    # ASGITransport no ejecuta lifespan; el esquema lo crea el fixture setup_db.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client


def login_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
