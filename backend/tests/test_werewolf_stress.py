"""全板子随机对局压测验收：每个预置板子 + 自定义板子跑多局随机对局，
断言：必定在有限轮内终局（无死锁）、终局 winner 合法、全员角色已发放。"""
import random

import pytest

from app.services.werewolf.boards import PRESET_BOARDS, GameSettings, validate_board
from app.services.werewolf.engine import EngineError, Phase, WerewolfEngine
from app.services.werewolf.roles import Role
from tests.werewolf_helpers import DriveHelper


def random_drive(eng: WerewolfEngine, rng: random.Random, max_rounds=400):
    """随机策略驱动一局到终局；返回 (终局, 轮数)。随机玩家做合法行动。"""
    rounds = 0
    while not eng.finished() and rounds < max_rounds:
        rounds += 1
        for p in eng.players:
            if not p.alive or p.escaped:
                continue
            snap = eng.snapshot(p.user_id)
            if snap["phase"] == "RESULT":
                return eng, rounds
            you = snap["you"]
            if you.get("acting") and you.get("can"):
                action = rng.choice([a for a in you["can"] if a != "skip"] or ["skip"])
                others = [pp["seat"] for pp in snap["players"]
                          if pp["alive"] and pp["seat"] != you["seat"]]
                target = rng.choice(others) if others else None
                try:
                    if action == "witch_save":
                        target = you["witch"]["victim"]
                    elif action == "witch_poison":
                        continue  # 毒药少用，避免过快终局
                    elif action == "vote_pk":
                        pk = snap.get("pk_seats") or []
                        target = rng.choice(pk) if pk else None
                    eng.submit_action(p.user_id, action, target, rounds * 100.0)
                except EngineError:
                    pass
            elif you.get("speaking"):
                try:
                    eng.submit_speech(p.user_id, f"{you['seat']} 号发言", rounds * 100.0)
                except EngineError:
                    pass
            snap2 = eng.snapshot(p.user_id)
            if snap2.get("last_words_seat") == you["seat"]:
                try:
                    eng.submit_last_words(p.user_id, "遗言", rounds * 100.0)
                except EngineError:
                    pass
        # 心跳推进超时
        t = rounds * 100.0 + 90.0
        eng.check_timeouts(t)
    return eng, rounds


@pytest.mark.parametrize("board", PRESET_BOARDS, ids=lambda b: b["id"])
def test_board_random_games_complete(board):
    """每个预置板子跑 5 局随机对局：必终局、winner 合法、角色守恒"""
    for seed in range(42, 47):
        rng = random.Random(seed)
        n = board["player_count"]
        players = [(i, f"玩家{i}") for i in range(1, n + 1)]
        roles = {Role(k): v for k, v in board["roles"].items()}
        eng = WerewolfEngine(players, roles, GameSettings(), now=1000.0, rng=random.Random(seed))
        eng.start(1000.0)
        eng, rounds = random_drive(eng, rng)
        assert eng.finished(), f"{board['id']} seed={seed} 未终局（轮数 {rounds}）"
        assert eng.winner() in ("VILLAGER", "WEREWOLF")
        assert all(p.role is not None for p in eng.players)


def test_custom_boards_random_games():
    """自定义板子（含极端配置）随机对局压测"""
    custom_boards = [
        {"WEREWOLF": 1, "SEER": 1, "WITCH": 1, "HUNTER": 1, "GUARD": 1, "IDIOT": 1, "VILLAGER": 6},  # 12人全神
        {"WEREWOLF": 3, "SEER": 1, "WITCH": 1, "VILLAGER": 5},   # 10人无猎守白
        {"WEREWOLF": 4, "SEER": 1, "WITCH": 1, "HUNTER": 1, "GUARD": 1, "VILLAGER": 4},  # 12人守卫版
        {"WEREWOLF": 2, "WITCH": 1, "VILLAGER": 4},              # 7人无预言家（警告级）
        {"WEREWOLF": 5, "SEER": 1, "WITCH": 1, "HUNTER": 1, "VILLAGER": 4},  # 12人屠边狼多
    ]
    for i, roles_map in enumerate(custom_boards):
        errors, _ = validate_board(dict(roles_map))
        assert not errors, f"板子{i} 校验失败: {errors}"
        for seed in range(42, 45):
            rng = random.Random(seed)
            total = sum(roles_map.values())
            players = [(j, f"玩家{j}") for j in range(1, total + 1)]
            roles = {Role(k): v for k, v in roles_map.items()}  # 与生产路径一致
            eng = WerewolfEngine(players, roles, GameSettings(),
                                 now=1000.0, rng=random.Random(seed))
            eng.start(1000.0)
            eng, rounds = random_drive(eng, rng)
            assert eng.finished(), f"自定义板{i} seed={seed} 未终局（{rounds} 轮）"
            assert eng.winner() in ("VILLAGER", "WEREWOLF")
