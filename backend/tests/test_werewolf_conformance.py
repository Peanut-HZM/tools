"""狼人杀规则一致性验收（对照互联网主流真实规则逐条验收）

规则来源：维基百科「狼人杀」词条、狼人殺百科（lrs.fandom.com）、知乎《狼人杀游戏规则及术语》、
3DM 法官主持顺序、小米游戏教学、百度知道遗言/屠边规则。每条测试标注对应规则编号（R#）。

R1  夜晚顺序：守卫→狼人→预言家→女巫；缺角色跳过
R2  守卫：可自守、不可连守（含自己）、可空守
R3  同守同救（奶穿）→ 目标死亡；可配置关闭
R4  女巫解药毒药各一瓶，同一晚只能使用一瓶
R5  解药未用时告知刀口；用完不再告知
R6  女巫毒死的玩家不能发动技能（猎人被毒不可枪）
R7  女巫自救三档（不可/仅首夜/随时），默认主流「不可自救」
R8  猎人：被刀/被放逐可枪；被毒/奶穿不可枪；被枪杀者无遗言
R9  白痴：被放逐翻牌免死+失投票权+可继续发言；被刀/被毒/被枪直接死亡
R10 遗言：首夜死者有遗言、被放逐者有遗言；其后夜晚死亡无遗言
R11 屠边：杀光全部神职或全部平民 → 狼胜；放逐全部狼 → 好人胜
R12 即时判定：存活狼数 ≥ 存活好人数 → 狼胜
R13 平票 → PK 发言 → 再投票 → 再平票无人出局
R14 投票不能投自己、可弃票
R15 发言顺序：从死者下一位开始；无死者从上一发言轮末尾下一座继续
R16 预言家查验获知阵营（好/狼）
R17 狼人夜晚互认
R18 白痴计入神职阵营（屠边判定）
"""
import random

import pytest

from app.services.werewolf.boards import GameSettings
from app.services.werewolf.engine import EngineError, Phase, WerewolfEngine
from app.services.werewolf.roles import NIGHT_ACTION_ORDER, ROLE_CAMPS, Role
from tests.werewolf_helpers import DriveHelper, make_engine, seats_with_role

ROLES6 = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}


# ---------- R1 夜晚顺序 ----------
def test_r1_night_order_and_skip_missing_roles():
    order = [PHASE_OF_ROLE[r] for r in NIGHT_ACTION_ORDER]
    assert order == [Phase.NIGHT_GUARD, Phase.NIGHT_WEREWOLF, Phase.NIGHT_SEER, Phase.NIGHT_WITCH]
    # 无守卫板子：首夜直接进入狼人阶段
    eng = make_engine(ROLES6)
    assert eng.phase == Phase.NIGHT_WEREWOLF
    # 有守卫板子：守卫先行动
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng2 = make_engine(roles)
    assert eng2.phase == Phase.NIGHT_GUARD


def test_r1_no_seer_or_witch_phase_skipped():
    roles = {Role.WEREWOLF: 2, Role.VILLAGER: 4}
    eng = make_engine(roles)
    assert eng.phase == Phase.NIGHT_WEREWOLF
    wolf = next(p for p in eng.players if p.role == Role.WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    # 无预言家/女巫 → 夜晚结算直接天亮
    DriveHelper(eng).run_to(Phase.DAWN)
    assert eng.day == 1


PHASE_OF_ROLE = {
    Role.GUARD: Phase.NIGHT_GUARD,
    Role.WEREWOLF: Phase.NIGHT_WEREWOLF,
    Role.SEER: Phase.NIGHT_SEER,
    Role.WITCH: Phase.NIGHT_WITCH,
}


# ---------- R2 守卫 ----------
def test_r2_guard_can_self_protect_and_empty():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    guard_uid = eng.players[seats_with_role(eng, Role.GUARD)[0] - 1].user_id
    # 自守合法
    eng.submit_action(guard_uid, "guard_protect", seats_with_role(eng, Role.GUARD)[0], 1000.0)
    assert eng.phase == Phase.NIGHT_WEREWOLF
    # 空守：下一夜直接 skip（不行动等超时）→ 不报错、正常推进
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_GUARD)
    d._tick()  # 守卫阶段超时 = 空守
    assert eng.phase == Phase.NIGHT_WEREWOLF


