from typing import Dict, Set, List, Optional, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from chat.db.database import SessionLocal
from chat.db.models import User, Group, GroupMember, Message
from chat.config import SECRET_KEY, ALGORITHM
from chat.api.groups import (
    db_get_group,
    db_is_member,
    db_group_member_ids,
    db_create_group,
    db_delete_group,
    db_rename_group,
    db_add_members,
    db_get_members_with_users,
)

chat_router = APIRouter(tags=["Chat WS"])


def _extract_token(websocket: WebSocket, token_q: Optional[str]) -> Optional[str]:
    if token_q:
        return token_q
    auth = websocket.headers.get("authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_user_from_token(db: Session, token: str) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise JWTError("no sub")
    except JWTError:
        raise ValueError("Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise ValueError("User not found")
    return user


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        conns = list(self._connections.get(user_id, []))
        dead: List[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast_to_users(self, user_ids: List[int], payload: dict) -> None:
        for uid in set(user_ids):
            await self.send_to_user(uid, payload)


manager = ConnectionManager()


def group_to_dict(g: Group) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "owner_id": g.owner_id,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


def msg_to_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "group_id": m.group_id,
        "user_id": m.author_id,
        "text": m.text,
        "sent_at": m.sent_at.isoformat() if m.sent_at else None,
        "edited_at": m.edited_at.isoformat() if m.edited_at else None,
    }


@chat_router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    db = SessionLocal()
    user: Optional[User] = None

    try:
        tok = _extract_token(websocket, token)
        if not tok:
            await websocket.accept()
            await websocket.send_json({"event": "error", "detail": "Missing token"})
            await websocket.close(code=1008)
            return

        try:
            user = get_user_from_token(db, tok)
        except ValueError:
            await websocket.accept()
            await websocket.send_json({"event": "error", "detail": "Invalid token"})
            await websocket.close(code=1008)
            return

        await manager.connect(user.id, websocket)
        await websocket.send_json({
            "event": "connected",
            "user_id": user.id,
            "username": user.username,
        })

        while True:
            data: Dict[str, Any] = await websocket.receive_json()
            action = data.get("action") or data.get("actions")

            if not action:
                await websocket.send_json({"event": "error", "detail": "action is required"})
                continue

            # === CREATE GROUP ===
            if action == "create_group":
                name = (data.get("name") or "").strip()
                if not name:
                    await websocket.send_json({"event": "error", "action": action, "detail": "name is required"})
                    continue
                g = db_create_group(db, name, user.id)
                await websocket.send_json({"event": "group_created", "group": group_to_dict(g)})
                continue

            # === LIST GROUPS ===
            if action == "list_groups":
                groups = (
                    db.query(Group)
                    .join(GroupMember, GroupMember.group_id == Group.id)
                    .filter(GroupMember.user_id == user.id)
                    .order_by(Group.id.desc())
                    .all()
                )
                await websocket.send_json({
                    "event": "groups",
                    "items": [group_to_dict(g) for g in groups],
                })
                continue

            # === RENAME GROUP ===
            if action == "rename_group":
                group_id = data.get("group_id")
                new_name = (data.get("name") or "").strip()
                if not group_id or not new_name:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group_id and name required"})
                    continue
                g = db_get_group(db, int(group_id))
                if not g:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group not found"})
                    continue
                if g.owner_id != user.id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "only owner can rename"})
                    continue
                g = db_rename_group(db, g, new_name)
                members = db_group_member_ids(db, g.id)
                await manager.broadcast_to_users(members, {"event": "group_renamed", "group": group_to_dict(g)})
                continue

            # === DELETE GROUP ===
            if action == "delete_group":
                group_id = data.get("group_id")
                if not group_id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group_id required"})
                    continue
                g = db_get_group(db, int(group_id))
                if not g:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group not found"})
                    continue
                if g.owner_id != user.id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "only owner can delete"})
                    continue
                members = db_group_member_ids(db, g.id)
                db_delete_group(db, g)
                await manager.broadcast_to_users(members, {"event": "group_deleted", "group_id": int(group_id)})
                continue

            # === GROUP DETAILS ===
            if action == "group_details":
                group_id = data.get("group_id")
                if not group_id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group_id required"})
                    continue
                g = db_get_group(db, int(group_id))
                if not g:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group not found"})
                    continue
                if not db_is_member(db, g.id, user.id):
                    await websocket.send_json({"event": "error", "action": action, "detail": "not a member"})
                    continue
                members_data = db_get_members_with_users(db, g.id)
                await websocket.send_json({
                    "event": "group_details",
                    "group": group_to_dict(g),
                    "members": [
                        {
                            "user_id": u.id,
                            "username": u.username,
                            "joined_at": gm.joined_at.isoformat() if gm.joined_at else None,
                        }
                        for gm, u in members_data
                    ],
                })
                continue

            # === ADD MEMBERS ===
            if action == "add_members":
                group_id = data.get("group_id")
                user_ids = data.get("user_ids") or []
                if not group_id or not isinstance(user_ids, list) or not user_ids:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group_id and user_ids required"})
                    continue
                g = db_get_group(db, int(group_id))
                if not g:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group not found"})
                    continue
                if g.owner_id != user.id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "only owner can add members"})
                    continue
                added = db_add_members(db, g.id, user_ids)
                members = db_group_member_ids(db, g.id)
                await manager.broadcast_to_users(members, {
                    "event": "members_added",
                    "group_id": g.id,
                    "added_user_ids": added,
                })
                continue

            # === SEND MESSAGE ===
            if action == "send_message":
                group_id = data.get("group_id")
                text = (data.get("text") or "").strip()
                if not group_id or not text:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group_id and text required"})
                    continue
                group_id = int(group_id)
                if not db_is_member(db, group_id, user.id):
                    await websocket.send_json({"event": "error", "action": action, "detail": "not a member"})
                    continue
                m = Message(group_id=group_id, author_id=user.id, text=text)
                db.add(m)
                db.commit()
                db.refresh(m)
                members = db_group_member_ids(db, group_id)
                await manager.broadcast_to_users(members, {"event": "message", "message": msg_to_dict(m)})
                continue

            # === DELETE MESSAGE ===
            if action == "delete_message":
                message_id = data.get("message_id")
                if not message_id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "message_id required"})
                    continue
                m = db.query(Message).filter(Message.id == int(message_id)).first()
                if not m:
                    await websocket.send_json({"event": "error", "action": action, "detail": "message not found"})
                    continue
                if m.author_id != user.id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "only author can delete"})
                    continue
                members = db_group_member_ids(db, m.group_id)
                group_id_for_broadcast = m.group_id
                db.delete(m)
                db.commit()
                await manager.broadcast_to_users(members, {
                    "event": "message_deleted",
                    "message_id": message_id,
                    "group_id": group_id_for_broadcast,
                })
                continue


            # === EDIT MESSAGE ===
            if action == "edit_message":
                message_id = data.get("message_id")
                new_text = (data.get("text") or "").strip()
                if not message_id or not new_text:
                    await websocket.send_json({"event": "error", "action": action, "detail": "message_id and text required"})
                    continue
                m = db.query(Message).filter(Message.id == int(message_id)).first()
                if not m:
                    await websocket.send_json({"event": "error", "action": action, "detail": "message not found"})
                    continue
                if m.author_id != user.id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "only author can edit"})
                    continue
                m.text = new_text
                m.edited_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(m)
                members = db_group_member_ids(db, m.group_id)
                await manager.broadcast_to_users(members, {
                    "event": "message_edited",
                    "message": msg_to_dict(m),
                })
                continue

            # === FETCH MESSAGES ===
            if action == "fetch_messages":
                group_id = data.get("group_id")
                limit = int(data.get("limit") or 50)
                before_id = data.get("before_id")
                if not group_id:
                    await websocket.send_json({"event": "error", "action": action, "detail": "group_id required"})
                    continue
                group_id = int(group_id)
                if not db_is_member(db, group_id, user.id):
                    await websocket.send_json({"event": "error", "action": action, "detail": "not a member"})
                    continue
                q = db.query(Message).filter(Message.group_id == group_id)
                if before_id:
                    q = q.filter(Message.id < int(before_id))
                msgs = q.order_by(Message.id.desc()).limit(min(limit, 200)).all()
                msgs = list(reversed(msgs))
                await websocket.send_json({
                    "event": "messages",
                    "group_id": group_id,
                    "items": [msg_to_dict(x) for x in msgs],
                })
                continue

            await websocket.send_json({"event": "error", "detail": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        pass
    finally:
        if user is not None:
            manager.disconnect(user.id, websocket)
        db.close()
