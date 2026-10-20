from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import write_audit
from app.core.rbac import get_current_user, permissions_for_role
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login (application/x-www-form-urlencoded, compatible OAuth2 del swagger)."""
    return await _do_login(form.username, form.password, db)


@router.post("/login/json", response_model=Token)
async def login_json(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login vía JSON para el frontend."""
    return await _do_login(body.username, body.password, db)


async def _do_login(username: str, password: str, db: AsyncSession) -> Token:
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        await write_audit(
            db,
            module="login",
            action="IN",
            username=username,
            details={"result": "failed"},
            commit=True,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario inactivo")
    token = create_access_token(
        username=user.username, user_id=user.id, role=user.role.name
    )
    await write_audit(
        db,
        module="login",
        action="IN",
        user_id=user.id,
        username=user.username,
        details={"role": user.role.name},
        commit=True,
    )
    return Token(
        access_token=token,
        username=user.username,
        role=user.role.name,
        permissions=sorted(permissions_for_role(user.role.name)),
    )


@router.post("/logout")
async def logout(current = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await write_audit(
        db,
        module="login",
        action="OUT",
        user_id=current.id,
        username=current.username,
        commit=True,
    )
    return {"detail": "sesión cerrada"}