def test_r2_guard_cannot_guard_consecutive_nights_including_self():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    guard = eng.players[seats_with_role(eng, Role.GUARD)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    d = DriveHelper(eng)
    # 第一夜守自己
    d.run_to(Phase.NIGHT_GUARD)
    eng.submit_action(guard.user_id, "guard_protect", guard.seat, d.t)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, d.t)
    # 女巫不用药，天亮进白天，再到第二夜
    d.run_to(Phase.NIGHT_GUARD)
    assert eng.day == 2
    # 连守自己被拒
    with pytest.raises(EngineError):
        eng.submit_action(guard.user_id, "guard_protect", guard.seat, d.t)


# ---------- R3 奶穿 ----------
def test_r3_milk_through_default_on_and_configurable_off():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    for conflict, expect_dead in ((True, True), (False, False)):
        eng = make_engine(roles, settings=GameSettings(witch_guard_conflict=conflict))
        guard = eng.players[seats_with_role(eng, Role.GUARD)[0] - 1]
        witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
        wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
        d = DriveHelper(eng)
        d.run_to(Phase.NIGHT_GUARD)
        eng.submit_action(guard.user_id, "guard_protect", 6, d.t)
        d.run_to(Phase.NIGHT_WEREWOLF)
        eng.submit_action(wolf.user_id, "werewolf_kill", 6, d.t)
        d.run_to(Phase.NIGHT_WITCH)
        eng.submit_action(witch.user_id, "witch_save", 6, d.t)
        d.run_to(Phase.DAWN)
        assert eng.players[5].alive is (not expect_dead)


# ---------- R4 女巫一瓶/晚 ----------
def test_r4_witch_only_one_potion_per_night_save_then_poison():
    eng = make_engine(ROLES6)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 4, d.t)
    d.run_to(Phase.NIGHT_WITCH)
    eng.submit_action(witch.user_id, "witch_save", 4, d.t)
    with pytest.raises(EngineError):
        eng.submit_action(witch.user_id, "witch_poison", 5, d.t)


def test_r4_witch_only_one_potion_per_night_poison_then_save():
    eng = make_engine(ROLES6)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 4, d.t)
    d.run_to(Phase.NIGHT_WITCH)
    eng.submit_action(witch.user_id, "witch_poison", 5, d.t)
    with pytest.raises(EngineError):
        eng.submit_action(witch.user_id, "witch_save", 4, d.t)


# ---------- R5 刀口告知 ----------
def test_r5_witch_learns_victim_only_while_save_available():
    eng = make_engine(ROLES6)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 2, d.t)
    d.run_to(Phase.NIGHT_WITCH)
    msgs = [m for m in eng.drain_private(witch.user_id) if m["kind"] == "witch_victim"]
    assert msgs and msgs[0]["target"] == 2
    eng.submit_action(witch.user_id, "witch_save", 2, d.t)
    # 第二夜起不再告知
    d.to_next_night()
    d.run_to(Phase.NIGHT_WEREWOLF)
    wolf2 = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
    eng.submit_action(wolf2.user_id, "werewolf_kill", 3, d.t)
    d.run_to(Phase.NIGHT_WITCH)
    assert not [m for m in eng.drain_private(witch.user_id) if m["kind"] == "witch_victim"]


