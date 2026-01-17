import os
import json
import httpx
from pathlib import Path
from typing import Optional, Dict, Any

# 假期数据缓存目录
HOLIDAY_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "holidays"

# 远程数据源
HOLIDAY_API_URL = "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json"


def ensure_data_dir():
    """确保数据目录存在"""
    HOLIDAY_DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_local_holiday_file(year: int) -> Path:
    """获取本地假期数据文件路径"""
    return HOLIDAY_DATA_DIR / f"{year}.json"


def load_local_holidays(year: int) -> Optional[Dict[str, Any]]:
    """从本地加载假期数据"""
    file_path = get_local_holiday_file(year)
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取本地假期数据失败: {e}")
    return None


def save_local_holidays(year: int, data: Dict[str, Any]) -> bool:
    """保存假期数据到本地"""
    ensure_data_dir()
    file_path = get_local_holiday_file(year)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"假期数据已保存: {file_path}")
        return True
    except Exception as e:
        print(f"保存假期数据失败: {e}")
        return False


async def fetch_remote_holidays(year: int) -> Optional[Dict[str, Any]]:
    """从远程获取假期数据"""
    url = HOLIDAY_API_URL.format(year=year)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"获取远程假期数据失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"获取远程假期数据失败: {e}")
    return None


async def get_holidays(year: int) -> Optional[Dict[str, Any]]:
    """
    获取指定年份的假期数据
    优先从本地读取，本地没有则从远程获取并保存
    """
    # 1. 尝试从本地读取
    local_data = load_local_holidays(year)
    if local_data:
        print(f"从本地加载 {year} 年假期数据")
        return local_data
    
    # 2. 本地没有，从远程获取
    print(f"本地没有 {year} 年假期数据，从远程获取...")
    remote_data = await fetch_remote_holidays(year)
    
    if remote_data:
        # 3. 保存到本地
        save_local_holidays(year, remote_data)
        return remote_data
    
    return None


def list_cached_years() -> list:
    """列出已缓存的年份"""
    ensure_data_dir()
    years = []
    for file in HOLIDAY_DATA_DIR.glob("*.json"):
        try:
            year = int(file.stem)
            years.append(year)
        except ValueError:
            pass
    return sorted(years)
