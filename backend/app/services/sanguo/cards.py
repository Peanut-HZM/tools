"""三国杀卡牌定义：标准版牌堆（V1 105 张）与花色点数"""
from dataclasses import dataclass
from enum import Enum


class Suit(str, Enum):
    SPADE = "♠"
    HEART = "♥"
    CLUB = "♣"
    DIAMOND = "♦"


class CardKind(str, Enum):
    BASIC = "basic"      # 基本牌
    TRICK = "trick"      # 非延时锦囊
    DELAYED = "delayed"  # 延时锦囊
    EQUIP = "equip"      # 装备


@dataclass(frozen=True)
class Card:
    id: int
    name: str
    suit: str          # ♠ ♥ ♣ ♦
    point: int         # A=1 .. K=13
    kind: CardKind
    sub: str | None = None  # 装备位：weapon:青釭剑 / armor:八卦阵 / horse:+1 / horse:-1


def _mk(cards_spec: list[tuple[str, CardKind, list[tuple[str, int]]]],
        start_id: int) -> list[Card]:
    """cards_spec: [(牌名, 类别, [(花色, 点数), ...])] → 卡牌列表"""
    out: list[Card] = []
    cid = start_id
    for name, kind, suit_points in cards_spec:
        for suit, point in suit_points:
            sub = None
            if kind == CardKind.EQUIP:
                if name in ("诸葛连弩", "青釭剑", "贯石斧", "青龙偃月刀"):
                    sub = f"weapon:{name}"
                elif name in ("八卦阵", "仁王盾"):
                    sub = f"armor:{name}"
                else:
                    sub = f"horse:{name}"
            out.append(Card(id=cid, name=name, suit=suit, point=point,
                            kind=kind, sub=sub))
            cid += 1
    return out


def _spades(points: list[int]) -> list[tuple[str, int]]:
    return [("♠", p) for p in points]


def _hearts(points: list[int]) -> list[tuple[str, int]]:
    return [("♥", p) for p in points]


def _clubs(points: list[int]) -> list[tuple[str, int]]:
    return [("♣", p) for p in points]


def _diamonds(points: list[int]) -> list[tuple[str, int]]:
    return [("♦", p) for p in points]


# 杀 30（偏黑）：黑10 梅10 红5 方5
SHA_POINTS = {
    "spades": [7, 8, 8, 9, 9, 10, 10, 11, 4, 5],
    "clubs": [2, 3, 4, 5, 6, 7, 8, 8, 9, 9],
    "hearts": [10, 10, 11, 12, 13],
    "diamonds": [6, 7, 8, 9, 10],
}
# 闪 15（偏红）：红8 方7
SHAN_POINTS = {
    "hearts": [2, 2, 8, 9, 9, 11, 12, 13],
    "diamonds": [2, 3, 4, 5, 6, 7, 10],
}
# 桃 8（红）：红5 方3
TAO_POINTS = {
    "hearts": [3, 4, 5, 6, 7],
    "diamonds": [2, 3, 12],
}

BASIC_CARDS = [
    ("杀", CardKind.BASIC,
     _spades(SHA_POINTS["spades"]) + _clubs(SHA_POINTS["clubs"]) +
     _hearts(SHA_POINTS["hearts"]) + _diamonds(SHA_POINTS["diamonds"])),
    ("闪", CardKind.BASIC,
     _hearts(SHAN_POINTS["hearts"]) + _diamonds(SHAN_POINTS["diamonds"])),
    ("桃", CardKind.BASIC,
     _hearts(TAO_POINTS["hearts"]) + _diamonds(TAO_POINTS["diamonds"])),
]

# 锦囊（V1 41 张：官方 34 + 无懈外的平衡调整见 spec——总数以 DECK 对齐 105）
TRICK_CARDS = [
    ("决斗", CardKind.TRICK, _spades([1]) + _clubs([1]) + _diamonds([1])),
    ("过河拆桥", CardKind.TRICK,
     _spades([3, 4, 12]) + _clubs([3, 4]) + _hearts([12])),
    ("顺手牵羊", CardKind.TRICK,
     _spades([3, 4, 11]) + _clubs([3]) + _diamonds([3])),
    ("无中生有", CardKind.TRICK, _hearts([7, 8, 9, 11])),
    ("南蛮入侵", CardKind.TRICK, _spades([7, 13]) + _clubs([7])),
    ("万箭齐发", CardKind.TRICK, _hearts([1])),
    ("桃园结义", CardKind.TRICK, _hearts([1])),
    ("五谷丰登", CardKind.TRICK, _hearts([3, 4])),
    ("无懈可击", CardKind.TRICK,
     _spades([11]) + _clubs([10, 11, 12])),
    ("乐不思蜀", CardKind.DELAYED,
     _spades([6]) + _clubs([4]) + _hearts([6])),
    ("闪电", CardKind.DELAYED, _spades([2, 9])),
]

# 装备 14：武器4 + 防具3 + 马6 + 补1 防具（对齐总数）
EQUIP_CARDS = [
    ("诸葛连弩", CardKind.EQUIP, _clubs([1])),
    ("青釭剑", CardKind.EQUIP, _spades([6])),
    ("贯石斧", CardKind.EQUIP, _diamonds([5])),
    ("青龙偃月刀", CardKind.EQUIP, _spades([5])),
    ("八卦阵", CardKind.EQUIP, _diamonds([2]) + _clubs([9])),
    ("仁王盾", CardKind.EQUIP, _clubs([2])),
    ("绝影", CardKind.EQUIP, _spades([5])),      # +1 马
    ("爪黄飞电", CardKind.EQUIP, _hearts([13])),  # +1 马
    ("的卢", CardKind.EQUIP, _clubs([5])),        # +1 马
    ("大宛", CardKind.EQUIP, _spades([13])),      # -1 马
    ("赤兔", CardKind.EQUIP, _hearts([5])),       # -1 马
    ("紫骍", CardKind.EQUIP, _diamonds([13])),    # -1 马
]

DECK: list[Card] = (
    _mk(BASIC_CARDS, 1)
    + _mk(TRICK_CARDS, 100)
    + _mk(EQUIP_CARDS, 200)
)

# ±马 sub 归一（名字→方向）
for c in DECK:
    if c.kind == CardKind.EQUIP and c.sub and c.sub.startswith("horse:"):
        name = c.sub.split(":")[1]
        if name in ("绝影", "爪黄飞电", "的卢"):
            object.__setattr__(c, "sub", "horse:+1")
        else:
            object.__setattr__(c, "sub", "horse:-1")


def suit_count(name: str) -> dict:
    out: dict = {}
    for c in DECK:
        if c.name == name:
            key = c.sub or c.kind.value
            out[key] = out.get(key, 0) + 1
    return out