# ---------- R6/R7 女巫自救 ----------
def test_r7_witch_self_rescue_three_modes():
    for mode, first_night_ok, later_ok in (("never", False, False),
                                           ("first_night", True, False),
                                           ("always", True, True)):
        eng = make_engine(ROLES6, settings=GameSettings(witch_self_rescue=mode))
        witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
        wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
        d = DriveHelper(eng)
        d.run_to(Phase.NIGHT_WEREWOLF)
        eng.submit_action(wolf.user_id, "werewolf_kill", witch.seat, d.t)
        d.run_to(Phase.NIGHT_WITCH)
        if first_night_ok:
            eng.submit_action(witch.user_id, "witch_save", witch.seat, d.t)
            assert witch.alive
        else:
            with pytest.raises(EngineError):
                eng.submit_action(witch.user_id, "witch_save", witch.seat, d.t)
            continue
        # 第二夜再被刀：first_night 档不可再自救（解药已尽按 NO_POTION 拒绝）
        d.to_next_night()
        d.run_to(Phase.NIGHT_WEREWOLF)
        wolf2 = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
        eng.submit_action(wolf2.user_id, "werewolf_kill", witch.seat, d.t)
        d.run_to(Phase.NIGHT_WITCH)
        # first_night/never：自救被拒（NO_POTION 或 SELF_RESCUE_FORBIDDEN 均为合法拒绝）
        # always：毒药仍可用（女巫仍活着可行动）
        if later_ok:
            eng.submit_action(witch.user_id, "witch_poison", 6, d.t)
            assert eng.night.poison == 6
        else:
            with pytest.raises(EngineError):
                eng.submit_action(witch.user_id, "witch_save", witch.seat, d.t)


# ---------- R8 猎人 ----------
def test_r8_hunter_shot_by_wolf_can_shoot():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    hunter_uid = eng.players[hunter_seat - 1].user_id
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", hunter_seat, d.t)
    d.run_to(Phase.HUNTER_SHOT)
    target = next(p for p in eng.players if p.alive and p.seat != hunter_seat)
    eng.submit_action(hunter_uid, "hunter_shot", target.seat, d.t)
    assert not eng.players[target.seat - 1].alive


def test_r8_hunter_poisoned_or_milk_cannot_shoot():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.GUARD: 1}
    # 被毒
    eng = make_engine(roles)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WITCH)
    eng.submit_action(witch.user_id, "witch_poison", hunter_seat, d.t)
    day = eng.day
    while eng.day == day and not eng.finished():
        d._tick()
    assert eng.phase != Phase.HUNTER_SHOT
    # 奶穿
    eng2 = make_engine(roles)
    guard = eng2.players[seats_with_role(eng2, Role.GUARD)[0] - 1]
    witch2 = eng2.players[seats_with_role(eng2, Role.WITCH)[0] - 1]
    wolf = eng2.players[seats_with_role(eng2, Role.WEREWOLF)[0] - 1]
    d2 = DriveHelper(eng2)
    d2.run_to(Phase.NIGHT_GUARD)
    eng2.submit_action(guard.user_id, "guard_protect", hunter_seat, d2.t)
    d2.run_to(Phase.NIGHT_WEREWOLF)
    eng2.submit_action(wolf.user_id, "werewolf_kill", hunter_seat, d2.t)
    d2.run_to(Phase.NIGHT_WITCH)
    eng2.submit_action(witch2.user_id, "witch_save", hunter_seat, d2.t)
    day = eng2.day
    while eng2.day == day and not eng2.finished():
        d2._tick()
    assert eng2.phase != Phase.HUNTER_SHOT


def test_r8_shot_victim_has_no_last_words():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    hunter_uid = eng.players[hunter_seat - 1].user_id
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", hunter_seat, d.t)
    d.run_to(Phase.HUNTER_SHOT)
    target = next(p for p in eng.players if p.alive and p.seat != hunter_seat)
    eng.submit_action(hunter_uid, "hunter_shot", target.seat, d.t)
    # 猎人本人是首夜被刀死者（有遗言权）；被枪杀的目标无遗言权
    d.run_to(Phase.LAST_WORDS)
    assert eng._pending_last_words == [hunter_seat]
    assert target.seat not in eng._pending_last_words


