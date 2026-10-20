from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.core.rbac import CurrentUser, require_permission
from app.database import get_db
from app.models import Role, User
from app.schemas import Paginated, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _to_out(user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.role_name = user.role.name if user.role else None
    return out


async def _get_role(db: AsyncSession, name: str) -> Role:
    role = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if not role:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Rol inexistente: {name}")
    return role


@router.get("", response_model=Paginated)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("users.read")),
):
    total = (await db.execute(select(func_count()))).scalar() or 0
    rows = (
        await db.execute(
            select(User)
            .options(selectinload(User.role))
            .order_by(User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return Paginated(total=total, page=page, page_size=page_size, items=[_to_out(u) for u in rows])


def func_count():
    from sqlalchemy import func

    return func.count(User.id)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("users.manage")),
):
    exists = (
        await db.execute(
            select(User).where((User.username == body.username) | (User.email == body.email))
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username o email ya existen")
    role = await _get_role(db, body.role_name)
    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role_id=role.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(user, attribute_names=["role"])
    return _to_out(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("users.read")),
):
    user = (
        await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return _to_out(user)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("users.manage")),
):
    user = (
        await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    if body.email is not None:
        user.email = body.email
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)
    if body.role_name is not None:
        role = await _get_role(db, body.role_name)
        user.role_id = role.id
    await db.commit()
    await db.refresh(user)
    return _to_out(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_permission("users.manage")),
):
    if user_id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes eliminar tu propio usuario")
    user = (
        await db.execute(select(User).options(selectinload(User.role)).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    await db.delete(user)
    await db.commit()
