"""三国杀完整对局集成验收：引擎直驱随机局到终局 + 房间结算落库回放"""
import random

import pytest

from app.services.sanguo.engine import SangouEngine
from app.services.sanguo.heroes import HEROES
from app.services.sanguo.record import get_record, save_game_record
from app.services.sanguo.room import SanguoRoom

HERO_LIST = list(HEROES.values())


def random_act(eng: SangouEngine, rng: random.Random, max_rounds=600):
    """随机合法策略驱动一局到终局"""
    rounds = 0
    while not eng.finished() and rounds < max_rounds:
        rounds += 1
        t = rounds * 100.0
        eng.update_now(t)
        for p in list(eng.players):
            if not p.alive:
                continue
            snap = eng.snapshot(p.uid)
            if snap["gstate"] == "GAME_OVER":
                return rounds
            you = snap["you"]
            can = you.get("can") or []
            if snap["phase"] == "PLAY" and snap["turn_seat"] == you["seat"] \
                    and "play" in can:
                # 随机出一张合法手牌（尽量选单目标/无目标的直接使用）
                hand = you["hand"]
                if hand:
                    card = rng.choice(hand)
                    others = [pp["seat"] for pp in snap["players"]
                              if pp["alive"] and pp["seat"] != you["seat"]]
                    targets = [rng.choice(others)] if others else []
                    try:
                        eng.play_card(p.uid, [card["id"]], targets)
                    except Exception:
                        try:
                            eng.next_phase(p.uid)
                        except Exception:
                            pass
                else:
                    try:
                        eng.next_phase(p.uid)
                    except Exception:
                        pass
            elif snap["phase"] == "DISCARD" and snap["turn_seat"] == you["seat"]:
                try:
                    eng.discard_to_limit(p.uid)
                except Exception:
                    pass
            if snap.get("pending") and snap["pending"]["seat"] == you["seat"]:
                # 有待响应：尝试用第一张可响应牌；否则超时托管
                hand = you["hand"]
                if hand:
                    try:
                        eng.respond(p.uid, [hand[0]["id"]])
                    except Exception:
                        pass
        eng.tick(t + 90.0)
    return rounds


@pytest.mark.parametrize("seed", list(range(42, 50)))
def test_random_games_complete(seed):
    """8 局随机对局：必终局、winner 合法、无死锁"""
    rng = random.Random(seed)
    players = [(i, f"玩家{i}") for i in range(1, 5)]
    heroes = rng.sample(HERO_LIST, 4)
    eng = SangouEngine(players, heroes, seed=seed)
    eng.start(1000.0)
    rounds = random_act(eng, rng)
    assert eng.finished(), f"seed={seed} 未终局（{rounds} 轮）"
    assert eng.winner() in ("LORD", "REBEL", "SPY")
    h = eng.public_history()
    assert h["timeline"]  # 过程时间线非空


def test_room_finish_saves_record_with_replay(mgr_tmp=None):
    """房间驱动到终局 → build_record_summary 含 timeline → 落库可查询"""
    rng = random.Random(7)
    room = SanguoRoom("777888", 1, rng.sample(HERO_LIST, 4))
    saved = {}
    room.on_finished = lambda: saved.update({"summary": room.build_record_summary()})
    for uid in range(1, 5):
        room.add_member(uid, f"玩家{uid}")
    room.start(1, now=1000.0)
    rng = random.Random(9)
    t = 1000.0
    for _ in range(1200):
        if room.engine.finished():
            break
        t += 30.0  # 每步 30s
        eng = room.engine
        eng.update_now(t)
        # 随机出牌/响应（当前回合者出牌；被请求者响应；否则超时托管）
        for p in list(eng.players):
            if not p.alive:
                continue
            snap = eng.snapshot(p.uid)
            if snap["phase"] == "PLAY" and snap["turn_seat"] == snap["you"]["seat"]:
                hand = snap["you"]["hand"]
                # 优先攻击牌（避免无伤害僵局），否则随机
                attacks = [c for c in hand if c["name"] in ("杀", "决斗")]
                card = rng.choice(attacks or hand) if hand else None
                if card:
                    others = [pp["seat"] for pp in snap["players"]
                              if pp["alive"] and pp["seat"] != snap["you"]["seat"]]
                    try:
                        eng.play_card(p.uid, [card["id"]],
                                      [rng.choice(others)] if others else [])
                    except Exception:
                        pass
            pend = snap.get("pending")
            if pend and pend["seat"] == snap["you"]["seat"] and p.hand:
                try:
                    eng.respond(p.uid, [p.hand[0].id])
                except Exception:
                    pass
        room.tick(t)
    assert room.engine.finished(), (
        f"房间驱动未终局 turns={room.engine.turn_count} "
        f"alive={[(p.seat, p.alive, p.hp) for p in room.engine.players]} "
        f"pending={room.engine.pending} dying={room.engine.ctx_dying} "
        f"roles={[(p.seat, p.role) for p in room.engine.players]}")
    summary = room.build_record_summary()
    assert summary["winner"] in ("LORD", "REBEL", "SPY")
    assert summary["timeline"]["timeline"]
    rid = save_game_record(summary)
    detail = get_record(rid)
    assert detail["record"]["timeline"]["timeline"]
    assert detail["record"]["winner"] in ("LORD", "REBEL", "SPY")
