"""三国杀房间：成员/连接管理 + 引擎驱动 + 广播"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

from app.services.sanguo.engine import EngineError, SangouEngine

logger = logging.getLogger(__name__)

DISCONNECT_GRACE_SECONDS = 60
IDLE_ROOM_SECONDS = 600


@dataclass
class Member:
    user_id: int
    nickname: str
    connected: bool = False
    disconnected_at: float | None = None


class SanguoRoom:
    def __init__(self, room_id: str, host_id: int, heroes: list, settings: dict | None = None):
        self.room_id = room_id
        self.host_id = host_id
        self.heroes = list(heroes)   # 参与武将池（4 个 Hero）
        self.settings = settings or {}
        self.members: dict[int, Member] = {host_id: Member(host_id, "")}
        self.status = "WAITING"
        self.engine: Optional[SangouEngine] = None
        self._sockets: dict[int, object] = {}
        self.created_at = time.time()
        self.last_activity = time.time()
        self.started_at: float | None = None
        self.record_saved = False
        self._event_cursor = 0
        self._last_state_key: tuple | None = None
        self.on_broadcast: Callable[[dict], None] = self._noop
        self.on_send: Callable[[int, dict], None] = self._noop
        self.on_finished: Callable[[], None] = self._noop

    def _noop(self, *args, **kwargs):
        pass

    def _touch(self) -> None:
        self.last_activity = time.time()

    def _broadcast_room(self) -> None:
        self.on_broadcast({"type": "room", "room": self.member_view()})

    def _pump(self) -> None:
        """把引擎事件广播 + 每成员个人视角 state 推送 + 消息驱动结算"""
        if self.engine is None:
            return
        for ev in self.engine.events_since(self._event_cursor):
            self._event_cursor = ev["id"]
            self.on_broadcast({"type": "event", **ev})
        key = (self.engine.phase.value, self.engine.current_seat,
               self.engine.finished(), len(self.engine.timeline),
               self._event_cursor,
               tuple(sorted((p.seat, p.alive, p.hp) for p in self.engine.players)))
        if key != self._last_state_key:
            self._last_state_key = key
            for uid in list(self.members):
                self.on_send(uid, {"type": "state", "state": self.full_view(uid)})

    # ---------- 成员 ----------
    def member_count(self) -> int:
        return len(self.members)

    def capacity(self) -> int:
        return 4

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
                self.host_id = next(iter(self.members))
            self._broadcast_room()
        else:
            m = self.members[user_id]
            m.connected = False
            m.disconnected_at = time.time()
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

    def start(self, by_user_id: int, now: float) -> None:
        if by_user_id != self.host_id:
            raise ValueError("只有房主可以开始对局")
        if self.status != "WAITING":
            raise ValueError("对局已开始")
        if self.member_count() != self.capacity():
            raise ValueError(f"人数未满：{self.member_count()}/{self.capacity()}，需满员开局")
        # 成员顺序映射到座位 1-4（uid 升序）
        members = sorted(self.members.items())
        players = [(uid, m.nickname or f"玩家{uid}") for uid, m in members]
        picked = random.sample(list(self.heroes), 4)  # 8 将池随机 4 名上场
        engine = SangouEngine(players, picked)
        self.engine = engine
        self.status = "PLAYING"
        self.started_at = now
        engine.start(now)
        self._pump()
        self._touch()

    # ---------- 连接 ----------
    def mark_connected(self, user_id: int, ws) -> None:
        m = self.members.get(user_id)
        if m:
            old = self._sockets.get(user_id)
            if old is not None and old is not ws:
                try:
                    old.close()
                except Exception as e:  # noqa: BLE001
                    logger.debug("[sanguo] 关闭旧连接失败: %s", e)
            m.connected = True
            m.disconnected_at = None
            self._sockets[user_id] = ws
            self._touch()

    def mark_disconnected(self, user_id: int, now: float, ws=None) -> None:
        m = self.members.get(user_id)
        if m and (ws is None or self._sockets.get(user_id) is ws):
            m.connected = False
            m.disconnected_at = now
            self._sockets.pop(user_id, None)
            self._touch()

    # ---------- 消息 ----------
    def on_message(self, user_id: int, data: dict) -> None:
        if self.engine is None or self.engine.finished():
            raise EngineError("NOT_PLAYING", "当前没有进行中的对局")
        msg_type = data.get("type")
        if msg_type == "act":
            self.engine.play_card(user_id, data.get("card_ids") or [],
                                  data.get("targets"), data.get("as_name"))
        elif msg_type == "respond":
            self.engine.respond(user_id, data.get("card_ids") or [])
        elif msg_type == "skill":
            skill = data.get("skill")
            if skill == "rende":
                self.engine.rende(user_id, int(data["target"]), data.get("card_ids") or [])
            elif skill == "qingnang":
                self.engine.qingnang(user_id, int(data["card_id"]), int(data["target"]))
            elif skill == "lijian":
                self.engine.lijian(user_id, int(data["card_id"]),
                                   int(data["male_a"]), int(data["male_b"]))
            else:
                raise EngineError("UNKNOWN_SKILL", f"未知技能: {skill}")
        elif msg_type == "next_phase":
            self.engine.next_phase(user_id)
        elif msg_type == "discard":
            self.engine.discard_to_limit(user_id)
        else:
            raise EngineError("UNKNOWN_MESSAGE", f"未知消息类型: {msg_type}")
        self._pump()
        self._touch()

    # ---------- 心跳 ----------
    def tick(self, now: float) -> None:
        if self.engine and not self.engine.finished():
            for uid, m in self.members.items():
                if m.disconnected_at is not None \
                        and now - m.disconnected_at > DISCONNECT_GRACE_SECONDS:
                    uid_int = uid
                    if uid_int in self.engine._by_uid:
                        pl = self.engine._by_uid[uid_int]
                        pl.escaped = True
            self.engine.tick(now)
            self._pump()
        if self.engine and self.engine.finished() and self.status == "PLAYING":
            self.status = "RESULT"
            self.last_activity = time.time()
            self.on_finished()

    # ---------- 视图 ----------
    def member_view(self) -> dict:
        return {"room_id": self.room_id, "status": self.status,
                "host_id": str(self.host_id), "capacity": self.capacity(),
                "members": [{"user_id": str(uid), "nickname": m.nickname,
                             "connected": m.connected, "is_host": uid == self.host_id,
                             "seat": i + 1}
                            for i, (uid, m) in enumerate(self.members.items())]}

    def full_view(self, user_id: int) -> dict:
        view = dict(self.member_view())
        if self.engine:
            view["snapshot"] = self.engine.snapshot(user_id)
        return view

    def reset_for_replay(self, by_user_id: int, now: float) -> None:
        if by_user_id != self.host_id:
            raise ValueError("只有房主可以开始新一局")
        if self.status != "RESULT":
            raise ValueError("对局尚未结束")
        self.status = "PLAYING"
        self.record_saved = False
        self._event_cursor = 0
        self._last_state_key = None
        members = sorted(self.members.items())
        players = [(uid, m.nickname or f"玩家{uid}") for uid, m in members]
        picked = random.sample(list(self.heroes), 4)
        self.engine = SangouEngine(players, picked)
        self.engine.start(now)
        self.started_at = now
        self._pump()
        self._touch()

    def build_record_summary(self) -> dict:
        eng = self.engine
        winner = eng.winner()
        role_label = {"LORD": "主公", "LOYAL": "忠臣", "REBEL": "反贼", "SPY": "内奸"}
        players = []
        for p in eng.players:
            players.append({
                "user_id": str(p.uid), "nickname": p.nickname,
                "hero": p.hero.name, "role": p.role,
                "role_name": role_label.get(p.role, p.role),
                "alive_at_end": p.alive,
                "is_winner": self._is_winner(p, winner),
            })
        duration = int(time.time() - (self.started_at or self.created_at))
        return {
            "room_id": self.room_id,
            "board_name": f"{len(eng.players)}人身份局",
            "player_count": len(eng.players),
            "winner": winner or "UNKNOWN",
            "turn_count": eng.turn_count,
            "duration_seconds": max(0, duration),
            "config": {"heroes": [h.name for h in self.heroes]},
            "players": players,
            "timeline": eng.public_history(),
        }

    def _is_winner(self, p, winner: str | None) -> bool:
        if winner == "LORD":
            return p.role in ("LORD", "LOYAL")
        if winner == "REBEL":
            return p.role == "REBEL"
        if winner == "SPY":
            return p.role == "SPY"
        return False
