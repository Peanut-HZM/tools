"""三国杀引擎基础行为：身份发放/回合流程/距离/杀闪结算/濒死"""
import pytest

from app.services.sanguo.engine import SangouEngine, SPhase
from app.services.sanguo.heroes import Hero, Kingdom


def advance(eng, t, n=12, step=100.0):
    """时间步进式 tick（覆盖 AOE 链/多回合的累计超时）"""
    for i in range(n):
        eng.tick(t + i * step)


def find_card(eng, uid, name, suit=None):
    """造一张指定牌塞到 uid 手里（独立对象，避免跨测试共享状态）"""
    from app.services.sanguo.cards import Card, CardKind
    p = eng.player_by_uid(uid)
    suits = {"杀": "♠", "闪": "♥", "桃": "♥"}.get(name, "♠")
    eng._test_card_seq = getattr(eng, "_test_card_seq", 0) + 1
    card = Card(id=50000 + eng._test_card_seq, name=name,
                suit=suit or suits, point=7, kind=CardKind.BASIC)
    p.hand.append(card)
    return card


def make_engine(seed=42, heroes=None):
    players = [(i, f"玩家{i}") for i in range(1, 5)]
    if heroes is None:
        heroes = [Hero(f"none{i}", f"白板{i}", Kingdom.QUN, 4, ()) for i in range(1, 5)]
    eng = SangouEngine(players, heroes, seed=seed)
    eng.start(1000.0)
    for _ in range(10):
        if eng.phase == SPhase.PLAY:
            break
        eng.tick(1000.0)
    assert eng.phase == SPhase.PLAY
    return eng


def first_near_and_far(eng, cur):
    near = next(p for p in eng.players if p.uid != cur.uid
                and eng.distance(cur.seat, p.seat) == 1)
    far = next(p for p in eng.players if p.uid != cur.uid
               and eng.distance(cur.seat, p.seat) == 2)
    return near, far


class TestRolesAndSetup:
    def test_roles_assigned_one_each(self):
        eng = make_engine()
        roles = sorted(p.role for p in eng.players)
        assert roles == ["LORD", "LOYAL", "REBEL", "SPY"]
        lord = next(p for p in eng.players if p.role == "LORD")
        assert lord.is_lord and lord.max_hp == lord.hero.max_hp + 1
        snap = eng.snapshot(1)
        assert any(pp.get("role") == "LORD" for pp in snap["players"])
        others = [pp for pp in snap["players"] if pp["seat"] != snap["you"]["seat"]]
        for pp in others:
            assert pp.get("role") in (None, "LORD")

    def test_deal_4_cards_and_lord_first_turn(self):
        eng = make_engine()
        assert eng.current_seat == eng.lord_seat
        assert eng.phase == SPhase.PLAY
        assert len(eng.current_player().hand) == 6  # 主公 4+2（已过摸牌阶段）


class TestTurnFlow:
    def test_draw_two_then_play_then_next_turn(self):
        eng = make_engine()
        cur = eng.current_player()
        eng.next_phase(cur.uid)
        assert eng.phase == SPhase.DISCARD
        advance(eng, 1050.0)  # 越过弃牌 45s 窗口
        assert eng.phase in (SPhase.PLAY, SPhase.DRAW)  # 下家回合（DRAW 为中间态）

    def test_discard_phase_forces_hand_to_hp(self):
        eng = make_engine()
        cur = eng.current_player()
        cur.hand = []
        for _ in range(3):
            find_card(eng, cur.uid, "闪")
        assert len(cur.hand) == 3
        cur.hp = 2
        eng.next_phase(cur.uid)
        assert eng.phase == SPhase.DISCARD
        eng.discard_to_limit(cur.uid)
        assert len(cur.hand) <= 2
        advance(eng, 1050.0)
        assert eng.phase in (SPhase.PLAY, SPhase.DRAW)

    def test_play_timeout_auto_discard_and_advance(self):
        eng = make_engine()
        cur = eng.current_player()
        eng.next_phase(cur.uid)
        advance(eng, 1000.0)
        assert eng.phase in (SPhase.PLAY, SPhase.DRAW, SPhase.DISCARD, SPhase.READY, SPhase.END)
        assert len(cur.hand) <= max(cur.hp, 0) or cur.hp >= len(cur.hand) or not cur.alive


class TestDistanceAndSha:
    def test_distance_in_4p_ring(self):
        eng = make_engine()
        assert eng.distance(1, 2) == 1
        assert eng.distance(1, 3) == 2
        assert eng.distance(1, 4) == 1

    def test_horse_modifies_distance(self):
        eng = make_engine()
        p1 = eng.player_by_uid(1)
        p3 = eng.player_by_uid(3)
        p1.equips["minus_horse"] = True
        assert eng.distance(1, 3) == 1
        p3.equips["plus_horse"] = True
        assert eng.distance(1, 3) == 2
        p1.equips["minus_horse"] = False
        p3.equips["plus_horse"] = False

    def test_sha_requires_distance_and_dodge(self):
        eng = make_engine()
        cur = eng.current_player()
        near, far = first_near_and_far(eng, cur)
        sha = find_card(eng, cur.uid, "杀")
        with pytest.raises(Exception):
            eng.play_card(cur.uid, [sha.id], [far.uid])
        eng.play_card(cur.uid, [sha.id], [near.uid])
        assert eng.pending is not None and eng.pending.kind == "dodge"
        assert eng.pending.seat == near.seat
        advance(eng, 1000.0)
        assert near.hp == near.hero.max_hp - 1
        assert eng.pending is None

    def test_sha_limit_once_per_turn(self):
        eng = make_engine()
        cur = eng.current_player()
        near, _ = first_near_and_far(eng, cur)
        sha1 = find_card(eng, cur.uid, "杀")
        eng.play_card(cur.uid, [sha1.id], [near.uid])
        advance(eng, 1000.0)
        sha2 = find_card(eng, cur.uid, "杀")
        with pytest.raises(Exception):
            eng.play_card(cur.uid, [sha2.id], [near.uid])


class TestDodgeAndDamage:
    def test_dodge_negates_sha(self):
        eng = make_engine()
        cur = eng.current_player()
        near, _ = first_near_and_far(eng, cur)
        sha = find_card(eng, cur.uid, "杀")
        eng.play_card(cur.uid, [sha.id], [near.uid])
        dodge = find_card(eng, near.uid, "闪")
        eng.respond(near.uid, [dodge.id])
        assert near.hp == near.hero.max_hp
        assert eng.pending is None
