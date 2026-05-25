from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from chat.db.database import SessionLocal
from chat.db.models import User, Group, GroupMember
from chat.db.schema import GroupCreate, GroupRead, GroupMemberRead
from chat.api.auth import get_current_user   # ← исправлено

router = APIRouter(tags=["Groups"], prefix="/api/groups")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=GroupRead)
async def create_group(
    group: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать группу"""
    new_group = Group(name=group.name, owner_id=current_user.id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    # Добавляем создателя как участника
    member = GroupMember(user_id=current_user.id, group_id=new_group.id)
    db.add(member)
    db.commit()

    return new_group


@router.get("/", response_model=List[GroupRead])
async def list_user_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Список групп пользователя"""
    groups = (
        db.query(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .filter(GroupMember.user_id == current_user.id)
        .all()
    )
    return groups


@router.get("/{group_id}", response_model=GroupRead)
async def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о группе"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first():
        raise HTTPException(status_code=403, detail="Not a member")

    return group


@router.put("/{group_id}", response_model=GroupRead)
async def update_group(
    group_id: int,
    group_update: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Переименовать группу (только owner)"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can rename")

    group.name = group_update.name
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить группу (только owner)"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete")

    db.delete(group)
    db.commit()
    return {"detail": "Group deleted successfully"}


@router.post("/{group_id}/members", response_model=List[GroupMemberRead])
async def add_members(
    group_id: int,
    user_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Добавить участников в группу (только owner)"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can add members")

    added = []
    for uid in user_ids:
        if db.query(User).filter(User.id == uid).first() is None:
            continue
        if db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == uid
        ).first():
            continue

        member = GroupMember(user_id=uid, group_id=group_id)
        db.add(member)
        added.append(member)

    db.commit()
    return added