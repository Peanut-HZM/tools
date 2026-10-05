"""房间管理单例：房号分配、每秒心跳、闲置清扫"""
from __future__ import annotations

import asyncio
import logging
import random
import time

from .boards import GameSettings
from .room import IDLE_ROOM_SECONDS, GameRoom

logger = logging.getLogger(__name__)


class RoomManager:
    def __init__(self):
        self._rooms: dict[str, GameRoom] = {}
        self._task: asyncio.Task | None = None

    def create_room(self, host_id: int, host_nickname: str,
                    board: dict, settings: GameSettings) -> GameRoom:
        room_id = self._new_room_id()
        room = GameRoom(room_id, host_id, board, settings)
        room.members[host_id].nickname = host_nickname
        self._rooms[room_id] = room
        logger.info("[werewolf] 创建房间 %s 房主=%s 板子=%s", room_id, host_id,
                    board.get("id"))
        return room

    def _new_room_id(self) -> str:
        for _ in range(100):
            rid = f"{random.randint(100000, 999999)}"
            if rid not in self._rooms:
                return rid
        raise RuntimeError("房间号分配失败")

    def get(self, room_id: str) -> GameRoom | None:
        return self._rooms.get(str(room_id))

    def remove(self, room_id: str) -> None:
        self._rooms.pop(str(room_id), None)

    def rooms_of(self, user_id: int) -> list[GameRoom]:
        return [r for r in self._rooms.values() if user_id in r.members]

    async def run(self) -> None:
        """每秒驱动所有房间；每 30s 清扫闲置房间"""
        try:
            while True:
                now = time.time()
                for room in list(self._rooms.values()):
                    try:
                        room.tick(now)
                    except Exception:
                        logger.exception("[werewolf] 房间 %s tick 异常", room.room_id)
                if int(now) % 30 == 0:
                    await self._sweep(now)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("[werewolf] 房间心跳循环停止")
            raise

    async def _sweep(self, now: float) -> None:
        for room in list(self._rooms.values()):
            idle = now - room.last_activity
            no_conn = not any(m.connected for m in room.members.values())
            if room.status in ("WAITING", "RESULT") and no_conn \
                    and idle > IDLE_ROOM_SECONDS:
                logger.info("[werewolf] 回收闲置房间 %s", room.room_id)
                self.remove(room.room_id)

    def shutdown(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None


manager = RoomManager()  # 模块级单例
