"""
内容安全过滤器
"""

import re
from typing import Tuple, Optional


class ContentFilter:
    """内容安全过滤器"""

    # 敏感词列表（示例）
    SENSITIVE_PATTERNS = [
        r"暴力",
        r"色情",
        r"赌博",
        r"毒品",
        r"黑客",
        r"攻击",
    ]

    @classmethod
    def check_content(cls, content: str) -> Tuple[bool, Optional[str]]:
        """
        检查内容是否安全

        Returns:
            (是否安全, 违规原因)
        """
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"内容包含不当信息: {pattern}"

        return True, None

    @classmethod
    def sanitize_input(cls, content: str) -> str:
        """清理输入内容"""
        # 移除控制字符
        content = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", content)
        # 限制长度
        return content[:10000]
