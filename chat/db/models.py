from .database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Enum, Date, ForeignKey, DateTime, Text
from enum import Enum as PyEnum
from datetime import date, datetime, timezone
from typing import List, Optional


class UserStatus(str, PyEnum):
    admin = 'admin'
    simple = 'simple'


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.simple)
    registered_at: Mapped[date] = mapped_column(Date, default=date.today)

    owned_groups: Mapped[List['Group']] = relationship(back_populates='owner', cascade='all, delete-orphan')
    memberships: Mapped[List['GroupMember']] = relationship(back_populates='user', cascade='all, delete-orphan')
    messages: Mapped[List['Message']] = relationship(back_populates='author', cascade='all, delete-orphan')


class Group(Base):
    __tablename__ = 'group'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False)
    owner: Mapped['User'] = relationship(back_populates='owned_groups')
    members: Mapped[List['GroupMember']] = relationship(back_populates='group', cascade='all, delete-orphan')
    messages: Mapped[List['Message']] = relationship(back_populates='group', cascade='all, delete-orphan')


class GroupMember(Base):
    __tablename__ = 'group_member'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False)
    user: Mapped['User'] = relationship(back_populates='memberships')

    group_id: Mapped[int] = mapped_column(ForeignKey('group.id'), nullable=False)
    group: Mapped['Group'] = relationship(back_populates='members')


class Message(Base):
    __tablename__ = 'message'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)  # <-- добавить

    author_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False)
    author: Mapped['User'] = relationship(back_populates='messages')

    group_id: Mapped[int] = mapped_column(ForeignKey('group.id'), nullable=False)
    group: Mapped['Group'] = relationship(back_populates='messages')
