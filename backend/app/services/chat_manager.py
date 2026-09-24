"""Gestionnaire de connexions WebSocket du chat (mono-processus).

Structure : match_id → {user_id → WebSocket}. La persistance reste en base ;
ce manager ne fait que diffuser les événements temps réel (message,
frappe, lecture) aux clients connectés.

TODO(scaling) : pour un déploiement multi-instances, diffuser via Redis
pub/sub (même interface), cf. plan d'architecture.
"""

import json

from fastapi import WebSocket


class ChatManager:
    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, match_id: str, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms.setdefault(match_id, {})[user_id] = ws

    def disconnect(self, match_id: str, user_id: str) -> None:
        room = self._rooms.get(match_id)
        if room is None:
            return
        room.pop(user_id, None)
        if not room:
            self._rooms.pop(match_id, None)

    async def broadcast(
        self, match_id: str, payload: dict, *, exclude_user: str | None = None
    ) -> None:
        room = self._rooms.get(match_id, {})
        message = json.dumps(payload, ensure_ascii=False)
        stale: list[str] = []
        for user_id, ws in room.items():
            if user_id == exclude_user:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(user_id)
        for user_id in stale:
            self.disconnect(match_id, user_id)


chat_manager = ChatManager()
