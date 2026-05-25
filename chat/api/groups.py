from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from chat.db.database import get_db
from chat.db.models import User, Group, GroupMember
from chat.db.schema import GroupCreate, GroupRead, GroupMemberRead
from chat.api.auth import get_current_user

router = APIRouter(tags=["Groups"], prefix="/api/groups")


# ====================== CRUD FUNCTIONS ======================

def db_get_group(db: Session, group_id: int) -> Optional[Group]:
    return db.query(Group).filter(Group.id == group_id).first()


def db_is_member(db: Session, group_id: int, user_id: int) -> bool:
    return db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first() is not None


def db_group_member_ids(db: Session, group_id: int) -> List[int]:
    rows = db.query(GroupMember.user_id).filter(
        GroupMember.group_id == group_id
    ).all()
    return [r[0] for r in rows]


def db_create_group(db: Session, name: str, owner_id: int) -> Group:
    g = Group(name=name, owner_id=owner_id)
    db.add(g)
    db.commit()
    db.refresh(g)
    db.add(GroupMember(group_id=g.id, user_id=owner_id))
    db.commit()
    return g


def db_delete_group(db: Session, group: Group) -> None:
    db.delete(group)
    db.commit()


def db_rename_group(db: Session, group: Group, new_name: str) -> Group:
    group.name = new_name
    db.commit()
    db.refresh(group)
    return group


def db_add_members(db: Session, group_id: int, user_ids: List[int]) -> List[int]:
    added = []
    for uid in user_ids:
        if not isinstance(uid, int):
            continue
        if db.query(User).filter(User.id == uid).first() is None:
            continue
        if db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == uid
        ).first():
            continue
        db.add(GroupMember(group_id=group_id, user_id=uid))
        added.append(uid)
    db.commit()
    return added


def db_get_members_with_users(db: Session, group_id: int):
    return (
        db.query(GroupMember, User)
        .join(User, User.id == GroupMember.user_id)
        .filter(GroupMember.group_id == group_id)
        .all()
    )


# ====================== ROUTES ======================

@router.post("/", response_model=GroupRead)
async def create_group(
    group: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db_create_group(db, group.name, current_user.id)


@router.get("/", response_model=List[GroupRead])
async def list_user_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .filter(GroupMember.user_id == current_user.id)
        .all()
    )


@router.get("/{group_id}", response_model=GroupRead)
async def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    group = db_get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if not db_is_member(db, group_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member")
    return group


@router.put("/{group_id}", response_model=GroupRead)
async def update_group(
    group_id: int,
    group_update: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    group = db_get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can rename")
    return db_rename_group(db, group, group_update.name)


@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    group = db_get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete")
    db_delete_group(db, group)
    return {"detail": "Group deleted successfully"}


@router.post("/{group_id}/members", response_model=List[GroupMemberRead])
async def add_members(
    group_id: int,
    user_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    group = db_get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can add members")
    db_add_members(db, group_id, user_ids)
    return db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