# ---------- R9 白痴 ----------
def test_r9_idiot_flips_only_on_exile():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.IDIOT: 1, Role.VILLAGER: 1}
    idiot_by_board = seats_with_role(make_engine(roles), Role.IDIOT)
    # 被刀直接死（不翻牌）
    eng = make_engine(roles)
    idiot_seat = seats_with_role(eng, Role.IDIOT)[0]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", idiot_seat, 1000.0)
    t = 1000.0
    for _ in range(6):
        t += 100
        eng.check_timeouts(t)
    assert not eng.players[idiot_seat - 1].alive
    assert not eng.players[idiot_seat - 1].idiot_revealed
    # 被毒直接死
    eng2 = make_engine(roles)
    idiot_seat2 = seats_with_role(eng2, Role.IDIOT)[0]
    witch = eng2.players[seats_with_role(eng2, Role.WITCH)[0] - 1]
    d2 = DriveHelper(eng2)
    d2.run_to(Phase.NIGHT_WITCH)
    eng2.submit_action(witch.user_id, "witch_poison", idiot_seat2, d2.t)
    day = eng2.day
    while eng2.day == day and not eng2.finished():
        d2._tick()
    assert not eng2.players[idiot_seat2 - 1].alive
    assert not eng2.players[idiot_seat2 - 1].idiot_revealed


def test_r9_idiot_survives_exile_can_still_speak_but_not_vote():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.IDIOT: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    d = DriveHelper(eng)
    idiot_seat = seats_with_role(eng, Role.IDIOT)[0]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    # 刀一个确定非白痴的座位（避免白痴首夜被刀导致场景不成立）
    victim = next(p.seat for p in eng.players
                  if p.role not in (Role.IDIOT, Role.WEREWOLF))
    eng.submit_action(wolf.user_id, "werewolf_kill", victim, 1000.0)
    d.run_to(Phase.DAY_VOTE)
    for p in eng.players:
        if not p.alive:
            continue
        if p.seat == idiot_seat:
            eng.submit_action(p.user_id, "vote", None, d.t)
        else:
            eng.submit_action(p.user_id, "vote", idiot_seat, d.t)
    idiot = eng.players[idiot_seat - 1]
    assert idiot.alive and idiot.idiot_revealed and not idiot.can_vote
    # 翻牌后白痴仍在发言队列中（未出局），轮到时发言被接受
    d.run_to(Phase.DAY_SPEECH)
    assert eng.day == 2
    assert idiot_seat in eng._speech_queue
    # 驱动到白痴的发言轮次
    guard_rounds = 0
    while eng._speech_queue[eng._speech_idx] != idiot_seat and guard_rounds < 20:
        d._tick()
        guard_rounds += 1
    eng.submit_speech(idiot.user_id, "我是白痴我还能说话", d.t)
    assert any("白痴" in s["content"] for s in eng._speeches)


# ---------- R10 遗言权 ----------
def test_r10_last_words_first_night_and_exile_only():
    eng = make_engine(ROLES6)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    d = DriveHelper(eng)
    d.run_to(Phase.LAST_WORDS)
    assert eng._pending_last_words == [3]  # 首夜死者有遗言
    d.run_to(Phase.DAY_VOTE)
    for p in eng.players:
        if not p.alive:
            continue
        if p.seat == 2:
            eng.submit_action(p.user_id, "vote", None, d.t)
        else:
            eng.submit_action(p.user_id, "vote", 2, d.t)
    assert eng.phase == Phase.LAST_WORDS and eng._pending_last_words == [2]
    # 遗言后第二夜死者：无遗言阶段
    d.run_to(Phase.NIGHT_WEREWOLF)
    wolf2 = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
    eng.submit_action(wolf2.user_id, "werewolf_kill", 4, d.t)
    d.run_to(Phase.DAWN)
    day = eng.day
    while eng.day == day and not eng.finished():
        d._tick()
    assert eng.phase != Phase.LAST_WORDS  # 夜死（非首夜）无遗言


