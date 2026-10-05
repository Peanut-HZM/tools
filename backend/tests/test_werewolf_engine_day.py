"""白天流程：发言轮转/投票/平票PK/放逐遗言/白痴翻牌"""
import pytest

from app.services.werewolf.engine import EngineError, Phase
from app.services.werewolf.roles import Role
from tests.werewolf_helpers import DriveHelper, make_engine, seats_with_role

ROLES6 = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}


def kill3_and_to_day_speech(seed=42):
    """构造：狼刀 3 号，女巫不救（超时），推进到白天发言"""
    eng = make_engine(ROLES6, seed=seed)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    DriveHelper(eng).run_to(Phase.DAY_SPEECH)
    return eng


def to_day_vote(seed=42):
    """构造：推进到白天投票阶段"""
    eng = kill3_and_to_day_speech(seed=seed)
    d = DriveHelper(eng)
    d.run_to(Phase.DAY_VOTE)
    return eng, d


def test_speech_starts_after_first_death():
    eng = kill3_and_to_day_speech()
    assert eng._speech_queue[0] == 4  # 3 号死亡 → 从 4 号开始发言


def test_speech_order_and_submit_advances():
    eng = kill3_and_to_day_speech()
    speaker_uid = eng.players[eng._speech_queue[0] - 1].user_id
    eng.submit_speech(speaker_uid, "我是好人", 1500.0)
    assert eng._speeches[-1]["content"] == "我是好人"
    assert eng._speech_queue[eng._speech_idx] != 4  # 前进到下一位


def test_non_speaker_cannot_speak():
    eng = kill3_and_to_day_speech()
    other = eng.players[eng._speech_queue[1] - 1]
    with pytest.raises(EngineError):
        eng.submit_speech(other.user_id, "抢话", 1500.0)


def test_vote_exiles_and_last_words():
    eng, d = to_day_vote()
    # 除 2 号外全部投 2 号，2 号本人弃票（所有存活玩家都须表态）
    for p in eng.players:
        if p.alive and p.seat != 2:
            eng.submit_action(p.user_id, "vote", 2, d.t)
        elif p.alive:
            eng.submit_action(p.user_id, "vote", None, d.t)
    assert eng.phase == Phase.LAST_WORDS
    assert eng._pending_last_words == [2]
    assert not eng.players[1].alive and eng.players[1].death_cause == "exile"
    assert eng._last_votes and all(v["target"] == 2 for v in eng._last_votes
                                   if v["target"] is not None)


def test_vote_cannot_target_self():
    eng, d = to_day_vote()
    voter = next(p for p in eng.players if p.alive and p.seat != 2)
    with pytest.raises(EngineError):
        eng.submit_action(voter.user_id, "vote", voter.seat, d.t)


def test_tie_vote_goes_to_pk_then_exile():
    eng, d = to_day_vote(seed=7)
    # 4/5/6 各投 1/2/弃，PK 候选人 1、2 弃票 → 1 与 2 各 1 票平票 PK
    for p in eng.players:
        if not p.alive or p.seat == 3:
            continue
        if p.seat == 4:
            eng.submit_action(p.user_id, "vote", 1, d.t)
        elif p.seat == 5:
            eng.submit_action(p.user_id, "vote", 2, d.t)
        else:
            eng.submit_action(p.user_id, "vote", None, d.t)
    assert eng.phase == Phase.PK_SPEECH
    assert sorted(eng._pk_seats) == [1, 2]
    # PK 发言全部超时 → PK 投票：4/5 投 1、6 弃 → 1 号出局
    d.run_to(Phase.DAY_VOTE_PK)
    non_pk = [p for p in eng.players if p.alive and p.seat not in (1, 2)]
    for i, p in enumerate(non_pk):
        eng.submit_action(p.user_id, "vote_pk", 1 if i < 2 else None, d.t)
    assert not eng.players[0].alive and eng.players[0].death_cause == "exile"


