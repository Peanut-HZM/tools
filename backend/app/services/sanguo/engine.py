"""三国杀引擎（标准版 4 人身份局，服务端权威状态机）

- 回合六阶段由 tick(now) 驱动推进；需要响应（闪/杀/桃/无懈）时挂起 Pending，
  玩家 respond 提交；超时托管默认不响应。
- 时间统一由 update_now(now) 注入（room/测试调用），引擎内用 self._now。
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.services.sanguo.cards import DECK, Card, CardKind
from app.services.sanguo.heroes import Hero

logger = logging.getLogger(__name__)

ROLE_LORD = "LORD"
ROLE_LOYAL = "LOYAL"
ROLE_REBEL = "REBEL"
ROLE_SPY = "SPY"

RED_SUITS = ("♥", "♦")
BLACK_SUITS = ("♠", "♣")

WEAPON_RANGE = {"诸葛连弩": 1, "青釭剑": 1, "贯石斧": 2, "青龙偃月刀": 3}

PLAY_SECONDS = 120
DISCARD_SECONDS = 45
PENDING_SECONDS = 45


class SPhase(str, Enum):
    READY = "READY"
    JUDGE = "JUDGE"
    DRAW = "DRAW"
    PLAY = "PLAY"
    DISCARD = "DISCARD"
    END = "END"


class GState(str, Enum):
    TURN = "TURN"
    PENDING = "PENDING"
    GAME_OVER = "GAME_OVER"


class EngineError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class GPlayer:
    uid: int
    nickname: str
    seat: int
    hero: Hero
    role: str = ""
    hp: int = 0
    max_hp: int = 0
    hand: list[Card] = field(default_factory=list)
    equips: dict = field(default_factory=lambda: {"weapon": None, "armor": None,
                                                  "plus_horse": None, "minus_horse": None})
    judge_area: list[Card] = field(default_factory=list)
    alive: bool = True
    escaped: bool = False
    used_sha: bool = False
    rende_given: int = 0
    rende_healed: bool = False
    qingnang_used: bool = False
    lijian_used: bool = False
    skip_play: bool = False

    @property
    def is_lord(self) -> bool:
        return self.role == ROLE_LORD

    def weapon_name(self) -> str | None:
        return self.equips["weapon"].sub.split(":")[1] if self.equips["weapon"] else None

    def armor_name(self) -> str | None:
        return self.equips["armor"].sub.split(":")[1] if self.equips["armor"] else None


@dataclass
class Pending:
    kind: str
    seat: int
    need: int = 1
    answered: list[Card] = field(default_factory=list)
    deadline: float = 0.0
    source_seat: int | None = None
    card_name: str = ""
    damage: int = 1
    ctx: dict = field(default_factory=dict)


class SangouEngine:
    def __init__(self, players: list[tuple[int, str]], heroes: list[Hero],
                 seed: int | None = None):
        assert len(players) == 4 and len(heroes) == 4
        self.rng = random.Random(seed)
        roles = [ROLE_LORD, ROLE_LOYAL, ROLE_REBEL, ROLE_SPY]
        self.rng.shuffle(roles)
        shuffled_heroes = heroes.copy()
        self.rng.shuffle(shuffled_heroes)
        self.players: list[GPlayer] = []
        lord_idx = roles.index(ROLE_LORD)
        for i, ((uid, nick), role) in enumerate(zip(players, roles)):
            hero = shuffled_heroes[i]
            p = GPlayer(uid=uid, nickname=nick, seat=i + 1, hero=hero, role=role)
            p.max_hp = hero.max_hp + (1 if role == ROLE_LORD else 0)
            p.hp = p.max_hp
            self.players.append(p)
        self.lord_seat = lord_idx + 1
        self.deck: list[Card] = DECK.copy()
        self.rng.shuffle(self.deck)
        self.discard: list[Card] = []
        self._now = 0.0
        self.gstate = GState.GAME_OVER
        self.current_seat = self.lord_seat
        self.phase = SPhase.READY
        self.deadline: float | None = None
        self.pending: Pending | None = None
        self.winner: str | None = None
        self.turn_count = 0
        self.events: list[dict] = []
        self._event_seq = 0
        self.timeline: list[dict] = []
        self.ctx_aoe: dict | None = None
        self.ctx_dying: dict | None = None
        self.last_damage_card: Card | None = None

    # ---------- 基础 ----------
    def update_now(self, now: float) -> None:
        self._now = now

    def player_by_uid(self, uid: int) -> GPlayer:
        for p in self.players:
            if p.uid == uid:
                return p
        raise EngineError("NOT_IN_GAME", "你不在此对局中")

    def player_by_seat(self, seat: int) -> GPlayer:
        return self.players[seat - 1]

    def alive_players(self) -> list[GPlayer]:
        return [p for p in self.players if p.alive]

    def current_player(self) -> GPlayer:
        return self.player_by_seat(self.current_seat)

    def _emit(self, text: str) -> None:
        self._event_seq += 1
        self.events.append({"id": self._event_seq, "text": text})
        self.timeline.append({"kind": "event", "day": self.turn_count,
                              "phase": self.phase.value, "text": text,
                              "seq": self._event_seq})

    def _tl_speech(self, seat: int, nickname: str, content: str,
                   last_words: bool = False, pk: bool = False) -> None:
        self.timeline.append({"kind": "speech", "day": self.turn_count, "seat": seat,
                              "nickname": nickname, "text": content,
                              "last_words": last_words, "pk": pk})

    def _tl_vote(self, kind: str, detail: list[dict], exiled: int | None) -> None:
        self.timeline.append({"kind": "vote", "day": self.turn_count,
                              "vote_kind": kind, "detail": detail, "exiled": exiled})

    def events_since(self, event_id: int) -> list[dict]:
        return [e for e in self.events if e["id"] > event_id]

    def finished(self) -> bool:
        return self.gstate == GState.GAME_OVER

    def public_history(self) -> dict:
        timeline = [{"seq": i, **item} for i, item in enumerate(self.timeline, start=1)]
        return {"events": self.events, "timeline": timeline}

    def draw_cards(self, p: GPlayer, n: int) -> None:
        for _ in range(n):
            if not self.deck:
                if not self.discard:
                    break
                self.deck = self.discard.copy()
                self.rng.shuffle(self.deck)
                self.discard = []
            if self.deck:
                p.hand.append(self.deck.pop())

    def _to_discard(self, card: Card) -> None:
        if card and card.id > 0:
            self.discard.append(card)

    def _flip_judge(self) -> Card:
        if not self.deck:
            self.deck = self.discard.copy()
            self.rng.shuffle(self.deck)
            self.discard = []
        card = self.deck.pop()
        self.discard.append(card)
        return card

    # ---------- 距离 ----------
    def seat_distance(self, a: int, b: int) -> int:
        diff = abs(a - b)
        return min(diff, 4 - diff)

    def distance(self, a_seat: int, b_seat: int) -> int:
        if a_seat == b_seat:
            return 0
        pa, pb = self.player_by_seat(a_seat), self.player_by_seat(b_seat)
        d = self.seat_distance(a_seat, b_seat)
        if pa.equips["minus_horse"]:
            d = max(0, d - 1)
        if pb.equips["plus_horse"]:
            d += 1
        return d

    def attack_range(self, seat: int) -> int:
        p = self.player_by_seat(seat)
        return WEAPON_RANGE.get(p.weapon_name(), 1)

    def can_attack(self, a_seat: int, b_seat: int) -> bool:
        return a_seat != b_seat and self.distance(a_seat, b_seat) <= self.attack_range(a_seat)

    # ---------- 开局 ----------
    def start(self, now: float) -> None:
        self.update_now(now)
        for p in self.players:
            self.draw_cards(p, 4)
        self.gstate = GState.TURN
        lord = self.player_by_seat(self.lord_seat)
        self._emit(f"对局开始，主公是 {lord.seat} 号 {lord.nickname}")
        self._begin_turn(self.lord_seat, now)

    # ---------- 回合流转 ----------
    def _begin_turn(self, seat: int, now: float) -> None:
        self.current_seat = seat
        p = self.player_by_seat(seat)
        p.used_sha = False
        p.rende_given = 0
        p.rende_healed = False
        p.qingnang_used = False
        p.lijian_used = False
        p.skip_play = False
        self._set_phase(SPhase.READY, now)

    def _set_phase(self, phase: SPhase, now: float) -> None:
        self.phase = phase
        dur = {SPhase.PLAY: PLAY_SECONDS, SPhase.DISCARD: DISCARD_SECONDS}.get(phase)
        self.deadline = now + dur if dur else now
        if phase == SPhase.PLAY:
            self._emit(f"轮到 {self.current_seat} 号玩家出牌")

    def _next_alive_seat(self, seat: int) -> int:
        s = seat
        for _ in range(4):
            s = s % 4 + 1
            if self.player_by_seat(s).alive:
                return s
        return seat

    def tick(self, now: float) -> None:
        self.update_now(now)
        if self.gstate == GState.GAME_OVER:
            return
        if self.pending and now >= self.pending.deadline:
            self._resolve_pending_fail()
        if self.pending:
            return
        if now < (self.deadline or now):
            return
        ph = self.phase
        cur = self.current_player()
        if ph == SPhase.READY:
            self._enter_judge(now)
        elif ph == SPhase.JUDGE:
            self._resolve_judge_area(now)
        elif ph == SPhase.DRAW:
            self.draw_cards(cur, 2)
            self._emit(f"{cur.seat} 号摸两张牌")
            if cur.skip_play:
                cur.skip_play = False
                self._set_phase(SPhase.DISCARD, now)
            else:
                self._set_phase(SPhase.PLAY, now)
        elif ph == SPhase.PLAY:
            if not cur.alive:
                self._end_turn(now)
                return
            self._set_phase(SPhase.DISCARD, now)
        elif ph == SPhase.DISCARD:
            self._auto_discard(cur)
            self._end_turn(now)
        elif ph == SPhase.END:
            self._end_turn(now)

    def _enter_judge(self, now: float) -> None:
        self.phase = SPhase.JUDGE
        self._resolve_judge_area(now)

    def _resolve_judge_area(self, now: float) -> None:
        cur = self.current_player()
        while cur.judge_area:
            card = cur.judge_area.pop()
            judge = self._flip_judge()
            self._emit(f"{cur.seat} 号判定 {card.name}，判定牌 {judge.suit}{judge.point}")
            self.timeline.append({"kind": "judge", "day": self.turn_count,
                                  "for": card.name, "suit": judge.suit,
                                  "point": judge.point})
            if card.name == "乐不思蜀":
                if judge.suit not in RED_SUITS:
                    cur.skip_play = True
                    self._emit(f"{cur.seat} 号被乐不思蜀，将跳过出牌阶段")
            elif card.name == "闪电":
                if judge.suit == "♠" and 2 <= judge.point <= 9:
                    self._emit(f"{cur.seat} 号被闪电击中，受到 3 点雷电伤害")
                    self._damage(None, cur.seat, 3, "闪电")
                    if self.gstate == GState.GAME_OVER or self.pending:
                        return
                else:
                    nxt = self._next_alive_seat(cur.seat)
                    self.player_by_seat(nxt).judge_area.append(card)
                    self._emit(f"闪电移给 {nxt} 号")
        self._set_phase(SPhase.DRAW, now)

    def _auto_discard(self, p: GPlayer) -> None:
        limit = max(p.hp, 0)
        while len(p.hand) > limit:
            self._to_discard(p.hand.pop())

    def _end_turn(self, now: float) -> None:
        cur = self.current_player()
        if cur.alive and "闭月" in cur.hero.skills:
            self.draw_cards(cur, 1)
            self._emit(f"{cur.seat} 号闭月摸一张牌")
        nxt = self._next_alive_seat(cur.seat)
        self._begin_turn(nxt, now)

    # ---------- 出牌 ----------
    def _require_play_phase(self, uid: int) -> GPlayer:
        p = self.player_by_uid(uid)
        if self.gstate != GState.TURN:
            raise EngineError("GAME_OVER", "对局已结束")
        if self.pending is not None:
            raise EngineError("PENDING", "有待响应的结算")
        if self.phase != SPhase.PLAY:
            raise EngineError("WRONG_PHASE", "当前不是出牌阶段")
        if self.current_seat != p.seat:
            raise EngineError("NOT_YOUR_TURN", "当前不是你的回合")
        if not p.alive:
            raise EngineError("NOT_ALIVE", "你已出局")
        return p

    def _take_card(self, p: GPlayer, card_id: int) -> Card:
        for i, c in enumerate(p.hand):
            if c.id == card_id:
                return p.hand.pop(i)
        raise EngineError("NO_SUCH_CARD", "你没有这张牌")

    def next_phase(self, uid: int) -> None:
        p = self._require_play_phase(uid)
        self._set_phase(SPhase.DISCARD, self._now)

    def discard_to_limit(self, uid: int) -> None:
        p = self.player_by_uid(uid)
        if self.phase != SPhase.DISCARD or self.current_seat != p.seat:
            raise EngineError("WRONG_PHASE", "当前不是你的弃牌阶段")
        self._auto_discard(p)
        self.deadline = self._now  # 立即结束回合

    def play_card(self, uid: int, card_ids: list[int], targets: list[int] | None = None,
                  as_name: str | None = None) -> None:
        targets = targets or []
        p = self._require_play_phase(uid)
        if not card_ids:
            raise EngineError("NO_SUCH_CARD", "缺少牌")
        card = self._take_card(p, card_ids[0])
        name = as_name or card.name
        try:
            if name == "杀":
                self._use_sha(p, card, as_name, targets)
            elif name == "桃":
                if p.hp >= p.max_hp:
                    p.hand.append(card)
                    raise EngineError("FULL_HP", "体力已满")
                p.hp += 1
                self._to_discard(card)
                self._emit(f"{p.seat} 号使用桃，回复至 {p.hp} 体力")
            elif name == "决斗":
                self._use_duel(p, card, targets)
            elif name == "过河拆桥":
                self._use_dismantle(p, card, targets)
            elif name == "顺手牵羊":
                self._use_snatch(p, card, targets)
            elif name == "无中生有":
                self._wuxiao_gate_and_do(p, card, None, lambda: self._do_ex_nihilo(p, card))
            elif name == "南蛮入侵":
                self._wuxiao_gate_and_do(p, card, None,
                                         lambda: self._begin_aoe(p, card, "南蛮入侵", "nanman_sha"))
            elif name == "万箭齐发":
                self._wuxiao_gate_and_do(p, card, None,
                                         lambda: self._begin_aoe(p, card, "万箭齐发", "wanjian_dodge"))
            elif name == "桃园结义":
                self._to_discard(card)
                self._emit(f"{p.seat} 号使用桃园结义")
                for t in self.alive_players():
                    if t.hp < t.max_hp:
                        t.hp += 1
            elif name == "五谷丰登":
                self._wuxiao_gate_and_do(p, card, None, lambda: self._do_harvest(p, card))
            elif name == "乐不思蜀":
                if len(targets) != 1:
                    raise EngineError("TARGETS", "乐不思蜀需要恰好一个目标")
                self._wuxiao_gate_and_do(p, card, targets[0],
                                         lambda: self._do_indulgence(p, card, targets[0]))
            elif name == "闪电":
                self._to_discard(card)
                bolt = self._named_from_discard_or_self("闪电", card)
                p.judge_area.append(bolt)
                self._emit(f"{p.seat} 号使用闪电")
            elif card.kind == CardKind.EQUIP and as_name is None:
                self._do_equip(p, card)
            else:
                p.hand.append(card)
                raise EngineError("UNKNOWN_CARD", f"无法使用 {name}")
        except EngineError:
            p.hand.append(card)  # 非法使用退回手牌
            raise

    def _named_from_discard_or_self(self, name: str, fallback: Card) -> Card:
        for i in range(len(self.discard) - 1, -1, -1):
            if self.discard[i].name == name:
                return self.discard.pop(i)
        return fallback

    # ---------- 杀 ----------
    def _use_sha(self, p: GPlayer, card: Card, as_name: str | None,
                 targets: list[int]) -> None:
        if len(targets) != 1:
            raise EngineError("TARGETS", "杀需要恰好一个目标")
        if p.used_sha and "咆哮" not in p.hero.skills and p.weapon_name() != "诸葛连弩":
            raise EngineError("SHA_LIMIT", "出牌阶段只能使用一张杀")
        target = self.player_by_uid(targets[0])
        if not target.alive:
            raise EngineError("INVALID_TARGET", "目标已出局")
        if not self.can_attack(p.seat, target.seat):
            raise EngineError("OUT_OF_RANGE", "目标超出攻击范围")
        black = card.suit in BLACK_SUITS
        red_as_sha = as_name == "杀" and card.suit in RED_SUITS
        if (target.armor_name() == "仁王盾" and (black or red_as_sha)
                and p.weapon_name() != "青釭剑"):
            self._to_discard(card)
            self._emit(f"{target.seat} 号的仁王盾使黑色杀无效")
            return
        p.used_sha = True
        self._to_discard(card)
        self.last_damage_card = card
        need = 2 if "无双" in p.hero.skills else 1
        self._emit(f"{p.seat} 号对 {target.seat} 号使用杀")
        self._push_pending("dodge", target.seat, need=need,
                           source_seat=p.seat, card_name="杀", damage=1,
                           ctx={"qinggang": p.weapon_name() == "青釭剑"})
        self._trigger_bagua(target)

    def _trigger_bagua(self, target: GPlayer) -> None:
        if (self.pending and self.pending.kind == "dodge"
                and self.pending.seat == target.seat
                and target.armor_name() == "八卦阵"
                and not self.pending.ctx.get("qinggang")):
            judge = self._flip_judge()
            self._emit(f"{target.seat} 号八卦阵判定：{judge.suit}{judge.point}")
            self._to_discard(judge)
            if judge.suit in RED_SUITS:
                self.pending.answered.append(judge)
                self._emit(f"{target.seat} 号八卦阵视为打出闪")
                if len(self.pending.answered) >= self.pending.need:
                    self._resolve_pending_success()

    # ---------- 锦囊 ----------
    def _use_duel(self, p: GPlayer, card: Card, targets: list[int]) -> None:
        if len(targets) != 1:
            raise EngineError("TARGETS", "决斗需要恰好一个目标")
        t = self.player_by_uid(targets[0])
        if not t.alive:
            raise EngineError("INVALID_TARGET", "目标已出局")
        self._to_discard(card)
        self.last_damage_card = card
        need = 2 if "无双" in p.hero.skills else 1
        opp_need = 2 if "无双" in t.hero.skills else 1
        self._emit(f"{p.seat} 号对 {t.seat} 号使用决斗")
        self._push_pending("duel_sha", t.seat, need=need, source_seat=p.seat,
                           card_name="决斗", damage=1,
                           ctx={"next_seat": p.seat,
                                "opp_need": need, "self_need": opp_need})

    def _use_dismantle(self, p: GPlayer, card: Card, targets: list[int]) -> None:
        if len(targets) != 1:
            raise EngineError("TARGETS", "过河拆桥需要恰好一个目标")
        t = self.player_by_uid(targets[0])
        if not t.alive:
            raise EngineError("INVALID_TARGET", "目标已出局")
        self._wuxiao_gate_and_do(p, card, targets[0], lambda: self._do_dismantle(p, t))

    def _do_dismantle(self, p: GPlayer, t: GPlayer) -> None:
        if t.judge_area:
            c = t.judge_area.pop()
            self._to_discard(c)
            self._emit(f"{p.seat} 号拆掉 {t.seat} 号判定区的 {c.name}")
        elif any(t.equips.values()):
            key = next(k for k, v in t.equips.items() if v)
            c = t.equips[key]
            t.equips[key] = None
            self._to_discard(c)
            self._emit(f"{p.seat} 号拆掉 {t.seat} 号装备的 {c.name}")
        elif t.hand:
            c = t.hand.pop(self.rng.randrange(len(t.hand)))
            self._to_discard(c)
            self._emit(f"{p.seat} 号拆掉 {t.seat} 号一张手牌")
        else:
            self._emit(f"{t.seat} 号没有牌可拆")

    def _use_snatch(self, p: GPlayer, card: Card, targets: list[int]) -> None:
        if len(targets) != 1:
            raise EngineError("TARGETS", "顺手牵羊需要恰好一个目标")
        t = self.player_by_uid(targets[0])
        if not t.alive:
            raise EngineError("INVALID_TARGET", "目标已出局")
        if self.distance(p.seat, t.seat) > 1:
            raise EngineError("OUT_OF_RANGE", "顺手牵羊距离须为 1")
        self._wuxiao_gate_and_do(p, card, targets[0], lambda: self._do_snatch(p, t))

    def _do_snatch(self, p: GPlayer, t: GPlayer) -> None:
        if any(t.equips.values()):
            key = next(k for k, v in t.equips.items() if v)
            c = t.equips[key]
            t.equips[key] = None
            p.hand.append(c)
            self._emit(f"{p.seat} 号牵走 {t.seat} 号装备的 {c.name}")
        elif t.hand:
            c = t.hand.pop(self.rng.randrange(len(t.hand)))
            p.hand.append(c)
            self._emit(f"{p.seat} 号牵走 {t.seat} 号一张手牌")
        else:
            self._emit(f"{t.seat} 号没有牌可牵")

    def _do_ex_nihilo(self, p: GPlayer, card: Card) -> None:
        self._to_discard(card)
        self.draw_cards(p, 2)
        self._emit(f"{p.seat} 号无中生有摸两张牌")

    def _begin_aoe(self, p: GPlayer, card: Card, card_name: str, kind: str) -> None:
        self._to_discard(card)
        self.last_damage_card = card
        self._emit(f"{p.seat} 号使用 {card_name}")
        order = []
        s = p.seat
        for _ in range(3):
            s = self._next_alive_seat(s)
            order.append(s)
        self.ctx_aoe = {"source_seat": p.seat, "card_name": card_name,
                        "kind": kind, "order": order, "idx": 0}
        self._aoe_next()

    def _aoe_next(self) -> None:
        ctx = self.ctx_aoe
        if not ctx:
            return
        while ctx["idx"] < len(ctx["order"]):
            seat = ctx["order"][ctx["idx"]]
            target = self.player_by_seat(seat)
            if target.alive:
                need = 2 if "无双" in self.player_by_seat(ctx["source_seat"]).hero.skills else 1
                self._push_pending(ctx["kind"], seat, need=need,
                                   source_seat=ctx["source_seat"],
                                   card_name=ctx["card_name"], damage=1,
                                   ctx={"aoe": True})
                return
            ctx["idx"] += 1
        self.ctx_aoe = None

    def _do_harvest(self, p: GPlayer, card: Card) -> None:
        self._to_discard(card)
        shown = [self._flip_judge() for _ in self.alive_players()]
        names = "、".join(f"{c.name}" for c in shown)
        self._emit(f"{p.seat} 号使用五谷丰登，亮出：{names}")
        for i, t in enumerate(self.alive_players()):
            if i < len(shown):
                t.hand.append(shown[i])
                self._emit(f"{t.seat} 号获得 {shown[i].name}")

    def _do_indulgence(self, p: GPlayer, card: Card, target_seat: int) -> None:
        self._to_discard(card)
        t = self.player_by_seat(target_seat)
        bolt_like = self._named_from_discard_or_self("乐不思蜀", card)
        t.judge_area.append(bolt_like)
        self._emit(f"{p.seat} 号对 {t.seat} 号使用乐不思蜀")

    def _do_equip(self, p: GPlayer, card: Card) -> None:
        sub = card.sub or ""
        if sub.startswith("weapon:"):
            old = p.equips["weapon"]
            p.equips["weapon"] = card
        elif sub.startswith("armor:"):
            old = p.equips["armor"]
            p.equips["armor"] = card
        elif sub == "horse:+1":
            old = p.equips["plus_horse"]
            p.equips["plus_horse"] = card
        elif sub == "horse:-1":
            old = p.equips["minus_horse"]
            p.equips["minus_horse"] = card
        else:
            p.hand.append(card)
            raise EngineError("UNKNOWN_EQUIP", sub)
        if old:
            self._to_discard(old)
        self._emit(f"{p.seat} 号装备 {card.name}")

    # ---------- 技能动作 ----------
    def rende(self, uid: int, target_uid: int, card_ids: list[int]) -> None:
        p = self._require_play_phase(uid)
        if "仁德" not in p.hero.skills:
            raise EngineError("NO_SKILL", "你没有仁德")
        t = self.player_by_uid(target_uid)
        if t.uid == uid or not t.alive:
            raise EngineError("INVALID_TARGET", "仁德目标非法")
        cards = [self._take_card(p, cid) for cid in card_ids]
        t.hand.extend(cards)
        p.rende_given += len(cards)
        self._emit(f"{p.seat} 号仁德：将 {len(cards)} 张牌交给 {t.seat} 号")
        if p.rende_given >= 2 and not p.rende_healed and p.hp < p.max_hp:
            p.hp += 1
            p.rende_healed = True
            self._emit(f"{p.seat} 号仁德回复 1 点体力")

    def qingnang(self, uid: int, card_id: int, target_uid: int) -> None:
        p = self._require_play_phase(uid)
        if "青囊" not in p.hero.skills:
            raise EngineError("NO_SKILL", "你没有青囊")
        if p.qingnang_used:
            raise EngineError("SKILL_USED", "青囊每阶段限一次")
        t = self.player_by_uid(target_uid)
        if not t.alive or t.hp >= t.max_hp:
            raise EngineError("INVALID_TARGET", "目标无需回复")
        c = self._take_card(p, card_id)
        self._to_discard(c)
        t.hp += 1
        p.qingnang_used = True
        self._emit(f"{p.seat} 号青囊为 {t.seat} 号回复 1 点体力")

    def lijian(self, uid: int, card_id: int, male_a: int, male_b: int) -> None:
        p = self._require_play_phase(uid)
        if "离间" not in p.hero.skills:
            raise EngineError("NO_SKILL", "你没有离间")
        if p.lijian_used:
            raise EngineError("SKILL_USED", "离间每阶段限一次")
        a = self.player_by_uid(male_a)
        b = self.player_by_uid(male_b)
        if a.uid == b.uid or a.hero.gender != "male" or b.hero.gender != "male":
            raise EngineError("INVALID_TARGET", "离间需要两名男性角色")
        c = self._take_card(p, card_id)
        self._to_discard(c)
        p.lijian_used = True
        self._emit(f"{p.seat} 号离间：{a.seat} 号对 {b.seat} 号决斗")
        need = 2 if "无双" in p.hero.skills else 1
        self._push_pending("duel_sha", b.seat, need=need, source_seat=a.seat,
                           card_name="决斗", damage=1,
                           ctx={"next_seat": a.seat,
                                "opp_need": need, "self_need": 1})

    # ---------- 无懈门 ----------
    def _wuxiao_gate_and_do(self, p: GPlayer, card: Card, target_seat: int | None,
                            effect) -> None:
        if len(p.hand) and card.id in [c.id for c in p.hand]:
            p.hand = [c for c in p.hand if c.id != card.id]
            self._to_discard(card)
        self._emit(f"{p.seat} 号使用 {card.name}" + (f"（目标 {target_seat} 号）" if target_seat else ""))
        ask = [q.seat for q in self.alive_players() if q.uid != p.uid
               and any(c.name == "无懈可击" for c in q.hand)]
        if ask:
            effect_holder = {"effect": effect, "cancelled": False}
            self._push_pending("wuxiao", ask[0], need=1, source_seat=p.seat,
                               card_name=card.name, damage=0,
                               ctx={"ask_seats": ask, "holder": effect_holder})
            self.ctx_wuxiao_effect = effect_holder
        else:
            effect()

    # ---------- Pending ----------
    def _push_pending(self, kind: str, seat: int, need: int = 1,
                      source_seat: int | None = None, card_name: str = "",
                      damage: int = 1, ctx: dict | None = None) -> None:
        self.pending = Pending(kind=kind, seat=seat, need=need,
                               source_seat=source_seat, card_name=card_name,
                               damage=damage, ctx=ctx or {})
        self.pending.deadline = self._now + PENDING_SECONDS
        self.gstate = GState.PENDING

    def _required_card_names(self, kind: str) -> list[str]:
        return {
            "dodge": ["闪"], "wanjian_dodge": ["闪"],
            "duel_sha": ["杀"], "nanman_sha": ["杀"],
            "dying_peach": ["桃"], "wuxiao": ["无懈可击"],
        }.get(kind, ["闪"])

    def _can_answer(self, p: GPlayer, kind: str, c: Card) -> bool:
        need = self._required_card_names(kind)[0]
        if need == "闪":
            if c.name == "闪":
                return True
            if "龙胆" in p.hero.skills and c.name == "杀":
                return True
            return False
        if need == "杀":
            if c.name == "杀":
                return True
            if "龙胆" in p.hero.skills and c.name == "闪":
                return True
            if "武圣" in p.hero.skills and c.suit in RED_SUITS:
                return True
            return False
        if need == "桃":
            if c.name == "桃":
                return True
            if "急救" in p.hero.skills and c.suit in RED_SUITS:
                return True
            return False
        if need == "无懈可击":
            return c.name == "无懈可击"
        return False

    def respond(self, uid: int, card_ids: list[int]) -> None:
        p = self.player_by_uid(uid)
        if self.pending is None:
            raise EngineError("NO_PENDING", "当前没有待响应的请求")
        pend = self.pending
        if pend.kind == "wuxiao":
            if p.seat not in pend.ctx.get("ask_seats", []):
                raise EngineError("NOT_YOUR_RESPONSE", "你无需响应")
        elif pend.seat != p.seat:
            raise EngineError("NOT_YOUR_RESPONSE", "当前不需要你响应")
        cards = []
        for cid in card_ids:
            cards.append(self._take_card(p, cid))
        ok_cards = [c for c in cards if self._can_answer(p, pend.kind, c)]
        rejected = [c for c in cards if c not in ok_cards]
        for c in rejected:
            p.hand.append(c)
        if not ok_cards:
            raise EngineError("INVALID_RESPONSE",
                              f"响应需要 {'/'.join(self._required_card_names(pend.kind))}")
        for c in ok_cards:
            self._to_discard(c)
        pend.answered.extend(ok_cards)
        if len(pend.answered) < pend.need:
            pend.deadline = self._now + PENDING_SECONDS
            return
        self._resolve_pending_success()

    def _resolve_pending_success(self) -> None:
        pend = self.pending
        self.pending = None
        self.gstate = GState.TURN
        target = self.player_by_seat(pend.seat)
        if pend.kind == "dodge":
            self._emit(f"{pend.seat} 号打出闪")
        elif pend.kind == "duel_sha":
            self._emit(f"{pend.seat} 号打出杀")
            opponent = pend.ctx.get("next_seat")
            opp_need = pend.ctx.get("opp_need", 1)
            self._push_pending("duel_sha", opponent, need=opp_need,
                               source_seat=pend.source_seat, card_name="决斗",
                               damage=1, ctx={"next_seat": pend.seat,
                                              "opp_need": pend.ctx.get("self_need", 1)})
        elif pend.kind == "nanman_sha":
            self._emit(f"{pend.seat} 号打出杀")
            if pend.ctx.get("aoe"):
                self._aoe_advance()
        elif pend.kind == "wanjian_dodge":
            self._emit(f"{pend.seat} 号打出闪")
            if pend.ctx.get("aoe"):
                self._aoe_advance()
        elif pend.kind == "dying_peach":
            dying = self.player_by_seat(pend.ctx.get("dying", pend.seat))
            dying.hp += 1
            self._emit(f"{pend.seat} 号使用桃救助 {dying.seat} 号")
            if dying.hp <= 0:
                self._dying_next()
        elif pend.kind == "wuxiao":
            self._emit(f"{pend.seat} 号打出无懈可击，锦囊被抵消")
            holder = getattr(self, "ctx_wuxiao_effect", None)
            if holder:
                holder["cancelled"] = True

    def _aoe_advance(self) -> None:
        if not self.ctx_aoe:
            return
        self.ctx_aoe["idx"] += 1
        self._aoe_next()

    def _resolve_pending_fail(self) -> None:
        pend = self.pending
        self.pending = None
        self.gstate = GState.TURN
        target = self.player_by_seat(pend.seat)
        if pend.kind == "dodge":
            self._emit(f"{pend.seat} 号未打出闪")
            self._damage(pend.source_seat, pend.seat, pend.damage, "杀")
        elif pend.kind == "duel_sha":
            self._emit(f"{pend.seat} 号未打出杀")
            self._damage(pend.source_seat, pend.seat, 1, "决斗")
        elif pend.kind == "nanman_sha":
            self._emit(f"{pend.seat} 号未打出杀")
            self._damage(pend.source_seat, pend.seat, 1, "南蛮入侵")
            self._aoe_advance()
        elif pend.kind == "wanjian_dodge":
            self._emit(f"{pend.seat} 号未打出闪")
            self._damage(pend.source_seat, pend.seat, 1, "万箭齐发")
            self._aoe_advance()
        elif pend.kind == "dying_peach":
            self._dying_next()
        elif pend.kind == "wuxiao":
            self._emit(f"无人打出无懈可击，{pend.card_name} 生效")
            holder = getattr(self, "ctx_wuxiao_effect", None)
            if holder and not holder.get("cancelled"):
                effect = holder.get("effect")
                if effect:
                    effect()

    # ---------- 伤害 / 濒死 / 死亡 ----------
    def _damage(self, source_seat: int | None, seat: int, n: int, card_name: str,
                source_card: Card | None = None) -> None:
        p = self.player_by_seat(seat)
        if not p.alive:
            return
        p.hp -= n
        src = self.player_by_seat(source_seat) if source_seat else None
        src_name = f"{src.seat} 号" if src else "无来源"
        self._emit(f"{p.seat} 号受到 {n} 点伤害（来源 {src_name}，{card_name}）")
        if src and "奸雄" in p.hero.skills and source_card is not None:
            p.hand.append(source_card)
            self._emit(f"{p.seat} 号奸雄获得 {source_card.name}")
        if p.hp <= 0:
            self._start_dying(p, killer_seat=source_seat)

    def _start_dying(self, p: GPlayer, killer_seat: int | None = None) -> None:
        self._emit(f"{p.seat} 号濒死求桃")
        cur = self.current_seat
        order = []
        s = cur
        for _ in range(4):
            if self.player_by_seat(s).alive:
                order.append(s)
            s = s % 4 + 1
        self.ctx_dying = {"target": p.seat, "order": order, "idx": 0,
                          "killer_seat": killer_seat}
        self._dying_next()

    def _dying_next(self) -> None:
        ctx = self.ctx_dying
        if not ctx:
            return
        target = self.player_by_seat(ctx["target"])
        if target.hp > 0:
            self._emit(f"{target.seat} 号脱离濒死")
            return
        order = ctx["order"]
        while ctx["idx"] < len(order):
            seat = order[ctx["idx"]]
            asker = self.player_by_seat(seat)
            if asker.alive and not asker.escaped \
                    and any(self._can_answer(asker, "dying_peach", c) for c in asker.hand):
                self._push_pending("dying_peach", seat, need=1, card_name="桃",
                                   damage=0, ctx={"dying": target.seat,
                                                  "killer_seat": ctx.get("killer_seat")})
                return
            ctx["idx"] += 1
        self._die(target, ctx.get("killer_seat"))

    def _continue_dying(self, target: GPlayer) -> None:
        if target.hp <= 0:
            self._dying_next()
        else:
            self._emit(f"{target.seat} 号脱离濒死")

    def _die(self, p: GPlayer, killer_seat: int | None) -> None:
        p.alive = False
        p.hp = 0
        self._emit(f"{p.seat} 号阵亡（身份：{p.role}）")
        if p.is_lord:
            self._lord_punish_if_kills_loyal(killer_seat)
        if killer_seat is not None:
            killer = self.player_by_seat(killer_seat)
            if killer.alive and p.role == ROLE_REBEL:
                self.draw_cards(killer, 3)
                self._emit(f"{killer.seat} 号杀死反贼，摸三张牌")
        for c in p.hand + list(p.judge_area):
            self._to_discard(c)
        for k in list(p.equips.keys()):
            if p.equips[k]:
                self._to_discard(p.equips[k])
            p.equips[k] = None
        p.hand = []
        p.judge_area = []
        self._check_win()

    def _lord_punish_if_kills_loyal(self, killer_seat: int | None) -> None:
        # 由调用方在确认死者为忠臣且击杀者为主公时调用：主公弃全部牌
        pass

    def _check_win(self) -> None:
        alive = self.alive_players()
        lord_alive = any(p.is_lord for p in alive)
        rebels_alive = [p for p in alive if p.role == ROLE_REBEL]
        spies_alive = [p for p in alive if p.role == ROLE_SPY]
        if not lord_alive:
            if not rebels_alive and len(alive) == 1 and spies_alive:
                self.winner = ROLE_SPY
            else:
                self.winner = ROLE_REBEL
        elif not rebels_alive and not spies_alive:
            self.winner = ROLE_LORD
        if self.winner:
            self.gstate = GState.GAME_OVER
            self.pending = None
            label = {"LORD": "主公忠臣", "REBEL": "反贼", "SPY": "内奸"}[self.winner]
            self._emit(f"游戏结束：{label}获胜")

    # ---------- 视角 ----------
    def snapshot(self, uid: int) -> dict:
        me = self.player_by_uid(uid)
        players = []
        for p in self.players:
            role_visible = p.role
            if not p.is_lord and p.alive and p.uid != uid:
                role_visible = None
            if not p.alive:
                role_visible = p.role
            players.append({
                "seat": p.seat, "nickname": p.nickname, "hero": p.hero.name,
                "kingdom": p.hero.kingdom.value, "hp": p.hp, "max_hp": p.max_hp,
                "alive": p.alive, "role": role_visible,
                "hand_count": len(p.hand),
                "equips": [c.name for c in p.equips.values() if c],
                "judge": [c.name for c in p.judge_area],
            })
        pend = None
        if self.pending:
            pend = {"kind": self.pending.kind, "seat": self.pending.seat,
                    "need": self.pending.need, "have": len(self.pending.answered),
                    "card": self.pending.card_name}
        return {
            "phase": self.phase.value, "gstate": self.gstate.value,
            "turn_seat": self.current_seat, "turn_count": self.turn_count,
            "deadline": self.deadline, "pending": pend,
            "players": players,
            "you": {
                "seat": me.seat, "role": me.role, "hero": me.hero.name,
                "skills": list(me.hero.skills), "hp": me.hp, "max_hp": me.max_hp,
                "hand": [{"id": c.id, "name": c.name, "suit": c.suit,
                          "point": c.point, "kind": c.kind.value} for c in me.hand],
                "equips": {k: (v.name if v else None) for k, v in me.equips.items()},
                "judge": [c.name for c in me.judge_area],
                "can": self._action_hints(me),
            },
            "winner": self.winner,
            "deck_count": len(self.deck),
            "log": self.events[-60:],
        }

    def _action_hints(self, me: GPlayer) -> list[str]:
        if self.phase == SPhase.PLAY and self.current_seat == me.seat and me.alive:
            return ["play", "next_phase"]
        if self.phase == SPhase.DISCARD and self.current_seat == me.seat:
            return ["discard"]
        if self.pending and self.pending.seat == me.seat and not me.escaped:
            return ["respond"]
        return []
