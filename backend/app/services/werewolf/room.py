"""游戏房间：成员/连接管理 + 引擎驱动 + 视图（公共广播/私有下发由路由层回调实现）"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from .boards import GameSettings, validate_board
from .engine import EngineError, WerewolfEngine
from .roles import Role

logger = logging.getLogger(__name__)

DISCONNECT_GRACE_SECONDS = 60   # 断线保留座位等待重连
IDLE_ROOM_SECONDS = 600         # WAITING/RESULT 且无连接的房间回收


async def _close_quietly(ws) -> None:
    try:
        await ws.close()
    except Exception as e:  # noqa: BLE001  连接可能已死
        logger.debug("[werewolf] 挤线关闭旧连接失败: %s", e)


def sync_close(ws) -> None:
    try:
        ws.close()
    except Exception as e:  # noqa: BLE001
        logger.debug("[werewolf] 关闭旧连接失败: %s", e)


@dataclass
class Member:
    user_id: int
    nickname: str
    connected: bool = False
    disconnected_at: float | None = None


class GameRoom:
    def __init__(self, room_id: str, host_id: int, board: dict, settings: GameSettings):
        self.room_id = room_id
        self.host_id = host_id
        self.board = dict(board)              # {id,name,player_count,roles{RoleStr:int}}
        self.settings = settings
        self.members: dict[int, Member] = {host_id: Member(host_id, "")}
        self.status = "WAITING"
        self.engine: WerewolfEngine | None = None
        self._event_cursor = 0
        self._last_state_key: tuple | None = None
        self._sockets: dict[int, object] = {}  # user_id -> WebSocket（由路由层注册）
        self.created_at = time.time()
        self.last_activity = time.time()
        self.started_at: float | None = None
        self.record_saved = False
        # 连接层回调（路由模块注入，同步函数；发送通过 asyncio.create_task 落地）
        self.on_broadcast: Callable[[dict], None] = self._noop
        self.on_send: Callable[[int, dict], None] = self._noop
        self.on_finished: Callable[[], None] = self._noop  # 对局结束钩子（结算落库）

    def _noop(self, *args, **kwargs):  # pragma: no cover - 默认空实现
        pass

    def _pump(self) -> None:
        """把引擎新增的公共事件/私有消息经回调推送出去；
        阶段/天数/发言数变化时向每个成员推送个人视角 state 快照（spec §5.4）"""
        if self.engine is None:
            return
        for ev in self.engine.events_since(self._event_cursor):
            self._event_cursor = ev["id"]
            self.on_broadcast({"type": "event", **ev})
        for uid, priv in self.engine.drain_all_private():
            self.on_send(uid, {"type": "private", **priv})
        key = (self.engine.phase.value, self.engine.day, self.engine.finished(),
               len(self.engine._speeches), self._event_cursor)
        if key != self._last_state_key:
            self._last_state_key = key
            for uid in list(self.members):
                self.on_send(uid, {"type": "state", "state": self.full_view(uid)})

    # ---------- 成员 ----------
    def member_count(self) -> int:
        return len(self.members)

    def capacity(self) -> int:
        return self.board["player_count"]

    def add_member(self, user_id: int, nickname: str) -> None:
        if self.status != "WAITING":
            raise ValueError("对局已开始，无法加入")
        if user_id in self.members:
            return
        if self.member_count() >= self.capacity():
            raise ValueError("房间已满员")
        self.members[user_id] = Member(user_id, nickname)
        self._touch()
        self._broadcast_room()

    def remove_member(self, user_id: int) -> None:
        if user_id not in self.members:
            return
        if self.status == "WAITING":
            self.members.pop(user_id)
            if user_id == self.host_id and self.members:
                self.host_id = next(iter(self.members))  # 房主转移
            self._broadcast_room()
        else:
            # 对局中离开视为逃跑：保留座位与身份，转托管
            m = self.members[user_id]
            m.connected = False
            m.disconnected_at = time.time()
            if self.engine:
                self.engine.set_escaped(user_id, True)
        self._touch()

    def kick(self, user_id: int, by_user_id: int) -> None:
        if by_user_id != self.host_id:
            raise ValueError("只有房主可以踢人")
        if self.status != "WAITING":
            raise ValueError("对局中不能踢人")
        if user_id == self.host_id:
            raise ValueError("不能踢自己")
        self.members.pop(user_id, None)
        self._touch()
        self._broadcast_room()

    def update_config(self, board: dict | None, settings: GameSettings | None,
                      by_user_id: int) -> None:
        if by_user_id != self.host_id:
            raise ValueError("只有房主可以修改配置")
        if self.status != "WAITING":
            raise ValueError("对局中不能修改配置")
        if board is not None:
            if not board.get("id"):
                errors, _ = validate_board(board["roles"])
                if errors:
                    raise ValueError("；".join(errors))
            if self.member_count() > board["player_count"]:
                raise ValueError("当前人数超过新板子容量")
            self.board = dict(board)
        if settings is not None:
            self.settings = settings
        self._touch()

    def start(self, by_user_id: int, now: float) -> None:
        if by_user_id != self.host_id:
            raise ValueError("只有房主可以开始对局")
        if self.status != "WAITING":
            raise ValueError("对局已开始")
        if self.member_count() < 2:
            raise ValueError("至少 2 名玩家才能开始")
        if self.member_count() != self.capacity():
            raise ValueError(f"人数未满：{self.member_count()}/{self.capacity()}，"
                             "板子角色数量要求满员开局")
        players = [(uid, m.nickname or f"玩家{uid}") for uid, m in self.members.items()]
        roles = {Role(k): v for k, v in self.board["roles"].items()}
        self.engine = WerewolfEngine(players, roles, self.settings, now=now)
        self.status = "PLAYING"
        self.started_at = now
        self.engine.start(now)
        self._pump()
        self._touch()

    # ---------- 连接 ----------
    def mark_connected(self, user_id: int, ws) -> None:
        m = self.members.get(user_id)
        if m:
            old = self._sockets.get(user_id)
            if old is not None and old is not ws:
                # 挤线：异步关闭旧连接（starlette WebSocket.close 是协程，
                # 同步调用不会真正执行，旧连接会变成收不到广播的孤儿）
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_close_quietly(old))
                except RuntimeError:
                    sync_close(old)  # 无事件循环（单测假连接）
            m.connected = True
            m.disconnected_at = None
            self._sockets[user_id] = ws
            self._touch()

    def mark_disconnected(self, user_id: int, now: float, ws=None) -> None:
        """ws 传入时做连接比对：仅当断开的是当前注册连接才生效（旧连接迟到的
        断开事件不得清掉新连接，spec §8 挤线语义）"""
        m = self.members.get(user_id)
        if m and (ws is None or self._sockets.get(user_id) is ws):
            m.connected = False
            m.disconnected_at = now
            self._sockets.pop(user_id, None)
            self._touch()

    # ---------- 消息入口（路由 WS 层调用） ----------
    def on_message(self, user_id: int, data: dict) -> None:
        if self.engine is None or self.engine.finished():
            raise EngineError("NOT_PLAYING", "当前没有进行中的对局")
        msg_type = data.get("type")
        if msg_type == "act":
            self.engine.submit_action(user_id, data.get("action"), data.get("target"),
                                      time.time())
        elif msg_type == "speech":
            self.engine.submit_speech(user_id, data.get("content", ""), time.time())
        elif msg_type == "last_words":
            self.engine.submit_last_words(user_id, data.get("content", ""), time.time())
        elif msg_type == "skip":
            self.engine.skip(user_id, time.time())
        else:
            raise EngineError("UNKNOWN_MESSAGE", f"未知消息类型: {msg_type}")
        self._pump()
        self._touch()

    # ---------- 心跳驱动 ----------
    def tick(self, now: float) -> None:
        if self.engine and not self.engine.finished():
            # 断线超过宽限 → 托管（直到对局结束，spec §5.6）
            for uid, m in self.members.items():
                if m.disconnected_at is not None and not self.engine._by_uid[uid].escaped \
                        and now - m.disconnected_at > DISCONNECT_GRACE_SECONDS:
                    self.engine.set_escaped(uid, True)
                    logger.info("[werewolf] 玩家 %s 断线超时转托管 room=%s", uid, self.room_id)
            self.engine.check_timeouts(now)
            self._pump()
        if self.engine and self.engine.finished() and self.status == "PLAYING":
            self.status = "RESULT"
            self.last_activity = time.time()
            self.on_finished()

    # ---------- 视图 ----------
    def member_view(self) -> dict:
        return {
            "room_id": self.room_id,
            "status": self.status,
            "host_id": str(self.host_id),
            "board": self.board,
            "settings": self.settings_view(),
            "capacity": self.capacity(),
            "members": [
                {"user_id": str(uid), "nickname": m.nickname, "connected": m.connected,
                 "is_host": uid == self.host_id, "seat": i + 1}
                for i, (uid, m) in enumerate(self.members.items())
            ],
        }

    def settings_view(self) -> dict:
        s = self.settings
        return {"speech_seconds": s.speech_seconds, "vote_seconds": s.vote_seconds,
                "night_seconds": s.night_seconds,
                "witch_self_rescue": s.witch_self_rescue,
                "witch_guard_conflict": s.witch_guard_conflict}

    def _uid_of_seat(self, seat: int) -> int | None:
        for i, uid in enumerate(self.members):
            if i + 1 == seat:
                return uid
        return None

    def full_view(self, user_id: int) -> dict:
        view = dict(self.member_view())
        if self.engine:
            snap = self.engine.snapshot(user_id)
            for p in snap["players"]:
                m = self.members.get(self._uid_of_seat(p["seat"]))
                if m:
                    p["connected"] = m.connected
            view["snapshot"] = snap
        return view

    def _touch(self) -> None:
        self.last_activity = time.time()

    def _broadcast_room(self) -> None:
        """等待期房间视图广播（成员变动实时刷新前端列表）"""
        self.on_broadcast({"type": "room", "room": self.member_view()})

    # ---------- 再来一局 ----------
    def reset_for_replay(self, by_user_id: int, now: float) -> None:
        if by_user_id != self.host_id:
            raise ValueError("只有房主可以开始新一局")
        if self.status != "RESULT":
            raise ValueError("对局尚未结束")
        self.status = "PLAYING"
        self.record_saved = False
        self._event_cursor = 0        # 新引擎事件 id 从 0 重新计数
        self._last_state_key = None
        players = [(uid, m.nickname or f"玩家{uid}") for uid, m in self.members.items()]
        roles = {Role(k): v for k, v in self.board["roles"].items()}
        self.engine = WerewolfEngine(players, roles, self.settings, now=now)
        self.engine.start(now)
        self.started_at = now
        self._touch()

    # ---------- 结算落库汇总 ----------
    def build_record_summary(self) -> dict:
        eng = self.engine
        winner = eng.winner()
        players = []
        for p in eng.players:
            players.append({
                "user_id": str(p.user_id), "nickname": p.nickname,
                "role": p.role.value if p.role else "UNKNOWN",
                "alive_at_end": p.alive,
                "is_winner": (winner == "WEREWOLF") == (p.role == Role.WEREWOLF),
            })
        duration = int(time.time() - (self.started_at or self.created_at))
        return {
            "room_id": self.room_id,
            "board_name": self.board.get("name", "自定义局"),
            "player_count": len(eng.players),
            "winner": winner or "UNKNOWN",
            "day_count": eng.day,
            "duration_seconds": max(0, duration),
            "config": {**self.settings_view(), "roles": self.board["roles"]},
            "players": players,
            "timeline": eng.public_history(),
        }
