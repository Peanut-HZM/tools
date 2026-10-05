"""狼人杀对局状态机（服务端权威法官）

纯逻辑：时间由调用方注入 now 参数，网络/DB 由上层（room/manager）负责，
pytest 可确定性驱动。规则依据 spec §3（对齐市面主流狼人杀）。
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum

from .boards import GameSettings
from .roles import NIGHT_ACTION_ORDER, ROLE_CAMPS, Role

logger = logging.getLogger(__name__)

WIN_VILLAGER = "VILLAGER"
WIN_WEREWOLF = "WEREWOLF"


class Phase(str, Enum):
    WAITING = "WAITING"
    DAWN = "DAWN"
    NIGHT_GUARD = "NIGHT_GUARD"
    NIGHT_WEREWOLF = "NIGHT_WEREWOLF"
    NIGHT_SEER = "NIGHT_SEER"
    NIGHT_WITCH = "NIGHT_WITCH"
    HUNTER_SHOT = "HUNTER_SHOT"
    LAST_WORDS = "LAST_WORDS"
    DAY_SPEECH = "DAY_SPEECH"
    DAY_VOTE = "DAY_VOTE"
    PK_SPEECH = "PK_SPEECH"
    DAY_VOTE_PK = "DAY_VOTE_PK"
    RESULT = "RESULT"


PHASE_OF_ROLE = {
    Role.GUARD: Phase.NIGHT_GUARD,
    Role.WEREWOLF: Phase.NIGHT_WEREWOLF,
    Role.SEER: Phase.NIGHT_SEER,
    Role.WITCH: Phase.NIGHT_WITCH,
}
ROLE_OF_PHASE = {v: k for k, v in PHASE_OF_ROLE.items()}


class EngineError(Exception):
    """对局业务拒绝（前端展示 message，按 code 处理）"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class EnginePlayer:
    user_id: int
    nickname: str
    seat: int
    role: Role | None = None
    alive: bool = True
    escaped: bool = False          # 断线超 60s 托管，直到对局结束
    can_vote: bool = True
    idiot_revealed: bool = False
    death_cause: str | None = None   # wolf/poison/milk/exile/shot
    witch_save_used: bool = False
    witch_poison_used: bool = False
    seer_checks: list = field(default_factory=list)   # [{seat, is_werewolf}]


@dataclass
class NightRecord:
    guard: int | None = None
    wolf: int | None = None
    seer: int | None = None
    save: bool = False
    poison: int | None = None


