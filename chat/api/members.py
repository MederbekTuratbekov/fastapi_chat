from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from chat.db.database import SessionLocal
from chat.db.models import User, Group, GroupMember
from chat.db.schema import GroupMemberRead
from chat.api.auth import get_current_user   # ← исправлено

router = APIRouter(tags=["Group Members"], prefix="/api/groups")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{group_id}/members", response_model=List[dict])
async def get_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список участников группы"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first():
        raise HTTPException(status_code=403, detail="Not a member of this group")

    members = (
        db.query(GroupMember, User)
        .join(User, User.id == GroupMember.user_id)
        .filter(GroupMember.group_id == group_id)
        .all()
    )

    result = []
    for member, user in members:
        result.append({
            "id": member.id,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None
        })

    return result


@router.delete("/{group_id}/members/{user_id}")
async def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить участника из группы (только владелец)"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only group owner can remove members")

    if user_id == group.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove group owner")

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="User is not a member")

    db.delete(member)
    db.commit()

    return {"detail": "Member removed successfully"}