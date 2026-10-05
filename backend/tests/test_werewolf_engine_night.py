"""狼人杀引擎夜晚流程测试：发牌/守卫/狼人/预言家/女巫/天亮结算"""
import pytest

from app.services.werewolf.boards import GameSettings
from app.services.werewolf.engine import EngineError, Phase
from app.services.werewolf.roles import Role
from tests.werewolf_helpers import DriveHelper, make_engine, seats_with_role

# 6人板：2狼 预 女巫 2民
ROLES = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}


def pass_seer(eng, t=1041.0):
    """用超时跳过预言家阶段（测试不关心查验时）"""
    if eng.phase == Phase.NIGHT_SEER:
        eng.check_timeouts(t)

def test_roles_dealt_and_private_role_message():
    eng = make_engine(ROLES)
    assert eng.phase in (Phase.NIGHT_GUARD, Phase.NIGHT_WEREWOLF)  # 无守卫则直接狼人
    roles = sorted(p.role for p in eng.players)
    assert roles.count(Role.WEREWOLF) == 2 and roles.count(Role.SEER) == 1
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    mates = [m for m in eng.drain_private(wolf.user_id) if m["kind"] == "role"]
    assert mates and len(mates[0]["mates"]) == 1  # 知道队友座位


def test_night_phase_order_guard_before_wolf():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng = make_engine(roles=roles)
    assert eng.phase == Phase.NIGHT_GUARD
    guard = seats_with_role(eng, Role.GUARD)[0]
    eng.submit_action(eng.players[guard - 1].user_id, "guard_protect", guard, 1000.0)  # 可守自己
    assert eng.phase == Phase.NIGHT_WEREWOLF


def test_guard_cannot_protect_same_target_two_nights():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng = make_engine(roles=roles)
    guard_uid = eng.players[seats_with_role(eng, Role.GUARD)[0] - 1].user_id
    wolf_uid = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1].user_id
    witch_uid = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1].user_id
    # 第一夜：守 1，狼刀 3，女巫救 3（避免死员干扰，3 为村民或预言家都能被救）
    eng.submit_action(guard_uid, "guard_protect", 1, 1000.0)
    eng.submit_action(wolf_uid, "werewolf_kill", 3, 1000.0)
    pass_seer(eng)
    eng.submit_action(witch_uid, "witch_save", 3, 1042.0)
    # 推进到第二夜（白天全部超时托管）
    DriveHelper(eng).to_next_night()
    assert eng.day == 2
    with pytest.raises(EngineError):
        eng.submit_action(guard_uid, "guard_protect", 1, 2000.0)  # 连守同一人被拒


def test_wolf_kill_resolved_at_dawn():
    eng = make_engine(ROLES)
    wolf_uid = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1].user_id
    eng.submit_action(wolf_uid, "werewolf_kill", 2, 1000.0)
    witch_uid = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1].user_id
    eng.drain_private(witch_uid)
    # 女巫不救，毒 6 号（先用超时跳过预言家阶段）
    pass_seer(eng)
    eng.submit_action(witch_uid, "witch_poison", 6, 1042.0)
    eng.check_timeouts(1999.0)
    assert not eng.players[1].alive
    assert eng.players[1].death_cause in ("wolf", "poison", "milk")
    assert not eng.players[5].alive


def test_witch_sees_victim_only_with_save_available():
    eng = make_engine(ROLES)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    wolf_uid = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1].user_id
    eng.submit_action(wolf_uid, "werewolf_kill", 2, 1000.0)
    pass_seer(eng)  # 推进到女巫阶段才会私发刀口
    victim_msgs = [m for m in eng.drain_private(witch.user_id) if m["kind"] == "witch_victim"]
    assert victim_msgs and victim_msgs[0]["target"] == 2
    eng.submit_action(witch.user_id, "witch_save", 2, 1042.0)
    # 推进到第二夜：解药已用，不再告知刀口
    DriveHelper(eng).to_next_night()
    wolf2 = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
    eng.submit_action(wolf2.user_id, "werewolf_kill", 3, 3000.0)
    assert not [m for m in eng.drain_private(witch.user_id) if m["kind"] == "witch_victim"]


def test_witch_one_potion_per_night():
    eng = make_engine(ROLES)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    wolf_uid = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1].user_id
    eng.submit_action(wolf_uid, "werewolf_kill", 2, 1000.0)
    pass_seer(eng)
    eng.submit_action(witch.user_id, "witch_save", 2, 1042.0)
    with pytest.raises(EngineError):
        eng.submit_action(witch.user_id, "witch_poison", 5, 1043.0)


def test_witch_self_rescue_settings():
    for mode, allowed in (("never", False), ("always", True)):
        eng = make_engine(ROLES, settings=GameSettings(witch_self_rescue=mode))
        wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
        witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
        eng.submit_action(wolf.user_id, "werewolf_kill", witch.seat, 1000.0)
        pass_seer(eng)
        if allowed:
            eng.submit_action(witch.user_id, "witch_save", witch.seat, 1042.0)
        else:
            with pytest.raises(EngineError):
                eng.submit_action(witch.user_id, "witch_save", witch.seat, 1042.0)
            eng.check_timeouts(1999.0)


def test_milk_through_death_when_guarded_and_saved():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng = make_engine(roles=roles)  # 默认 witch_guard_conflict=True
    guard = eng.players[seats_with_role(eng, Role.GUARD)[0] - 1]
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(guard.user_id, "guard_protect", 6, 1000.0)
    eng.submit_action(wolf.user_id, "werewolf_kill", 6, 1000.0)
    pass_seer(eng)
    eng.submit_action(witch.user_id, "witch_save", 6, 1042.0)
    eng.check_timeouts(1999.0)
    assert not eng.players[5].alive and eng.players[5].death_cause == "milk"


def test_guard_saves_wolf_kill():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.GUARD: 1, Role.VILLAGER: 1}
    eng = make_engine(roles=roles)
    guard = eng.players[seats_with_role(eng, Role.GUARD)[0] - 1]
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(guard.user_id, "guard_protect", 6, 1000.0)
    eng.submit_action(wolf.user_id, "werewolf_kill", 6, 1000.0)
    pass_seer(eng)
    eng.check_timeouts(2082.0)  # 女巫超时不用药
    assert eng.players[5].alive
