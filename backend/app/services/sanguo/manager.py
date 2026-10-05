"""三国杀房间管理单例：房号分配、每秒心跳、闲置清扫"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Optional

from app.services.sanguo.room import IDLE_ROOM_SECONDS, SanguoRoom

logger = logging.getLogger(__name__)


class SanguoManager:
    def __init__(self):
        self._rooms: dict[str, SanguoRoom] = {}
        self._task: Optional[asyncio.Task] = None

    def create_room(self, host_id: int, host_nickname: str, heroes: list) -> SanguoRoom:
        room_id = self._new_room_id()
        room = SanguoRoom(room_id, host_id, heroes)
        room.members[host_id].nickname = host_nickname
        self._rooms[room_id] = room
        logger.info("[sanguo] 创建房间 %s 房主=%s", room_id, host_id)
        return room

    def _new_room_id(self) -> str:
        for _ in range(100):
            rid = f"{random.randint(100000, 999999)}"
            if rid not in self._rooms:
                return rid
        raise RuntimeError("房间号分配失败")

    def get(self, room_id: str) -> Optional[SanguoRoom]:
        return self._rooms.get(str(room_id))

    def remove(self, room_id: str) -> None:
        self._rooms.pop(str(room_id), None)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run())

    async def run(self) -> None:
        try:
            while True:
                now = time.time()
                for room in list(self._rooms.values()):
                    try:
                        room.tick(now)
                    except Exception:
                        logger.exception("[sanguo] 房间 %s tick 异常", room.room_id)
                if int(now) % 30 == 0:
                    await self._sweep(now)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("[sanguo] 房间心跳循环停止")
            raise

    async def _sweep(self, now: float) -> None:
        for room in list(self._rooms.values()):
            idle = now - room.last_activity
            no_conn = not any(m.connected for m in room.members.values())
            if room.status in ("WAITING", "RESULT") and no_conn \
                    and idle > IDLE_ROOM_SECONDS:
                logger.info("[sanguo] 回收闲置房间 %s", room.room_id)
                self.remove(room.room_id)

    def shutdown(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None


manager = SanguoManager()
