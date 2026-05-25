from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from chat.db.database import SessionLocal
from chat.db.models import User
from chat.db.schema import UserRead
from chat.api.auth import get_current_user   # ← исправлено

router = APIRouter(tags=["Users"], prefix="/api/users")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Получить профиль текущего пользователя"""
    return current_user


@router.get("/search", response_model=List[UserRead])
async def search_users(
    q: str = Query(..., min_length=1, description="Поиск по username или email"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск пользователей"""
    users = (
        db.query(User)
        .filter(
            (User.username.ilike(f"%{q}%")) |
            (User.email.ilike(f"%{q}%"))
        )
        .limit(limit)
        .all()
    )
    return users


@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить пользователя по ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user