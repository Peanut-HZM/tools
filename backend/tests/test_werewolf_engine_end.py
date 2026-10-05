"""胜负判定/个人视角快照/猎人开枪资格"""

from app.services.werewolf.engine import Phase
from app.services.werewolf.roles import Role
from tests.werewolf_helpers import DriveHelper, make_engine, seats_with_role

ROLES6 = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}


def test_villager_win_when_all_wolves_dead():
    # 狼人自刀两晚：第一晚狼 A 刀狼 B？自刀需存活狼提交，第二晚另一头狼死
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    wolves = seats_with_role(eng, Role.WEREWOLF)
    d = DriveHelper(eng)
    # 第一晚：狼 A 刀狼 B（自刀合法）→ B 死
    wolf_a = eng.players[wolves[0] - 1]
    eng.submit_action(wolf_a.user_id, "werewolf_kill", wolves[1], 1000.0)
    day = eng.day
    while not eng.finished() and eng.day == day:
        d._tick()  # 天亮 → 首夜遗言 → 发言 → 投票弃票 → 第二夜
    if not eng.finished():
        # 第二夜：狼 A 刀自己 → 全狼出局 → 好人胜
        d.run_to(Phase.NIGHT_WEREWOLF)
        eng.submit_action(wolf_a.user_id, "werewolf_kill", wolves[0], d.t)
        while not eng.finished():
            d._tick()
    assert eng.finished() and eng.winner() == "VILLAGER"


def test_werewolf_win_by_slaughter_edge_all_gods_dead():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    gods = seats_with_role(eng, Role.SEER) + seats_with_role(eng, Role.WITCH)
    d = DriveHelper(eng)
    # 两晚分别刀死两名神职 → 屠神 → 狼胜
    for target in gods:
        if eng.finished():
            break
        d.run_to(Phase.NIGHT_WEREWOLF)
        alive_wolf = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
        eng.submit_action(alive_wolf.user_id, "werewolf_kill", target, d.t)
        day = eng.day
        while not eng.finished() and eng.day == day:
            d._tick()
    while not eng.finished():
        d._tick()
    assert eng.finished() and eng.winner() == "WEREWOLF"


def test_snapshot_hides_other_roles_during_game():
    eng = make_engine(ROLES6)
    any_uid = eng.players[0].user_id
    snap = eng.snapshot(any_uid)
    for pp in snap["players"]:
        assert "role" not in pp  # 对局中不暴露他人身份
    assert snap["you"]["role"] is not None  # 自己身份可见
    assert eng.finished() is False


def test_snapshot_wolf_sees_mates_and_witch_state():
    eng = make_engine(ROLES6)
    wolf = next(p for p in eng.players if p.role == Role.WEREWOLF)
    snap = eng.snapshot(wolf.user_id)
    assert len(snap["you"]["mates"]) == 1  # 队友座位
    witch = next(p for p in eng.players if p.role == Role.WITCH)
    wsnap = eng.snapshot(witch.user_id)
    assert wsnap["you"]["witch"] == {"save": True, "poison": True}


def test_snapshot_result_reveals_all():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}
    eng = make_engine(roles)
    d = DriveHelper(eng)
    gods = seats_with_role(eng, Role.SEER) + seats_with_role(eng, Role.WITCH)
    for target in gods:
        if eng.finished():
            break
        d.run_to(Phase.NIGHT_WEREWOLF)
        alive_wolf = next(p for p in eng.players if p.role == Role.WEREWOLF and p.alive)
        eng.submit_action(alive_wolf.user_id, "werewolf_kill", target, d.t)
        day = eng.day
        while not eng.finished() and eng.day == day:
            d._tick()
    while not eng.finished():
        d._tick()
    assert eng.finished() and eng.winner() == "WEREWOLF"
    snap = eng.snapshot(eng.players[0].user_id)
    reveal = {r["seat"]: r["role"] for r in snap["reveal"]}
    assert len(reveal) == 6 and all(reveal.values())
    assert snap["winner"] == "WEREWOLF"


def test_hunter_cannot_shoot_when_poisoned():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    witch = eng.players[seats_with_role(eng, Role.WITCH)[0] - 1]
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WITCH)
    eng.submit_action(witch.user_id, "witch_poison", hunter_seat, d.t)
    # 狼人阶段已过（随机刀），天亮 → 猎人被毒不可开枪
    day = eng.day
    while eng.day == day and not eng.finished():
        d._tick()
    assert not eng.players[hunter_seat - 1].alive
    assert eng.phase != Phase.HUNTER_SHOT  # 被毒不可开枪


def test_hunter_can_shoot_when_killed_by_wolf():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    hunter_uid = eng.players[hunter_seat - 1].user_id
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", hunter_seat, d.t)
    d.run_to(Phase.HUNTER_SHOT)  # 女巫超时未救 → 天亮猎人被刀 → 开枪阶段
    eng.submit_action(hunter_uid, "hunter_shot", wolf.seat, d.t)
    assert not eng.players[wolf.seat - 1].alive
    assert eng.players[wolf.seat - 1].death_cause == "shot"


def test_hunter_shot_timeout_skips():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", hunter_seat, d.t)
    d.run_to(Phase.HUNTER_SHOT)
    d._tick()  # 开枪超时 → 弃枪继续
    assert eng.phase != Phase.HUNTER_SHOT
    assert eng.players[hunter_seat - 1].alive is False


def test_hunter_can_shoot_when_exiled():
    roles = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.HUNTER: 1, Role.VILLAGER: 1}
    eng = make_engine(roles)
    hunter_seat = seats_with_role(eng, Role.HUNTER)[0]
    hunter_uid = eng.players[hunter_seat - 1].user_id
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    d = DriveHelper(eng)
    d.run_to(Phase.NIGHT_WEREWOLF)
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, d.t)
    d.run_to(Phase.DAY_VOTE)
    # 全员投猎人（猎人本人弃票）
    for p in eng.players:
        if not p.alive:
            continue
        if p.seat == hunter_seat:
            eng.submit_action(p.user_id, "vote", None, d.t)
        else:
            eng.submit_action(p.user_id, "vote", hunter_seat, d.t)
    assert eng.phase == Phase.HUNTER_SHOT  # 被放逐可开枪
    target = next(p for p in eng.players if p.alive and p.seat != hunter_seat)
    eng.submit_action(hunter_uid, "hunter_shot", target.seat, d.t)
    assert not eng.players[target.seat - 1].alive