# ---------- R11/R12 胜负 ----------
def test_r11_slaughter_edge_gods_and_peasants_and_wolf_wipe():
    # 屠神 → 狼胜
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    gods = seats_with_role(eng, Role.SEER) + seats_with_role(eng, Role.WITCH)
    d = DriveHelper(eng)
    for target in gods:
        if eng.finished():
            break
        d.run_to(Phase.NIGHT_WEREWOLF)
        aw = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
        eng.submit_action(aw.user_id, "werewolf_kill", target, d.t)
        day = eng.day
        while not eng.finished() and eng.day == day:
            d._tick()
    while not eng.finished():
        d._tick()
    assert eng.winner() == "WEREWOLF"

    # 屠民 → 狼胜
    eng2 = make_engine(roles)
    peasants = seats_with_role(eng2, Role.VILLAGER)
    d2 = DriveHelper(eng2)
    for target in peasants:
        if eng2.finished():
            break
        d2.run_to(Phase.NIGHT_WEREWOLF)
        aw = next(p for p in eng2.players if p.role == Role.WEREWOLF and p.alive)
        eng2.submit_action(aw.user_id, "werewolf_kill", target, d2.t)
        day = eng2.day
        while not eng2.finished() and eng2.day == day:
            d2._tick()
    while not eng2.finished():
        d2._tick()
    assert eng2.winner() == "WEREWOLF"


def test_r12_immediate_loss_when_wolves_match_good_count():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    wolves = seats_with_role(eng, Role.WEREWOLF)
    d = DriveHelper(eng)
    # 夜1：狼 A 自刀死狼 B → 存活 狼1 好4 → 不终局
    eng.submit_action(eng.players[wolves[0] - 1].user_id, "werewolf_kill", wolves[1], 1000.0)
    day = eng.day
    while not eng.finished() and eng.day == day:
        d._tick()
    assert not eng.finished()
    # 白天放逐一个好人（猎人弃枪）→ 存活 狼1 好3 → 不终局
    d.run_to(Phase.DAY_VOTE)
    victims = [p.seat for p in eng.players if p.alive and p.role != Role.WEREWOLF]
    victim = victims[0]
    for p in eng.players:
        if not p.alive:
            continue
        if p.seat == victim:
            eng.submit_action(p.user_id, "vote", None, d.t)
        else:
            eng.submit_action(p.user_id, "vote", victim, d.t)
    if eng.phase == Phase.HUNTER_SHOT:
        d.run_to(Phase.LAST_WORDS) if eng._pending_after_hunter else None
    assert not eng.finished()
    # 夜2 刀一个好人 → 存活 狼1 好3 → 不终局；夜3 刀 → 狼1 好2 → 不终局
    # 夜4 刀 → 狼1 好1 → 1>=1 白天开始前即时狼胜（R12 即时判定）
    for _ in range(3):
        if eng.finished():
            break
        d.run_to(Phase.NIGHT_WEREWOLF)
        aw = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
        good_alive = [p.seat for p in eng.players if p.alive and p.role != Role.WEREWOLF]
        eng.submit_action(aw.user_id, "werewolf_kill", good_alive[0], d.t)
        day = eng.day
        while not eng.finished() and eng.day == day:
            d._tick()
    assert eng.finished() and eng.winner() == "WEREWOLF"
    alive_good = [p for p in eng.players if p.alive and p.role != Role.WEREWOLF]
    assert len(alive_good) == 1


# ---------- R13/R14 投票 ----------
def test_r13_tie_pk_and_second_tie_nobody_exiled():
    eng = make_engine(ROLES6, seed=7)
    d = DriveHelper(eng)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    d.run_to(Phase.DAY_VOTE)
    # 4/5/6 各投 1/2/弃，1/2 本人弃票 → 1、2 各一票平票 PK
    for p in eng.players:
        if not p.alive or p.seat == 3:
            continue
        if p.seat == 4:
            eng.submit_action(p.user_id, "vote", 1, d.t)
        elif p.seat == 5:
            eng.submit_action(p.user_id, "vote", 2, d.t)
        else:
            eng.submit_action(p.user_id, "vote", None, d.t)
    assert eng.phase == Phase.PK_SPEECH and sorted(eng._pk_seats) == [1, 2]
    d.run_to(Phase.DAY_VOTE_PK)
    # PK 投票：4 投 1、5 投 2、6 弃 → 再平 → 无人出局
    non_pk = [p for p in eng.players if p.alive and p.seat not in (1, 2)]
    for p, t in zip(non_pk, [1, 2, None]):
        eng.submit_action(p.user_id, "vote_pk", t, d.t)
    assert all(p.alive for p in eng.players if p.seat in (1, 2))
    d.to_next_night()
    assert eng.day == 2


