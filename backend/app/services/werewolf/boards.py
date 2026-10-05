"""板子定义与校验"""
from dataclasses import dataclass

from .roles import ROLE_NAMES, Role


@dataclass
class GameSettings:
    """对局可配置项（spec §3.5；时长类 spec 未列为可配置的用固定默认值）"""

    speech_seconds: int = 60        # 每人发言时长，可选 30/60/90/120
    vote_seconds: int = 30          # 投票时长（固定 30）
    night_seconds: int = 40         # 夜晚每个行动阶段时长（固定 40）
    pk_seconds: int = 30            # PK 发言时长（固定 30）
    last_words_seconds: int = 30    # 遗言时长（固定 30）
    dawn_seconds: int = 5           # 天亮死讯展示时长（固定 5）
    witch_self_rescue: str = "never"    # never | first_night | always
    witch_guard_conflict: bool = True   # 奶穿（同晚被守+被救 → 死）


# 预置板子（spec §3.1，屠边局）
PRESET_BOARDS: list[dict] = [
    {"id": "6p", "name": "6人新手局", "player_count": 6,
     "roles": {"WEREWOLF": 2, "SEER": 1, "WITCH": 1, "VILLAGER": 2}},
    {"id": "8p", "name": "8人进阶局", "player_count": 8,
     "roles": {"WEREWOLF": 2, "SEER": 1, "WITCH": 1, "HUNTER": 1, "VILLAGER": 3}},
    {"id": "9p", "name": "9人经典局", "player_count": 9,
     "roles": {"WEREWOLF": 3, "SEER": 1, "WITCH": 1, "HUNTER": 1, "VILLAGER": 3}},
    {"id": "10p", "name": "10人守卫局", "player_count": 10,
     "roles": {"WEREWOLF": 3, "SEER": 1, "WITCH": 1, "HUNTER": 1, "GUARD": 1, "VILLAGER": 3}},
    {"id": "12p", "name": "12人标准局", "player_count": 12,
     "roles": {"WEREWOLF": 4, "SEER": 1, "WITCH": 1, "HUNTER": 1, "IDIOT": 1, "VILLAGER": 4}},
]


def validate_board(roles: dict[str, int]) -> tuple[list[str], list[str]]:
    """校验自定义板子，返回 (errors, warnings)。errors 非空则拒绝创建。"""
    errors: list[str] = []
    warnings: list[str] = []
    total = 0
    cleaned: dict[Role, int] = {}
    for key, cnt in (roles or {}).items():
        try:
            role = Role(key)
        except ValueError:
            errors.append(f"未知角色: {key}")
            continue
        if not isinstance(cnt, bool) and (not isinstance(cnt, int) or cnt < 0):
            errors.append(f"{key} 数量非法")
            continue
        total += cnt
        cleaned[role] = cnt

    if not errors:
        if not 6 <= total <= 12:
            errors.append(f"总人数必须 6-12，当前 {total}")
        if cleaned.get(Role.WEREWOLF, 0) < 1:
            errors.append("狼人至少 1 名")
        if cleaned.get(Role.SEER, 0) > 1:
            errors.append("预言家最多 1 名")
        for r in (Role.WITCH, Role.HUNTER, Role.GUARD, Role.IDIOT):
            if cleaned.get(r, 0) > 1:
                errors.append(f"{ROLE_NAMES[r]}最多 1 名")
        if not errors:
            if cleaned.get(Role.SEER, 0) == 0:
                warnings.append("没有预言家，好人信息能力受限")
            if cleaned.get(Role.WITCH, 0) == 0:
                warnings.append("没有女巫，好人抗刀能力受限")
    return errors, warnings
