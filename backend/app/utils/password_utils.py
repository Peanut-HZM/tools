"""
密码工具函数
"""
import re
import string
import random
from typing import Tuple


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    验证密码强度

    规则:
    - 长度 8-100 位
    - 至少包含 1 个大写字母
    - 至少包含 1 个小写字母
    - 至少包含 1 个数字
    - 至少包含 1 个特殊字符

    返回：(是否通过，错误信息)
    """
    if not password:
        return False, "密码不能为空"

    if len(password) < 8 or len(password) > 100:
        return False, "密码长度必须在 8-100 位之间"

    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少 1 个大写字母"

    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少 1 个小写字母"

    if not re.search(r'\d', password):
        return False, "密码必须包含至少 1 个数字"

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', password):
        return False, "密码必须包含至少 1 个特殊字符"

    return True, ""


def generate_random_password(length: int = 12) -> str:
    """
    生成随机密码

    规则:
    - 默认 12 位
    - 必须包含大小写字母、数字、特殊字符
    """
    if length < 8:
        length = 8

    # 确保每种字符至少有一个
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice('!@#$%^&*()_+-='),
    ]

    # 随机填充剩余位数
    all_chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
    password.extend(random.choice(all_chars) for _ in range(length - 4))

    # 打乱顺序
    random.shuffle(password)

    return ''.join(password)
