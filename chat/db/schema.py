from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from .models import UserStatus


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    status: UserStatus
    registered_at: date

    class Config:
        from_attributes = True


class GroupBase(BaseModel):
    name: str


class GroupCreate(GroupBase):
    pass


class GroupRead(GroupBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GroupMemberRead(BaseModel):
    id: int
    user_id: int
    group_id: int
    joined_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    text: str


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: int
    group_id: int
    author_id: int
    sent_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None
