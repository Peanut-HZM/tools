"""狼人杀板子模块测试"""
from app.services.werewolf.boards import PRESET_BOARDS, validate_board
from app.services.werewolf.roles import ROLE_CAMPS, Role


def test_preset_boards_counts_match_player_count():
    for b in PRESET_BOARDS:
        assert sum(b["roles"].values()) == b["player_count"]
        assert 6 <= b["player_count"] <= 12
        assert b["roles"].get("WEREWOLF", 0) >= 1


def test_preset_boards_cover_6_8_9_10_12():
    assert sorted(b["player_count"] for b in PRESET_BOARDS) == [6, 8, 9, 10, 12]


def test_12p_board_is_standard_yu_nv_lie_bai():
    b = next(b for b in PRESET_BOARDS if b["player_count"] == 12)
    assert b["roles"] == {"WEREWOLF": 4, "SEER": 1, "WITCH": 1, "HUNTER": 1, "IDIOT": 1, "VILLAGER": 4}


def test_camps():
    assert ROLE_CAMPS[Role.WEREWOLF] == "WOLF"
    assert ROLE_CAMPS[Role.VILLAGER] == "PEASANT"
    assert ROLE_CAMPS[Role.IDIOT] == "GOD"  # 白痴计入神职（屠边判定）


def test_validate_board_ok():
    errors, _ = validate_board({"WEREWOLF": 2, "SEER": 1, "VILLAGER": 3})
    assert errors == []


def test_validate_board_rejects():
    errors, _ = validate_board({"WEREWOLF": 0, "VILLAGER": 6})
    assert any("狼人" in e for e in errors)
    errors, _ = validate_board({"WEREWOLF": 1, "SEER": 2, "VILLAGER": 3})
    assert any("预言家" in e for e in errors)
    errors, _ = validate_board({"WEREWOLF": 1, "VILLAGER": 20})
    assert any("6-12" in e for e in errors)
    errors, _ = validate_board({"GOD": 1, "VILLAGER": 5})
    assert any("未知角色" in e for e in errors)


def test_validate_board_warnings():
    _, warnings = validate_board({"WEREWOLF": 3, "VILLAGER": 3})
    assert warnings  # 无预言家/女巫给出体验警告但不算错误