class WerewolfEngine:
    """一局狼人杀的完整状态机。公开方法均为同步调用，now 为 Unix 秒。"""

    def __init__(self, players: list[tuple[int, str]], roles: dict[Role, int],
                 settings: GameSettings, now: float,
                 rng: random.Random | None = None):
        self.players: list[EnginePlayer] = [
            EnginePlayer(user_id=uid, nickname=nick, seat=i + 1)
            for i, (uid, nick) in enumerate(players)
        ]
        self._by_uid = {p.user_id: p for p in self.players}
        self.roles = dict(roles)
        self.settings = settings
        self.rng = rng or random.Random()
        self.phase = Phase.WAITING
        self.day = 0
        self.deadline: float | None = None
        self._events: list[dict] = []
        self._event_seq = 0
        self._private_outbox: list[tuple[int, dict]] = []
        self._speeches: list[dict] = []
        self._last_votes: list[dict] | None = None
        self._winner: str | None = None
        # 夜晚状态
        self.night = NightRecord()
        self._prev_guard: int | None = None
        self._submitted: set[int] = set()
        # 白天状态
        self._speech_queue: list[int] = []
        self._speech_idx = 0
        self._next_speech_start = 1
        self._last_exiled_seat: int | None = None
        self._votes: dict[int, int | None] = {}
        self._vote_history: list[dict] = []  # 每轮投票的公开票型（回放用）
        self._timeline: list[dict] = []      # 统一回放时间线（按发生顺序交错）
        self._pk_seats: list[int] = []
        self._pk_seats_orig: list[int] = []
        # 流程待办
        self._pending_last_words: list[int] = []   # 待遗言座位队列
        self._pending_hunter: int | None = None  # 待开枪座位
        self._pending_after_hunter: tuple | None = None  # 开枪后的续接流程
        self._hunter_handled: set[int] = set()           # 已触发过开枪的猎人座位
        self._dawn_deaths: dict[int, str] = {}
        self._last_words_then = "night"   # 遗言结束后的去向：day=首夜→白天 / night=放逐→下一夜

    # ---------- 基础 ----------
    def _emit(self, text: str) -> None:
        self._event_seq += 1
        self._events.append({"id": self._event_seq, "text": text})
        self._timeline.append({"kind": "event", "day": self.day,
                               "phase": self.phase.value if hasattr(self, "phase") else "",
                               "text": text})

    def _timeline_speech(self, seat: int, nickname: str, content: str,
                         last_words: bool = False, pk: bool = False) -> None:
        self._timeline.append({"kind": "speech", "day": self.day, "seat": seat,
                               "nickname": nickname, "text": content,
                               "last_words": last_words, "pk": pk})

    def _timeline_vote(self, kind: str, detail: list[dict], exiled: int | None) -> None:
        self._timeline.append({"kind": "vote", "day": self.day,
                               "vote_kind": kind, "detail": detail, "exiled": exiled})

    def _to(self, user_id: int, payload: dict) -> None:
        self._private_outbox.append((user_id, payload))

    def drain_private(self, user_id: int) -> list[dict]:
        mine = [p for uid, p in self._private_outbox if uid == user_id]
        self._private_outbox = [(uid, p) for uid, p in self._private_outbox if uid != user_id]
        return mine

    def drain_all_private(self) -> list[tuple[int, dict]]:
        """取走全部待发私有消息（按用户分离由 room._pump 完成）"""
        out = self._private_outbox
        self._private_outbox = []
        return out

    def events_since(self, event_id: int) -> list[dict]:
        return [e for e in self._events if e["id"] > event_id]

    # ---------- 对局开始与发牌 ----------
    def start(self, now: float) -> None:
        if self.phase != Phase.WAITING:
            raise EngineError("ALREADY_STARTED", "对局已开始")
        deck: list[Role] = []
        for role, cnt in self.roles.items():
            deck += [role] * cnt
        self.rng.shuffle(deck)
        for p, role in zip(self.players, deck):
            p.role = role
        for p in self.players:
            mates = None
            if p.role == Role.WEREWOLF:
                mates = [q.seat for q in self.players
                         if q.role == Role.WEREWOLF and q.seat != p.seat]
            self._to(p.user_id, {"kind": "role", "role": p.role.value, "mates": mates})
        self.day = 1
        self._emit(f"对局开始，共 {len(self.players)} 名玩家")
        self._begin_night(now)

    # ---------- 夜晚 ----------
    def _begin_night(self, now: float) -> None:
        self.night = NightRecord()
        self._submitted = set()
        self._emit(f"第 {self.day} 夜：天黑请闭眼")
        first = self._first_night_phase()
        if first is None:
            # 没有任何存活夜晚角色（理论不达：必有狼；防御性兜底）
            self._resolve_night(now)
        else:
            self._enter_phase(first, now)

    def _alive_with_role(self, role: Role) -> list[EnginePlayer]:
        return [p for p in self.players if p.alive and p.role == role]

    def _first_night_phase(self) -> Phase | None:
        for role in NIGHT_ACTION_ORDER:
            if self._alive_with_role(role):
                return PHASE_OF_ROLE[role]
        return None

    def _next_night_phase(self, current: Phase) -> Phase | None:
        order = [Phase.NIGHT_GUARD, Phase.NIGHT_WEREWOLF, Phase.NIGHT_SEER, Phase.NIGHT_WITCH]
        for ph in order[order.index(current) + 1:]:
            if self._alive_with_role(ROLE_OF_PHASE[ph]):
                return ph
        return None

    def _enter_phase(self, phase: Phase, now: float) -> None:
        self.phase = phase
        seconds = {
            Phase.NIGHT_GUARD: self.settings.night_seconds,
            Phase.NIGHT_WEREWOLF: self.settings.night_seconds,
            Phase.NIGHT_SEER: self.settings.night_seconds,
            Phase.NIGHT_WITCH: self.settings.night_seconds,
            Phase.DAWN: self.settings.dawn_seconds,
            Phase.DAY_VOTE: self.settings.vote_seconds,
            Phase.DAY_VOTE_PK: self.settings.vote_seconds,
            Phase.HUNTER_SHOT: self.settings.night_seconds,
            Phase.LAST_WORDS: self.settings.last_words_seconds,
        }.get(phase)
        self.deadline = now + seconds if seconds else None
        if phase == Phase.HUNTER_SHOT:
            hunter = self.players[self._pending_hunter - 1]
            self._to(hunter.user_id, {"kind": "hunter_prompt"})
        if phase == Phase.NIGHT_WITCH:
            # 手中有解药时才告知刀口（spec §3.2）
            for w in self._alive_with_role(Role.WITCH):
                if not w.witch_save_used and self.night.wolf is not None:
                    self._to(w.user_id, {"kind": "witch_victim", "target": self.night.wolf})
        if phase == Phase.LAST_WORDS:
            seat = self._pending_last_words[0]
            self._emit(f"请 {seat} 号玩家发表遗言")
        if phase == Phase.DAY_SPEECH:
            seat = self._speech_queue[self._speech_idx]
            self.deadline = now + self.settings.speech_seconds
            self._emit(f"轮到 {seat} 号玩家发言")
        if phase == Phase.PK_SPEECH:
            seat = self._speech_queue[self._speech_idx]
            self.deadline = now + self.settings.pk_seconds
            self._emit(f"PK 发言：{seat} 号")

    # ---------- 行动提交 ----------
    def submit_action(self, user_id: int, action: str, target: int | None,
                      now: float) -> None:
        p = self._by_uid.get(user_id)
        if p is None:
            raise EngineError("NOT_IN_GAME", "你不在此对局中")
        if self.phase == Phase.RESULT:
            raise EngineError("GAME_OVER", "对局已结束")
        handler = {
            "guard_protect": self._act_guard,
            "werewolf_kill": self._act_wolf,
            "seer_check": self._act_seer,
            "witch_save": self._act_witch_save,
            "witch_poison": self._act_witch_poison,
            "hunter_shot": self._act_hunter,
            "vote": self._act_vote,
            "vote_pk": self._act_vote_pk,
        }.get(action)
        if handler is None:
            raise EngineError("UNKNOWN_ACTION", f"未知行动: {action}")
        handler(p, target, now)

    def _require_phase(self, p: EnginePlayer, phase: Phase) -> None:
        if self.phase != phase:
            raise EngineError("WRONG_PHASE", "当前不是该行动阶段")
        if not p.alive:
            raise EngineError("NOT_ALIVE", "你已出局")
        if p.escaped:
            raise EngineError("HOSTED", "你已断线托管，无法行动")

    def _valid_target(self, target: int | None, exclude_self: EnginePlayer | None = None) -> bool:
        if target is None or not 1 <= target <= len(self.players):
            return False
        if exclude_self is not None and target == exclude_self.seat:
            return False
        return self.players[target - 1].alive

    def _act_guard(self, p: EnginePlayer, target: int | None, now: float) -> None:
        self._require_phase(p, Phase.NIGHT_GUARD)
        if p.role != Role.GUARD:
            raise EngineError("NOT_YOUR_TURN", "你不是守卫")
        if p.user_id in self._submitted:
            raise EngineError("ALREADY_ACTED", "本夜已行动")
        if not self._valid_target(target):
            raise EngineError("INVALID_TARGET", "守护目标无效")
        if self._prev_guard is not None and target == self._prev_guard:
            raise EngineError("INVALID_TARGET", "不能连续两晚守护同一人")
        self.night.guard = target
        self._submitted.add(p.user_id)
        self._advance_if_phase_done(now)

    def _act_wolf(self, p: EnginePlayer, target: int | None, now: float) -> None:
        self._require_phase(p, Phase.NIGHT_WEREWOLF)
        if p.role != Role.WEREWOLF:
            raise EngineError("NOT_YOUR_TURN", "你不是狼人")
        if not self._valid_target(target):
            raise EngineError("INVALID_TARGET", "刀杀目标无效")
        self.night.wolf = target  # 队友可改刀，最后一次为准
        self._submitted.add(p.user_id)
        self._advance_if_phase_done(now)

    def _act_seer(self, p: EnginePlayer, target: int | None, now: float) -> None:
        self._require_phase(p, Phase.NIGHT_SEER)
        if p.role != Role.SEER:
            raise EngineError("NOT_YOUR_TURN", "你不是预言家")
        if p.user_id in self._submitted:
            raise EngineError("ALREADY_ACTED", "本夜已查验")
        if not self._valid_target(target, exclude_self=p):
            raise EngineError("INVALID_TARGET", "查验目标无效")
        is_wolf = self.players[target - 1].role == Role.WEREWOLF
        p.seer_checks.append({"seat": target, "is_werewolf": is_wolf})
        self.night.seer = target
        self._submitted.add(p.user_id)
        self._to(p.user_id, {"kind": "seer_result", "target": target, "is_werewolf": is_wolf})
        self._advance_if_phase_done(now)

    def _witch_self_ok(self, p: EnginePlayer) -> bool:
        mode = self.settings.witch_self_rescue
        if mode == "always":
            return True
        if mode == "first_night":
            return self.day == 1
        return False

    def _act_witch_save(self, p: EnginePlayer, target: int | None, now: float) -> None:
        self._require_phase(p, Phase.NIGHT_WITCH)
        if p.role != Role.WITCH:
            raise EngineError("NOT_YOUR_TURN", "你不是女巫")
        if p.user_id in self._submitted:
            raise EngineError("ALREADY_ACTED", "本夜已行动")
        if p.witch_save_used:
            raise EngineError("NO_POTION", "解药已用完")
        if self.night.wolf is None:
            raise EngineError("INVALID_TARGET", "今晚无人被刀")
        if target != self.night.wolf:
            raise EngineError("INVALID_TARGET", "只能救今晚被刀的玩家")
        if target == p.seat and not self._witch_self_ok(p):
            raise EngineError("SELF_RESCUE_FORBIDDEN", "当前规则不允许自救")
        p.witch_save_used = True
        self.night.save = True
        self._submitted.add(p.user_id)
        self._advance_if_phase_done(now)

    def _act_witch_poison(self, p: EnginePlayer, target: int | None, now: float) -> None:
        self._require_phase(p, Phase.NIGHT_WITCH)
        if p.role != Role.WITCH:
            raise EngineError("NOT_YOUR_TURN", "你不是女巫")
        if p.user_id in self._submitted:
            raise EngineError("ALREADY_ACTED", "本夜已行动")
        if p.witch_poison_used:
            raise EngineError("NO_POTION", "毒药已用完")
        if not self._valid_target(target, exclude_self=p):
            raise EngineError("INVALID_TARGET", "毒杀目标无效")
        p.witch_poison_used = True
        self.night.poison = target
        self._submitted.add(p.user_id)
        self._advance_if_phase_done(now)

    def _act_hunter(self, p: EnginePlayer, target: int | None, now: float) -> None:
        if self.phase != Phase.HUNTER_SHOT or self._pending_hunter != p.seat:
            raise EngineError("NOT_YOUR_TURN", "当前不是你的开枪阶段")
        # 猎人已出局（被刀/被放逐）才有开枪权，故不检查 alive
        if p.death_cause not in ("wolf", "exile"):
            raise EngineError("CANNOT_SHOOT", "当前死因无法开枪")
        if target is not None:
            if target == p.seat or not self._valid_target(target):
                raise EngineError("INVALID_TARGET", "开枪目标无效")
            victim = self.players[target - 1]
            victim.alive = False
            victim.death_cause = "shot"
            self._emit(f"猎人开枪带走了 {target} 号")
        self._pending_hunter = None
        self._continue_after_hunter(now)

    def _phase_complete(self) -> bool:
        if self.phase == Phase.NIGHT_GUARD:
            return all(g.user_id in self._submitted for g in self._alive_with_role(Role.GUARD))
        if self.phase == Phase.NIGHT_WEREWOLF:
            return all(w.user_id in self._submitted
                       for w in self._alive_with_role(Role.WEREWOLF))
        if self.phase == Phase.NIGHT_SEER:
            return all(s.user_id in self._submitted for s in self._alive_with_role(Role.SEER))
        if self.phase == Phase.NIGHT_WITCH:
            return all(w.user_id in self._submitted for w in self._alive_with_role(Role.WITCH))
        return False

    def _advance_if_phase_done(self, now: float) -> None:
        if self._phase_complete():
            self._finish_night_phase(now)

    def _finish_night_phase(self, now: float) -> None:
        nxt = self._next_night_phase(self.phase)
        if nxt is None:
            self._resolve_night(now)
        else:
            self._submitted = set()
            self._enter_phase(nxt, now)

    # ---------- 夜晚结算 ----------
    def _resolve_night(self, now: float) -> None:
        n = self.night
        deaths: dict[int, str] = {}
        if n.wolf is not None:
            protected = (n.guard == n.wolf)
            if n.save and protected and self.settings.witch_guard_conflict:
                deaths[n.wolf] = "milk"       # 奶穿：同晚被守+被救 → 死
            elif n.save or protected:
                pass                          # 被救或被守 → 活
            else:
                deaths[n.wolf] = "wolf"
        if n.poison is not None and n.poison not in deaths:
            deaths[n.poison] = "poison"
        self._prev_guard = n.guard
        self._dawn_deaths = deaths
        for seat, cause in deaths.items():
            p = self.players[seat - 1]
            p.alive = False
            p.death_cause = cause
        if deaths:
            names = "、".join(f"{s} 号" for s in sorted(deaths))
            self._emit(f"天亮了，昨夜 {names} 死亡")
        else:
            self._emit("天亮了，昨夜是平安夜")
        self._enter_phase(Phase.DAWN, now)

    def _after_dawn(self, now: float) -> None:
        deaths = self._dawn_deaths
        # 夜死的猎人（被刀死才可枪；被毒/奶穿不可）先开枪（仅触发一次）
        for seat, cause in sorted(deaths.items()):
            p = self.players[seat - 1]
            if p.role == Role.HUNTER and cause == "wolf" \
                    and seat not in self._hunter_handled:
                self._hunter_handled.add(seat)
                self._pending_hunter = seat
                self._pending_after_hunter = ("after_dawn", seat)
                self._enter_phase(Phase.HUNTER_SHOT, now)
                return
        # 首夜死者依次留遗言，结束后进入白天发言
        if self.day == 1 and deaths:
            self._pending_last_words = sorted(deaths)
            self._last_words_then = "day"
            self._enter_phase(Phase.LAST_WORDS, now)
            return
        self._begin_day(now)

    def _begin_day(self, now: float) -> None:
        if self._check_win(now):
            return
        start = self._speech_start_seat()
        self._speech_queue = self._circular_alive_from(start)
        self._speech_idx = 0
        if not self._speech_queue:
            self._to_vote(now)
            return
        self._enter_phase(Phase.DAY_SPEECH, now)

    def _speech_start_seat(self) -> int:
        deaths = sorted(self._dawn_deaths or {})
        if deaths:
            return deaths[0] % len(self.players) + 1  # 首个死者下一位（环形）
        return self._next_speech_start  # 无死者：上一发言轮末尾的下一座（spec §3.3）

    def _circular_alive_from(self, start: int) -> list[int]:
        n = len(self.players)
        ordered = [((start - 1 + i) % n) + 1 for i in range(n)]
        return [s for s in ordered if self.players[s - 1].alive]

    # ---------- 白天 ----------
    def submit_speech(self, user_id: int, content: str, now: float) -> None:
        p = self._by_uid.get(user_id)
        if p is None:
            raise EngineError("NOT_IN_GAME", "你不在此对局中")
        if self.phase not in (Phase.DAY_SPEECH, Phase.PK_SPEECH):
            raise EngineError("WRONG_PHASE", "当前不是发言阶段")
        if not p.alive:
            raise EngineError("NOT_ALIVE", "你已出局")
        if p.escaped:
            raise EngineError("HOSTED", "你已断线托管")
        current_seat = self._speech_queue[self._speech_idx]
        if p.seat != current_seat:
            raise EngineError("NOT_YOUR_TURN", "还没轮到你发言")
        content = (content or "").strip()
        if not content:
            raise EngineError("EMPTY_SPEECH", "发言内容不能为空")
        if len(content) > 500:
            raise EngineError("SPEECH_TOO_LONG", "发言最长 500 字")
        self._speeches.append({"seat": p.seat, "nickname": p.nickname,
                               "content": content, "day": self.day,
                               "pk": self.phase == Phase.PK_SPEECH})
        self._timeline_speech(p.seat, p.nickname, content,
                              pk=self.phase == Phase.PK_SPEECH)
        self._advance_speech(now)

    def _advance_speech(self, now: float) -> None:
        self._speech_idx += 1
        if self._speech_idx >= len(self._speech_queue):
            if self.phase == Phase.PK_SPEECH:
                self._votes = {}
                self._enter_phase(Phase.DAY_VOTE_PK, now)
            else:
                self._to_vote(now)
        else:
            self._enter_phase(self.phase, now)  # 重置该发言者 deadline

    def _to_vote(self, now: float) -> None:
        if self._speech_queue:
            self._next_speech_start = (self._speech_queue[-1] % len(self.players)) + 1
        self._votes = {}
        self._enter_phase(Phase.DAY_VOTE, now)

    def _tally(self, votes: dict[int, int | None]) -> list[tuple[int, int]]:
        counts: dict[int, int] = {}
        for target in votes.values():
            if target is not None:
                counts[target] = counts.get(target, 0) + 1
        if not counts:
            return []
        mx = max(counts.values())
        tops = sorted(s for s, c in counts.items() if c == mx)
        return [(s, mx) for s in tops]

    def _act_vote(self, p: EnginePlayer, target: int | None, now: float) -> None:
        self._require_phase(p, Phase.DAY_VOTE)
        if not p.can_vote:
            raise EngineError("NO_VOTE_RIGHT", "你已失去投票权")
        if p.user_id in self._votes:
            raise EngineError("ALREADY_ACTED", "已投票")
        if target is not None:
            if target == p.seat:
                raise EngineError("INVALID_VOTE_TARGET", "不能投自己")
            if not self._valid_target(target):
                raise EngineError("INVALID_VOTE_TARGET", "投票目标无效")
        self._votes[p.user_id] = target
        eligible = [q for q in self.players
                    if q.alive and q.can_vote and not q.escaped]
        if all(q.user_id in self._votes for q in eligible):
            self._resolve_vote(now)

    def _resolve_vote(self, now: float) -> None:
        self._last_votes = self._vote_detail()
        tally = self._tally(self._votes)
        if not tally:
            self._vote_history.append({"day": self.day, "kind": "vote",
                                       "detail": self._last_votes, "exiled": None})
            self._timeline_vote("vote", self._last_votes, None)
            self._emit("投票结束：全员弃票，无人出局")
            self._next_night(now)
            return
        if len(tally) > 1:
            self._vote_history.append({"day": self.day, "kind": "vote",
                                       "detail": self._last_votes, "exiled": None})
            self._timeline_vote("vote", self._last_votes, None)
            self._pk_seats = [s for s, _ in tally]
            self._pk_seats_orig = list(self._pk_seats)
            names = "、".join(f"{s} 号" for s in self._pk_seats)
            self._emit(f"平票！{names} 进入 PK")
            self._speech_queue = list(self._pk_seats)
            self._speech_idx = 0
            self._enter_phase(Phase.PK_SPEECH, now)
            return
        self._vote_history.append({"day": self.day, "kind": "vote",
                                   "detail": self._last_votes, "exiled": tally[0][0]})
        self._timeline_vote("vote", self._last_votes, tally[0][0])
        self._do_exile(tally[0][0], now)

    def _act_vote_pk(self, p: EnginePlayer, target: int | None, now: float) -> None:
        self._require_phase(p, Phase.DAY_VOTE_PK)
        if not p.can_vote:
            raise EngineError("NO_VOTE_RIGHT", "你已失去投票权")
        if p.seat in self._pk_seats:
            raise EngineError("NO_VOTE_RIGHT", "PK 玩家本轮不投票")
        if p.user_id in self._votes:
            raise EngineError("ALREADY_ACTED", "已投票")
        if target is not None and target not in self._pk_seats:
            raise EngineError("INVALID_VOTE_TARGET", "只能投 PK 玩家或弃票")
        self._votes[p.user_id] = target
        eligible = [q for q in self.players if q.alive and q.can_vote
                    and q.seat not in self._pk_seats and not q.escaped]
        if all(q.user_id in self._votes for q in eligible):
            self._resolve_pk_vote(now)

    def _resolve_pk_vote(self, now: float) -> None:
        self._last_votes = self._vote_detail()
        tally = self._tally(self._votes)
        if len(tally) == 1:
            self._vote_history.append({"day": self.day, "kind": "vote_pk",
                                       "detail": self._last_votes, "exiled": tally[0][0]})
            self._timeline_vote("vote_pk", self._last_votes, tally[0][0])
            self._do_exile(tally[0][0], now)
        else:
            self._vote_history.append({"day": self.day, "kind": "vote_pk",
                                       "detail": self._last_votes, "exiled": None})
            self._timeline_vote("vote_pk", self._last_votes, None)
            self._emit("PK 再次平票，本轮无人出局")
            self._pk_seats = []
            if self._pk_seats_orig:
                self._next_speech_start = (self._pk_seats_orig[-1] % len(self.players)) + 1
            self._next_night(now)

    def _do_exile(self, seat: int, now: float) -> None:
        p = self.players[seat - 1]
        self._pk_seats = []
        self._last_exiled_seat = None  # 仅作终局统计用途，不再参与发言轮转
        if p.role == Role.IDIOT and not p.idiot_revealed:
            p.idiot_revealed = True
            p.can_vote = False
            self._emit(f"{seat} 号是白痴！翻牌亮明身份免于出局，失去投票权")
            self._next_night(now)
            return
        p.alive = False
        p.death_cause = "exile"
        self._emit(f"{seat} 号被投票放逐出局")
        if self._check_win(now):
            return
        # 放逐的猎人可开枪（被放逐非毒死，满足开枪条件）
        if p.role == Role.HUNTER:
            self._pending_hunter = seat
            self._pending_after_hunter = ("last_words", seat)
            self._enter_phase(Phase.HUNTER_SHOT, now)
            return
        self._pending_last_words = [seat]
        self._last_words_then = "night"
        self._enter_phase(Phase.LAST_WORDS, now)

    # ---------- 遗言 ----------
    def submit_last_words(self, user_id: int, content: str, now: float) -> None:
        p = self._by_uid.get(user_id)
        if self.phase != Phase.LAST_WORDS:
            raise EngineError("WRONG_PHASE", "当前不是遗言阶段")
        if p is None or p.seat != self._pending_last_words[0]:
            raise EngineError("NOT_YOUR_TURN", "还没轮到你留遗言")
        content = (content or "").strip()
        if content:
            if len(content) > 500:
                raise EngineError("SPEECH_TOO_LONG", "遗言最长 500 字")
            self._speeches.append({"seat": p.seat, "nickname": p.nickname,
                                   "content": content, "day": self.day,
                                   "last_words": True})
            self._timeline_speech(p.seat, p.nickname, content, last_words=True)
        self._advance_last_words(now)

    def _advance_last_words(self, now: float) -> None:
        if self._pending_last_words:
            self._pending_last_words.pop(0)
        if self._pending_last_words:
            self._enter_phase(Phase.LAST_WORDS, now)
            return
        if self._last_words_then == "day":
            self._begin_day(now)   # 首夜遗言后进入白天发言
        else:
            self._next_night(now)  # 放逐遗言后进入下一夜

    # ---------- 跳过（女巫用药/猎人开枪/发言/遗言） ----------
    def skip(self, user_id: int, now: float) -> None:
        p = self._by_uid.get(user_id)
        if p is None:
            raise EngineError("NOT_IN_GAME", "你不在此对局中")
        if self.phase == Phase.NIGHT_WITCH and p.role == Role.WITCH \
                and p.user_id not in self._submitted:
            self._submitted.add(p.user_id)
            self._advance_if_phase_done(now)
        elif self.phase == Phase.HUNTER_SHOT and self._pending_hunter == p.seat:
            self._pending_hunter = None
            self._continue_after_hunter(now)
        elif self.phase in (Phase.DAY_SPEECH, Phase.PK_SPEECH) and p.alive \
                and self._speech_queue[self._speech_idx] == p.seat:
            self._advance_speech(now)
        elif self.phase == Phase.LAST_WORDS and self._pending_last_words \
                and p.seat == self._pending_last_words[0]:
            self._advance_last_words(now)
        else:
            raise EngineError("WRONG_PHASE", "当前没有可跳过的行动")

    def set_escaped(self, user_id: int, escaped: bool) -> None:
        p = self._by_uid.get(user_id)
        if p:
            p.escaped = escaped

    def _vote_detail(self) -> list[dict]:
        return [{"voter": self._by_uid[uid].seat, "target": target}
                for uid, target in self._votes.items()]

    def _next_night(self, now: float) -> None:
        if self._check_win(now):
            return
        self.day += 1
        self._begin_night(now)

    # ---------- 胜负 ----------
    def _check_win(self, now: float) -> bool:
        alive = [p for p in self.players if p.alive]
        wolves = [p for p in alive if p.role == Role.WEREWOLF]
        gods = [p for p in alive if p.role and ROLE_CAMPS[p.role] == "GOD"]
        peasants = [p for p in alive if p.role and ROLE_CAMPS[p.role] == "PEASANT"]
        if not wolves:
            self._finish(WIN_VILLAGER, now)
            return True
        if not gods or not peasants or len(wolves) >= len(alive) - len(wolves):
            self._finish(WIN_WEREWOLF, now)
            return True
        return False

    def _finish(self, winner: str, now: float) -> None:
        self._winner = winner
        self.phase = Phase.RESULT
        self.deadline = None
        label = "狼人阵营" if winner == WIN_WEREWOLF else "好人阵营"
        self._emit(f"游戏结束：{label}获胜")

    # ---------- 超时托管 ----------
    def check_timeouts(self, now: float) -> None:
        if self.phase == Phase.RESULT or self.deadline is None or now < self.deadline:
            return
        ph = self.phase
        if ph in (Phase.NIGHT_GUARD, Phase.NIGHT_WEREWOLF, Phase.NIGHT_SEER, Phase.NIGHT_WITCH):
            # 托管默认：守卫不守/预言家不验/女巫不用药；狼人全体超时随机刀
            # 刀口只在非狼阵营存活玩家中选择（托管刀不会自刀）
            if ph == Phase.NIGHT_WEREWOLF and self.night.wolf is None:
                targets = [p.seat for p in self.players
                           if p.alive and p.role != Role.WEREWOLF]
                if not targets:
                    targets = [p.seat for p in self.players if p.alive]
                self.night.wolf = self.rng.choice(targets)
            self._finish_night_phase(now)
        elif ph == Phase.DAWN:
            self._after_dawn(now)
        elif ph == Phase.DAY_SPEECH or ph == Phase.PK_SPEECH:
            self._advance_speech(now)
        elif ph == Phase.DAY_VOTE:
            self._resolve_vote(now)
        elif ph == Phase.DAY_VOTE_PK:
            self._resolve_pk_vote(now)
        elif ph == Phase.HUNTER_SHOT:
            self._pending_hunter = None
            self._continue_after_hunter(now)
        elif ph == Phase.LAST_WORDS:
            self._advance_last_words(now)

    def _continue_after_hunter(self, now: float) -> None:
        cont = self._pending_after_hunter
        self._pending_after_hunter = None
        if cont and cont[0] == "last_words":
            self._pending_last_words = [cont[1]]
            self._last_words_then = "night"
            self._enter_phase(Phase.LAST_WORDS, now)
            return
        if self._check_win(now):
            return
        if cont and cont[0] == "after_dawn":
            self._after_dawn(now)
        else:
            self._next_night(now)

    # ---------- 个人视角快照（spec §5.4 契约） ----------
    def snapshot(self, user_id: int) -> dict:
        me = self._by_uid.get(user_id)
        players_view = []
        for p in self.players:
            item = {"seat": p.seat, "nickname": p.nickname, "alive": p.alive,
                    "escaped": p.escaped}
            if p.idiot_revealed:
                item["idiot_revealed"] = True
            players_view.append(item)
        you: dict = {"seat": me.seat if me else None, "role": None, "can_vote": True,
                     "mates": None, "acting": False, "can": [], "speaking": False}
        if me and me.role:
            you["role"] = me.role.value
            you["can_vote"] = me.can_vote
            if me.role == Role.WEREWOLF:
                you["mates"] = [q.seat for q in self.players
                                if q.role == Role.WEREWOLF and q.seat != me.seat]
            if me.role == Role.SEER:
                you["checks"] = list(me.seer_checks)
            if me.role == Role.WITCH:
                you["witch"] = {"save": not me.witch_save_used,
                                "poison": not me.witch_poison_used}
                if self.phase == Phase.NIGHT_WITCH and not me.witch_save_used \
                        and self.night.wolf:
                    you["witch"]["victim"] = self.night.wolf
            # 阶段行动提示
            if self.phase == PHASE_OF_ROLE.get(me.role) and me.alive and not me.escaped \
                    and me.user_id not in self._submitted:
                you["acting"] = True
                if me.role == Role.WITCH:
                    can = []
                    witch_state = you.get("witch") or {}
                    if witch_state.get("save") and self.night.wolf is not None:
                        can.append("witch_save")
                    if witch_state.get("poison"):
                        can.append("witch_poison")
                    can.append("skip")
                    you["can"] = can
                else:
                    you["can"] = {
                        Role.GUARD: ["guard_protect"],
                        Role.WEREWOLF: ["werewolf_kill"],
                        Role.SEER: ["seer_check"],
                    }[me.role]
            if self.phase == Phase.HUNTER_SHOT and self._pending_hunter == me.seat:
                you["acting"] = True
                you["can"] = ["hunter_shot", "skip"]
            # 投票阶段：存活未托管且有投票权者下发投票行动
            if self.phase in (Phase.DAY_VOTE, Phase.DAY_VOTE_PK) and me.alive \
                    and not me.escaped and me.can_vote:
                already = me.user_id in self._votes
                is_pk_voter = (self.phase == Phase.DAY_VOTE_PK
                               and me.seat not in self._pk_seats)
                if not already and (self.phase == Phase.DAY_VOTE or is_pk_voter):
                    you["acting"] = True
                    you["can"] = ["vote_pk" if self.phase == Phase.DAY_VOTE_PK else "vote",
                                  "skip"]
        if self.phase in (Phase.DAY_SPEECH, Phase.PK_SPEECH) and self._speech_queue:
            you["speaking"] = (me is not None and me.alive
                               and self._speech_queue[self._speech_idx] == me.seat)
        snap = {
            "phase": self.phase.value,
            "day": self.day,
            "deadline": self.deadline,
            "players": players_view,
            "you": you,
            "log": self._events[-100:],
            "speeches": self._speeches[-100:],
            "votes": self._last_votes,
            "speaking_seat": (self._speech_queue[self._speech_idx]
                              if self.phase in (Phase.DAY_SPEECH, Phase.PK_SPEECH)
                              and self._speech_queue else None),
            "pk_seats": self._pk_seats,
            "last_words_seat": (self._pending_last_words[0]
                                if self.phase == Phase.LAST_WORDS
                                and self._pending_last_words else None),
        }
        if self.phase == Phase.RESULT:
            snap["winner"] = self._winner
            snap["reveal"] = self.reveal()
        return snap

    def reveal(self) -> list[dict]:
        return [{"seat": p.seat, "role": p.role.value if p.role else None, "alive": p.alive}
                for p in self.players]

    def public_history(self) -> dict:
        """公开对局过程（回放数据）：统一时间线按发生顺序交错；不含任何私有信息"""
        timeline = []
        for seq, item in enumerate(self._timeline, start=1):
            timeline.append({"seq": seq, **item})
        return {"events": self._events, "speeches": self._speeches,
                "votes": self._vote_history, "timeline": timeline}

    def winner(self) -> str | None:
        return self._winner

    def finished(self) -> bool:
        return self.phase == Phase.RESULT
