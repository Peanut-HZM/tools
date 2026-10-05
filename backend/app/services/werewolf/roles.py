"""狼人杀角色定义"""
from enum import Enum


class Role(str, Enum):
    WEREWOLF = "WEREWOLF"
    VILLAGER = "VILLAGER"
    SEER = "SEER"
    WITCH = "WITCH"
    HUNTER = "HUNTER"
    GUARD = "GUARD"
    IDIOT = "IDIOT"


# 角色中文名
ROLE_NAMES: dict[Role, str] = {
    Role.WEREWOLF: "狼人",
    Role.VILLAGER: "村民",
    Role.SEER: "预言家",
    Role.WITCH: "女巫",
    Role.HUNTER: "猎人",
    Role.GUARD: "守卫",
    Role.IDIOT: "白痴",
}

# 阵营：WOLF=狼人阵营 GOD=神职 PEASANT=平民（屠边判定按 GOD/PEASANT 分边）
ROLE_CAMPS: dict[Role, str] = {
    Role.WEREWOLF: "WOLF",
    Role.SEER: "GOD",
    Role.WITCH: "GOD",
    Role.HUNTER: "GOD",
    Role.GUARD: "GOD",
    Role.IDIOT: "GOD",
    Role.VILLAGER: "PEASANT",
}

# 夜晚行动顺序（市面主流：守卫→狼人→预言家→女巫）
NIGHT_ACTION_ORDER: list[Role] = [Role.GUARD, Role.WEREWOLF, Role.SEER, Role.WITCH]
