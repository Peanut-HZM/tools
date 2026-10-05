"""三国杀牌堆与武将定义验收（对照标准版 108 张牌堆组成，V1 用 105 张）"""
from app.services.sanguo.cards import CardKind, DECK, suit_count
from app.services.sanguo.heroes import HEROES, Kingdom


def test_deck_total_100():
    """标准版精选牌堆（spec §1：105 计划按明细表收敛为 100 张）"""
    assert len(DECK) == 100
    ids = [c.id for c in DECK]
    assert len(set(ids)) == 100  # 每张牌唯一 id


def test_deck_basic_cards():
    by_name = {}
    for c in DECK:
        if c.kind == CardKind.BASIC:
            by_name[c.name] = by_name.get(c.name, 0) + 1
    assert by_name == {"杀": 30, "闪": 15, "桃": 8}


def test_deck_tricks():
    tricks = {}
    for c in DECK:
        if c.kind in (CardKind.TRICK, CardKind.DELAYED):
            tricks[c.name] = tricks.get(c.name, 0) + 1
    assert tricks == {
        "决斗": 3, "过河拆桥": 6, "顺手牵羊": 5, "无懈可击": 4,
        "南蛮入侵": 3, "万箭齐发": 1, "桃园结义": 1, "五谷丰登": 2,
        "无中生有": 4, "乐不思蜀": 3, "闪电": 2,
    }


def test_deck_equips():
    equips = [c for c in DECK if c.kind == CardKind.EQUIP]
    assert len(equips) == 13  # 武器4 + 防具3 + 马6
    weapon_names = {c.name for c in equips if c.sub and c.sub.startswith("weapon:")}
    assert weapon_names == {"诸葛连弩", "青釭剑", "贯石斧", "青龙偃月刀"}
    armor_names = [c.name for c in equips if c.sub and c.sub.startswith("armor:")]
    assert armor_names.count("八卦阵") == 2 and armor_names.count("仁王盾") == 1
    plus = [c for c in equips if c.sub == "horse:+1"]
    minus = [c for c in equips if c.sub == "horse:-1"]
    assert len(plus) == 3 and len(minus) == 3


def test_deck_points_and_suits_valid():
    for c in DECK:
        assert 1 <= c.point <= 13, c
        assert c.suit in ("♠", "♥", "♣", "♦"), c
    # 闪电必须可判定（黑桃 2-9 之间才会 3 雷伤，牌面应有黑桃闪电）
    bolts = [c for c in DECK if c.name == "闪电"]
    assert any(c.suit == "♠" and 2 <= c.point <= 9 for c in bolts)


def test_heroes_eight_standard():
    assert set(HEROES.keys()) == {
        "liubei", "guanyu", "zhangfei", "zhaoyun",
        "caocao", "lvbu", "diaochan", "huatuo",
    }
    assert HEROES["liubei"].kingdom == Kingdom.SHU
    assert HEROES["caocao"].kingdom == Kingdom.WEI
    assert HEROES["lvbu"].kingdom == Kingdom.QUN
    # 体力：标准 4 血；貂蝉/华佗 3 血
    assert HEROES["lvbu"].max_hp == 4
    assert HEROES["diaochan"].max_hp == 3 and HEROES["huatuo"].max_hp == 3
    # 技能清单
    assert "仁德" in HEROES["liubei"].skills
    assert "武圣" in HEROES["guanyu"].skills
    assert "咆哮" in HEROES["zhangfei"].skills
    assert "龙胆" in HEROES["zhaoyun"].skills
    assert "奸雄" in HEROES["caocao"].skills
    assert "无双" in HEROES["lvbu"].skills
    assert "离间" in HEROES["diaochan"].skills and "闭月" in HEROES["diaochan"].skills
    assert "急救" in HEROES["huatuo"].skills and "青囊" in HEROES["huatuo"].skills
