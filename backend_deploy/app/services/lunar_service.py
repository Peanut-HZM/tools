import json
import sqlite3
from pathlib import Path
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from lunardate import LunarDate

# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / "data" / "calendar.db"

# 农历月份名称
LUNAR_MONTHS = ['正', '二', '三', '四', '五', '六', '七', '八', '九', '十', '冬', '腊']

# 农历日期名称
LUNAR_DAYS = [
    '初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
    '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
    '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'
]

# 天干
TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

# 地支
DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 生肖
SHENG_XIAO = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

# 传统节日（农历）
LUNAR_FESTIVALS = {
    (1, 1): '春节',
    (1, 15): '元宵节',
    (2, 2): '龙抬头',
    (5, 5): '端午节',
    (7, 7): '七夕节',
    (7, 15): '中元节',
    (8, 15): '中秋节',
    (9, 9): '重阳节',
    (12, 8): '腊八节',
    (12, 23): '小年',
    (12, 30): '除夕',
}

# 公历节日
SOLAR_FESTIVALS = {
    (1, 1): '元旦',
    (2, 14): '情人节',
    (3, 8): '妇女节',
    (3, 12): '植树节',
    (4, 1): '愚人节',
    (5, 1): '劳动节',
    (5, 4): '青年节',
    (6, 1): '儿童节',
    (7, 1): '建党节',
    (8, 1): '建军节',
    (9, 10): '教师节',
    (10, 1): '国庆节',
    (12, 25): '圣诞节',
}


def ensure_db():
    """确保数据库和表存在"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lunar_calendar (
            date TEXT PRIMARY KEY,
            lunar_year INTEGER,
            lunar_month INTEGER,
            lunar_day INTEGER,
            is_leap_month INTEGER,
            lunar_month_name TEXT,
            lunar_day_name TEXT,
            gan_zhi_year TEXT,
            gan_zhi_month TEXT,
            gan_zhi_day TEXT,
            sheng_xiao TEXT,
            lunar_festival TEXT,
            solar_festival TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


def get_gan_zhi_year(year: int) -> str:
    """获取年份的干支"""
    # 以1984年甲子年为基准
    offset = (year - 1984) % 60
    gan = TIAN_GAN[offset % 10]
    zhi = DI_ZHI[offset % 12]
    return f"{gan}{zhi}"


def get_sheng_xiao(year: int) -> str:
    """获取生肖"""
    # 以1984年鼠年为基准
    offset = (year - 1984) % 12
    return SHENG_XIAO[offset]


def calculate_lunar_data(solar_date: date) -> Dict[str, Any]:
    """计算指定公历日期的农历数据"""
    try:
        lunar = LunarDate.fromSolarDate(solar_date.year, solar_date.month, solar_date.day)
        
        lunar_month_name = LUNAR_MONTHS[lunar.month - 1] + '月'
        if lunar.isLeapMonth:
            lunar_month_name = '闰' + lunar_month_name
        
        lunar_day_name = LUNAR_DAYS[lunar.day - 1]
        
        # 干支年
        gan_zhi_year = get_gan_zhi_year(lunar.year)
        
        # 生肖
        sheng_xiao = get_sheng_xiao(lunar.year)
        
        # 农历节日
        lunar_festival = LUNAR_FESTIVALS.get((lunar.month, lunar.day), '')
        
        # 处理除夕（腊月最后一天）
        if lunar.month == 12:
            try:
                # 检查是否是腊月最后一天
                next_day = LunarDate(lunar.year, lunar.month, lunar.day + 1)
            except:
                lunar_festival = '除夕'
        
        # 公历节日
        solar_festival = SOLAR_FESTIVALS.get((solar_date.month, solar_date.day), '')
        
        return {
            'date': solar_date.isoformat(),
            'lunar_year': lunar.year,
            'lunar_month': lunar.month,
            'lunar_day': lunar.day,
            'is_leap_month': 1 if lunar.isLeapMonth else 0,
            'lunar_month_name': lunar_month_name,
            'lunar_day_name': lunar_day_name,
            'gan_zhi_year': gan_zhi_year,
            'gan_zhi_month': '',  # 简化处理
            'gan_zhi_day': '',    # 简化处理
            'sheng_xiao': sheng_xiao,
            'lunar_festival': lunar_festival,
            'solar_festival': solar_festival,
        }
    except Exception as e:
        print(f"计算农历数据失败 {solar_date}: {e}")
        return None


def save_lunar_data(data: Dict[str, Any]):
    """保存农历数据到数据库"""
    ensure_db()
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO lunar_calendar 
        (date, lunar_year, lunar_month, lunar_day, is_leap_month, 
         lunar_month_name, lunar_day_name, gan_zhi_year, gan_zhi_month, 
         gan_zhi_day, sheng_xiao, lunar_festival, solar_festival)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['date'], data['lunar_year'], data['lunar_month'], data['lunar_day'],
        data['is_leap_month'], data['lunar_month_name'], data['lunar_day_name'],
        data['gan_zhi_year'], data['gan_zhi_month'], data['gan_zhi_day'],
        data['sheng_xiao'], data['lunar_festival'], data['solar_festival']
    ))
    
    conn.commit()
    conn.close()


def get_lunar_data(date_str: str) -> Optional[Dict[str, Any]]:
    """从数据库获取农历数据"""
    ensure_db()
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM lunar_calendar WHERE date = ?', (date_str,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'date': row[0],
            'lunar_year': row[1],
            'lunar_month': row[2],
            'lunar_day': row[3],
            'is_leap_month': bool(row[4]),
            'lunar_month_name': row[5],
            'lunar_day_name': row[6],
            'gan_zhi_year': row[7],
            'gan_zhi_month': row[8],
            'gan_zhi_day': row[9],
            'sheng_xiao': row[10],
            'lunar_festival': row[11],
            'solar_festival': row[12],
        }
    return None


def get_or_calculate_lunar_data(solar_date: date) -> Optional[Dict[str, Any]]:
    """获取农历数据，本地没有则计算并保存"""
    date_str = solar_date.isoformat()
    
    # 先从数据库查询
    data = get_lunar_data(date_str)
    if data:
        return data
    
    # 计算并保存
    data = calculate_lunar_data(solar_date)
    if data:
        save_lunar_data(data)
        return data
    
    return None


def get_month_lunar_data(year: int, month: int) -> List[Dict[str, Any]]:
    """获取指定月份所有日期的农历数据"""
    from calendar import monthrange
    
    # 获取该月天数
    _, days_in_month = monthrange(year, month)
    
    result = []
    for day in range(1, days_in_month + 1):
        solar_date = date(year, month, day)
        lunar_data = get_or_calculate_lunar_data(solar_date)
        if lunar_data:
            result.append(lunar_data)
    
    return result


def get_range_lunar_data(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """获取日期范围内的农历数据"""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    result = []
    current = start
    while current <= end:
        lunar_data = get_or_calculate_lunar_data(current)
        if lunar_data:
            result.append(lunar_data)
        current = date(current.year, current.month, current.day + 1) if current.day < 28 else \
                  date(current.year, current.month + 1, 1) if current.month < 12 else \
                  date(current.year + 1, 1, 1)
        # 简单的日期递增
        from datetime import timedelta
        current = start + timedelta(days=(current - start).days + 1)
        if current > end:
            break
        current = start + timedelta(days=len(result))
    
    return result
