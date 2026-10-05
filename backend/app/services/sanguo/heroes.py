"""三国杀标准版武将定义（V1 八将）"""
from dataclasses import dataclass
from enum import Enum


class Kingdom(str, Enum):
    SHU = "蜀"
    WEI = "魏"
    QUN = "群"


@dataclass(frozen=True)
class Hero:
    key: str
    name: str
    kingdom: Kingdom
    max_hp: int
    skills: tuple[str, ...]
    gender: str = "male"  # 离间只作用于男性角色


HEROES: dict[str, Hero] = {
    "liubei": Hero("liubei", "刘备", Kingdom.SHU, 4, ("仁德",), gender="male"),
    "guanyu": Hero("guanyu", "关羽", Kingdom.SHU, 4, ("武圣",)),
    "zhangfei": Hero("zhangfei", "张飞", Kingdom.SHU, 4, ("咆哮",)),
    "zhaoyun": Hero("zhaoyun", "赵云", Kingdom.SHU, 4, ("龙胆",)),
    "caocao": Hero("caocao", "曹操", Kingdom.WEI, 4, ("奸雄",)),
    "lvbu": Hero("lvbu", "吕布", Kingdom.QUN, 4, ("无双",)),
    "diaochan": Hero("diaochan", "貂蝉", Kingdom.QUN, 3, ("离间", "闭月"), gender="female"),
    "huatuo": Hero("huatuo", "华佗", Kingdom.QUN, 3, ("急救", "青囊")),
}