def test_pk_vote_only_pk_seats_valid_target():
    eng, d = to_day_vote(seed=7)
    for p in eng.players:
        if not p.alive or p.seat == 3:
            continue
        if p.seat == 4:
            eng.submit_action(p.user_id, "vote", 1, d.t)
        elif p.seat == 5:
            eng.submit_action(p.user_id, "vote", 2, d.t)
        else:
            eng.submit_action(p.user_id, "vote", None, d.t)
    d.run_to(Phase.DAY_VOTE_PK)
    pker = next(p for p in eng.players if p.seat == 1)
    with pytest.raises(EngineError):
        eng.submit_action(pker.user_id, "vote_pk", 1, d.t)  # PK 者无投票权


def test_second_tie_nobody_exiled():
    eng, d = to_day_vote(seed=7)
    for p in eng.players:
        if not p.alive or p.seat == 3:
            continue
        if p.seat == 4:
            eng.submit_action(p.user_id, "vote", 1, d.t)
        elif p.seat == 5:
            eng.submit_action(p.user_id, "vote", 2, d.t)
        else:
            eng.submit_action(p.user_id, "vote", None, d.t)
    d.run_to(Phase.DAY_VOTE_PK)
    non_pk = [p for p in eng.players if p.alive and p.seat not in (1, 2)]
    # 1 票投 1、1 票投 2、1 弃 → 再平票 → 无人出局
    for p, t in zip(non_pk, [1, 2, None]):
        eng.submit_action(p.user_id, "vote_pk", t, d.t)
    assert all(p.alive for p in eng.players if p.seat in (1, 2))
    d.to_next_night()  # 有界推进到下一夜，避免死循环
    assert eng.day == 2


def test_idiot_flips_on_exile_survives_loses_vote():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.IDIOT: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    d = DriveHelper(eng)
    idiot_seat = seats_with_role(eng, Role.IDIOT)[0]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    d.run_to(Phase.DAY_VOTE)
    for p in eng.players:
        if not p.alive:
            continue
        if p.seat != idiot_seat:
            eng.submit_action(p.user_id, "vote", idiot_seat, d.t)
        else:
            eng.submit_action(p.user_id, "vote", None, d.t)  # 白痴本人弃票
    idiot = eng.players[idiot_seat - 1]
    assert idiot.alive and idiot.idiot_revealed and not idiot.can_vote
    # 无人出局，直接进入下一夜
    d.to_next_night()
    assert eng.day == 2


def test_idiot_dies_to_night_kill():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.IDIOT: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    idiot_seat = seats_with_role(eng, Role.IDIOT)[0]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", idiot_seat, 1000.0)
    t = 1000.0
    for _ in range(6):  # 预言家/女巫/天亮逐阶段超时推进
        t += 100
        eng.check_timeouts(t)
    assert not eng.players[idiot_seat - 1].alive  # 夜刀正常死亡，不触发翻牌


def test_speech_starts_after_exiled_next_day():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng = make_engine(roles, seed=42)
    d = DriveHelper(eng)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    guard = eng.players[seats_with_role(eng, Role.GUARD)[0] - 1]
    # 第一夜：守卫守 6 号 → 狼刀 3 号 → 预言家/女巫超时 → 3 号死
    d.run_to(Phase.NIGHT_GUARD)
    eng.submit_action(guard.user_id, "guard_protect", 6, d.t)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, d.t)
    d.run_to(Phase.DAY_VOTE)
    # 白天放逐 2 号（2 号本人弃票）
    for p in eng.players:
        if not p.alive:
            continue
        if p.seat == 2:
            eng.submit_action(p.user_id, "vote", None, d.t)
        else:
            eng.submit_action(p.user_id, "vote", 2, d.t)
    # 第二夜：守卫守 1 号 → 狼刀 1 号被守护 → 平安夜
    d.run_to(Phase.NIGHT_GUARD)
    eng.submit_action(guard.user_id, "guard_protect", 1, d.t)
    d.run_to(Phase.NIGHT_WEREWOLF)
    wolf2 = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
    eng.submit_action(wolf2.user_id, "werewolf_kill", 1, d.t)
    # 第二天发言从被放逐者（2 号）下一位开始；3 号夜死被跳过 → 4 号
    d.run_to(Phase.DAY_SPEECH)
    assert eng.day == 2
    assert eng._speech_queue[0] == 4
