"""Endpoints chat : historique, envoi (REST de secours), lecture et
WebSocket temps réel `/ws/chat/{match_id}`.

Règles de sécurité :
- la conversation n'existe qu'entre membres d'un match ;
- un blocage (dans un sens comme dans l'autre) coupe l'accès immédiat ;
- token JWT requis (en-tête Bearer pour REST, `?token=` pour WebSocket).
"""

import json

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, get_session_factory
from app.core.security import decode_token, utcnow
from app.models.interactions import Match
from app.models.message import Message
from app.models.user import User
from app.schemas.profiles import MessageOut
from app.services.chat_manager import chat_manager
from app.services.matching import get_blocked_ids, get_match_or_none

router = APIRouter(tags=["chat"])

MAX_MESSAGE_LEN = 2000


class MessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LEN)


def _msg_out(msg: Message, me_id: str) -> MessageOut:
    return MessageOut(
        id=msg.id,
        sender_id=msg.sender_id,
        content=msg.content,
        created_at=msg.created_at,
        read_at=msg.read_at,
        is_mine=msg.sender_id == me_id,
    )


async def _get_allowed_match(
    db: AsyncSession, match_id: str, user_id: str
) -> Match:
    match = await get_match_or_none(db, match_id, user_id)
    if match is None:
        raise HTTPException(404, "Conversation introuvable.")
    peer = match.other_user_id(user_id)
    if peer in await get_blocked_ids(db, user_id):
        raise HTTPException(403, "Cette conversation est bloquée.")
    return match


@router.get(
    "/matches/{match_id}/messages",
    response_model=list[MessageOut],
    summary="Historique de la conversation (plus récents d'abord)",
)
async def list_messages(
    match_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    await _get_allowed_match(db, match_id, me.id)
    rows = (
        (
            await db.execute(
                select(Message)
                .where(Message.match_id == match_id)
                .order_by(Message.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [_msg_out(m, me.id) for m in rows]


@router.post(
    "/matches/{match_id}/messages",
    response_model=MessageOut,
    status_code=201,
    summary="Envoyer un message (fallback HTTP si le WebSocket est coupé)",
)
async def send_message(
    match_id: str,
    body: MessageIn,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    await _get_allowed_match(db, match_id, me.id)
    msg = Message(match_id=match_id, sender_id=me.id, content=body.content.strip())
    db.add(msg)
    await db.commit()
    # Diffusion temps réel aux clients WebSocket connectés (moi y compris
    # pour synchroniser mes autres appareils).
    await chat_manager.broadcast(
        match_id,
        {
            "type": "message",
            "message": _msg_out(msg, "").model_dump(mode="json"),
        },
    )
    # Phase 8 — notification (cloche + push) pour le destinataire hors-ligne.
    from app.services.notifications import notify_message_received

    await notify_message_received(db, match_id, me.id, msg.content)
    return _msg_out(msg, me.id)


@router.post(
    "/matches/{match_id}/read",
    summary="Marquer la conversation comme lue (accusés de lecture)",
)
async def mark_read(
    match_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_allowed_match(db, match_id, me.id)
    rows = (
        (
            await db.execute(
                select(Message).where(
                    Message.match_id == match_id,
                    Message.sender_id != me.id,
                    Message.read_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    now = utcnow()
    for msg in rows:
        msg.read_at = now
    await db.commit()
    if rows:
        await chat_manager.broadcast(
            match_id, {"type": "read", "by": me.id}
        )
    return {"read": len(rows)}


# ---------------------------------------------------------------- WebSocket


async def _ws_authenticate(
    ws: WebSocket, match_id: str, token: str | None, session_factory
) -> tuple[User, Match] | None:
    """Valide le token + l'appartenance au match. Ferme la socket sinon."""
    if not token:
        await ws.close(code=4401)
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access" or not payload.get("sub"):
            raise jwt.InvalidTokenError("type")
    except jwt.InvalidTokenError:
        await ws.close(code=4401)
        return None

    async with session_factory() as db:
        user = await db.get(User, payload["sub"])
        if user is None or not user.is_active:
            await ws.close(code=4401)
            return None
        match = await get_match_or_none(db, match_id, user.id)
        if match is None:
            await ws.close(code=4404)
            return None
        if match.other_user_id(user.id) in await get_blocked_ids(db, user.id):
            await ws.close(code=4403)
            return None
        return user, match


@router.websocket("/ws/chat/{match_id}")
async def chat_ws(
    ws: WebSocket,
    match_id: str,
    token: str | None = Query(default=None),
    session_factory=Depends(get_session_factory),
) -> None:
    """Canal temps réel d'une conversation.

    Messages JSON client → serveur :
      {"type": "message", "content": "…"}  → persisté + diffusé ("message")
      {"type": "typing"}                   → diffusé ("typing", non persisté)
      {"type": "read"}                     → lecture + diffusé ("read")
    """
    auth = await _ws_authenticate(ws, match_id, token, session_factory)
    if auth is None:
        return
    user, _match = auth

    await chat_manager.connect(match_id, user.id, ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "detail": "JSON invalide."})
                continue

            kind = data.get("type")
            if kind == "typing":
                await chat_manager.broadcast(
                    match_id,
                    {"type": "typing", "user_id": user.id},
                    exclude_user=user.id,
                )
            elif kind == "message":
                content = str(data.get("content", "")).strip()
                if not content or len(content) > MAX_MESSAGE_LEN:
                    await ws.send_json(
                        {"type": "error", "detail": "Message invalide."}
                    )
                    continue
                async with session_factory() as db:
                    # Revalidation à chaud (blocage éventuel depuis l'ouverture).
                    match = await get_match_or_none(db, match_id, user.id)
                    if match is None or match.other_user_id(
                        user.id
                    ) in await get_blocked_ids(db, user.id):
                        await ws.close(code=4403)
                        return
                    msg = Message(
                        match_id=match_id, sender_id=user.id, content=content
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)
                    payload = {
                        "type": "message",
                        "message": {
                            "id": msg.id,
                            "sender_id": msg.sender_id,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                            "read_at": None,
                        },
                    }
                await chat_manager.broadcast(match_id, payload)
                # Phase 8 — notification (cloche + push) du destinataire.
                from app.services.notifications import notify_message_received

                async with session_factory() as db_notif:
                    await notify_message_received(
                        db_notif, match_id, user.id, content
                    )
            elif kind == "read":
                async with session_factory() as db:
                    rows = (
                        (
                            await db.execute(
                                select(Message).where(
                                    Message.match_id == match_id,
                                    Message.sender_id != user.id,
                                    Message.read_at.is_(None),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    now = utcnow()
                    for msg in rows:
                        msg.read_at = now
                    await db.commit()
                await chat_manager.broadcast(
                    match_id, {"type": "read", "by": user.id}
                )
            else:
                await ws.send_json(
                    {"type": "error", "detail": "type inconnu"}
                )
    except WebSocketDisconnect:
        pass
    finally:
        chat_manager.disconnect(match_id, user.id)
