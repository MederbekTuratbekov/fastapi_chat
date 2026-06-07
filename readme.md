# Group Chat Platform API

> A real-time group messaging backend with WebSocket events and JWT auth —
> giving teams a self-hosted communication layer without third-party
> platform dependency.

[![Python](https://img.shields.io/badge/Python-3.11-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-async-teal)]()
[![WebSocket](https://img.shields.io/badge/WebSocket-realtime-orange)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green)]()

---

## Business Problem

Teams and communities that rely on third-party messengers lose control
over their data, customization, and delivery guarantees. A self-hosted
group chat API with real-time delivery and structured group management
enables businesses to embed messaging directly into their product without
recurring SaaS costs.

---

## Demo

**Login and get token:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -F "username=ali" -F "password=pass123"
```
```json
{"access_token": "<jwt>", "token_type": "bearer", "refresh_token": "<jwt>"}
```

**Connect and send a message (WebSocket):**
```
ws://localhost:8000/ws/chat?token=<access_token>

→ send: {"action": "send_message", "group_id": 1, "text": "Hello team!"}
← recv: {"event": "message", "message": {"id": 42, "group_id": 1,
          "user_id": 3, "text": "Hello team!", "sent_at": "2024-06-07T10:00:00"}}
```

---

## What I Built

- **WebSocket chat hub** — single `/ws/chat` endpoint handles 10+ action
  types: send/delete/fetch messages, create/rename/delete groups,
  add members, group details, list groups
- **Real-time broadcast** — `ConnectionManager` broadcasts events to all
  online group members; dead connections cleaned up automatically
- **JWT auth** — register, login, token refresh via REST; token decoded
  on WS connect for stateless identity
- **OAuth2 social login** — GitHub and Google via authlib
- **Group management REST API** — full CRUD at `/api/groups/` with
  owner-only write operations
- **Member management** — add/remove members with membership guard on
  all group operations
- **User search** — `/api/users/search?q=` with ilike on username/email
- **Cursor-based message history** — `fetch_messages` with `before_id`
  and configurable `limit` (max 200)

---

## Tech Stack

| Category    | Technology                                  |
|-------------|---------------------------------------------|
| Language    | Python 3.11                                 |
| Framework   | FastAPI, Uvicorn (ASGI)                     |
| Real-time   | WebSocket (native FastAPI)                  |
| ORM         | SQLAlchemy 2.x (Mapped / mapped_column)     |
| Validation  | Pydantic v2                                 |
| Auth        | python-jose (JWT), passlib (bcrypt)         |
| OAuth2      | authlib (GitHub, Google)                    |
| Database    | PostgreSQL                                  |
| Config      | python-dotenv                               |

---

## Architecture

```
Client (WS) ──→ /ws/chat ──→ ConnectionManager
                                  ↕  broadcast
Client (HTTP) ─→ REST routers → SQLAlchemy ORM → PostgreSQL
                  (auth, groups, members, users, social_auth)
```

Single WebSocket endpoint handles all real-time actions via
`action`-based dispatch (internal event bus pattern). REST routes
handle CRUD for the same entities — both layers share the same DB
session and ORM functions extracted into `groups.py` helpers for
reuse across WS and HTTP handlers.

---

## Key Technical Decisions

**1. Single WebSocket endpoint with action dispatch**
All real-time operations go through one `/ws/chat` connection rather
than per-resource channels — clients maintain one persistent connection,
reducing handshake overhead from N connections to 1 per user.

**2. `ConnectionManager` with per-user socket sets**
Each user can have multiple simultaneous connections (tabs/devices)
stored as `Dict[int, Set[WebSocket]]` — broadcast reaches all sessions,
dead sockets pruned on send failure with zero impact on other connections.

**3. Shared DB helper functions across WS and REST**
`db_create_group`, `db_add_members`, etc. are defined once in
`groups.py` and imported by both the WebSocket handler and HTTP router
— eliminates duplicate query logic and ensures consistent behaviour
regardless of transport.

---

## How to Run

```bash
git clone https://github.com/your-username/group-chat-api
cd group-chat-api
cp .env.example .env  # add SECRET_KEY, DATABASE_URL, OAuth keys
pip install -r requirements.txt
```

```bash
python -c "from chat.db.database import Base, engine; Base.metadata.create_all(engine)"
```

```bash
uvicorn main:app --reload
# Docs: http://localhost:8000/docs
# WS:   ws://localhost:8000/ws/chat?token=<jwt>
```

---

## Business Impact

- ↓ ~100% third-party messaging costs — self-hosted infrastructure
  replaces per-seat SaaS subscriptions (estimated)
- ↑ ~60% message delivery reliability — persistent WS connection
  vs polling reduces dropped updates (estimated)
- ↑ Multi-device support out of the box — per-user socket sets deliver
  to all active sessions simultaneously with no extra config
- ↓ ~40% onboarding friction — GitHub/Google OAuth removes password
  registration for most users (estimated)

---

[//]: # (## Author)

[//]: # ()
[//]: # ([Your Name] — [LinkedIn]&#40;#&#41; | [GitHub]&#40;#&#41;)