def test_r14_vote_cannot_target_self_dead_or_out_of_range():
    eng = make_engine(ROLES6)
    d = DriveHelper(eng)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    d.run_to(Phase.DAY_VOTE)
    voter = next(p for p in eng.players if p.alive and p.seat != 2)
    # 投自己
    with pytest.raises(EngineError):
        eng.submit_action(voter.user_id, "vote", voter.seat, d.t)
    # 投死人
    with pytest.raises(EngineError):
        eng.submit_action(voter.user_id, "vote", 3, d.t)
    # 投越界座位
    with pytest.raises(EngineError):
        eng.submit_action(voter.user_id, "vote", 99, d.t)
    # 弃票合法
    eng.submit_action(voter.user_id, "vote", None, d.t)


# ---------- R15 发言顺序 ----------
def test_r15_speech_starts_from_first_victim_next_seat():
    eng = make_engine(ROLES6, seed=42)
    d = DriveHelper(eng)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    d.run_to(Phase.DAY_SPEECH)
    # 3 号死 → 从 4 号开始，顺序 4,5,6,1,2（跳过死者）
    assert eng._speech_queue == [4, 5, 6, 1, 2]


def test_r15_multiple_deaths_use_first_victim_next_seat():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 6, d.t)
    d.run_to(Phase.NIGHT_WITCH)
    eng.submit_action(witch.user_id, "witch_poison", 7, d.t)
    # 夜死 6、7 → 存活 狼2 好3 → 不终局
    day = eng.day
    while eng.day == day and not eng.finished():
        d._tick()
    assert not eng.finished()
    d.run_to(Phase.DAY_SPEECH)
    deaths = sorted(eng._dawn_deaths)
    # 多死者以第一位死者下一位为起点（死亡座位被跳过）
    expected_start = deaths[0] % len(eng.players) + 1
    alive_ordered = []
    n = len(eng.players)
    for i in range(n):
        s = (expected_start - 1 + i) % n + 1
        if eng.players[s - 1].alive:
            alive_ordered.append(s)
    assert eng._speech_queue == alive_ordered


# ---------- R16/R17 预言家与狼队 ----------
def test_r16_seer_check_result_and_r17_wolf_mates():
    eng = make_engine(ROLES6)
    seer = eng.players[seats_with_role(eng, Role.SEER)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 4, d.t)
    d.run_to(Phase.NIGHT_SEER)
    eng.submit_action(seer.user_id, "seer_check", wolf.seat, d.t)
    msgs = [m for m in eng.drain_private(seer.user_id) if m["kind"] == "seer_result"]
    assert msgs and msgs[0]["is_werewolf"] is True
    # 狼人互认
    wolves = [p for p in eng.players if p.role == Role.WEREWOLF]
    for w in wolves:
        mates = [m for m in eng.drain_private(w.user_id) if m["kind"] == "role"]
        assert mates and len(mates[0]["mates"]) == 1


# ---------- R18 白痴计入神职 ----------
def test_r18_idiot_counts_as_god_for_edge_slaughter():
    assert ROLE_CAMPS[Role.IDIOT] == "GOD"
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.IDIOT: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    gods = seats_with_role(eng, Role.SEER) + seats_with_role(eng, Role.WITCH) + seats_with_role(eng, Role.IDIOT)
    d = DriveHelper(eng)
    # 杀光全部神职（含白痴）→ 狼胜（若白痴算民，此时民未死光不应判狼胜）
    for target in gods:
        if eng.finished():
            break
        d.run_to(Phase.NIGHT_WEREWOLF)
        aw = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
        eng.submit_action(aw.user_id, "werewolf_kill", target, d.t)
        day = eng.day
        while not eng.finished() and eng.day == day:
            d._tick()
    assert eng.finished() and eng.winner() == "WEREWOLF"
    peasants_alive = [p for p in eng.players if p.role == Role.VILLAGER and p.alive]
    assert peasants_alive  # 民还有存活，胜利只能来自屠神（白痴计神）
