"""
内容安全过滤器
检测不当内容，包括敏感词、政治内容、暴力内容等
"""

import re
from typing import List, Dict, Tuple


class ContentSafetyFilter:
    """内容安全过滤器"""

    # 敏感词类别
    CATEGORIES = {
        "political": "政治敏感",
        "violence": "暴力内容",
        "pornography": "色情内容",
        "gambling": "赌博内容",
        "drugs": "毒品相关",
        "hate_speech": "仇恨言论",
        "harassment": "骚扰内容",
    }

    def __init__(self):
        # 加载敏感词库（示例，实际应使用更完整的词库）
        self.sensitive_words = self._load_sensitive_words()

    def _load_sensitive_words(self) -> Dict[str, List[str]]:
        """加载敏感词库"""
        # 这里仅做示例，实际应使用配置文件或数据库
        return {
            "political": [],  # 政治敏感词
            "violence": ["杀人", "自杀", "爆炸", "恐怖"],  # 暴力词
            "pornography": [],  # 色情词
            "gambling": ["赌博", "赌球", "六合彩"],  # 赌博词
            "drugs": ["毒品", "冰毒", "海洛因"],  # 毒品词
            "hate_speech": [],  # 仇恨言论
            "harassment": [],  # 骚扰内容
        }

    def check_content(self, content: str) -> Tuple[bool, List[Dict]]:
        """
        检查内容安全性

        Args:
            content: 待检查的内容

        Returns:
            (is_safe, violations) - 是否安全，违规列表
        """
        if not content:
            return True, []

        violations = []

        # 检查敏感词
        for category, words in self.sensitive_words.items():
            for word in words:
                if word in content:
                    violations.append(
                        {
                            "type": "sensitive_word",
                            "category": self.CATEGORIES.get(category, category),
                            "keyword": word,
                            "severity": "high",
                        }
                    )

        # 检查 URL（过多的 URL 可能是垃圾信息）
        url_count = len(re.findall(r"https?://\S+", content))
        if url_count > 5:
            violations.append(
                {
                    "type": "excessive_urls",
                    "category": "垃圾信息",
                    "count": url_count,
                    "severity": "medium",
                }
            )

        # 检查重复内容（可能是刷屏）
        if self._check_repeated_content(content):
            violations.append(
                {"type": "repeated_content", "category": "刷屏行为", "severity": "low"}
            )

        # 检查过长的连续大写字母（可能是垃圾广告）
        if re.search(r"[A-Z]{10,}", content):
            violations.append(
                {"type": "excessive_caps", "category": "可疑内容", "severity": "low"}
            )

        is_safe = len(violations) == 0
        return is_safe, violations

    def _check_repeated_content(self, content: str, min_repeat: int = 3) -> bool:
        """检查是否有重复内容"""
        lines = content.strip().split("\n")
        if len(lines) < min_repeat:
            return False

        # 检查连续相同的行
        repeat_count = 1
        for i in range(1, len(lines)):
            if lines[i] == lines[i - 1] and lines[i].strip():
                repeat_count += 1
                if repeat_count >= min_repeat:
                    return True
            else:
                repeat_count = 1

        return False

    def filter_content(self, content: str) -> str:
        """
        过滤敏感内容

        Args:
            content: 待过滤的内容

        Returns:
            过滤后的内容
        """
        filtered = content

        for category, words in self.sensitive_words.items():
            for word in words:
                # 使用 * 替换敏感词
                filtered = filtered.replace(word, "*" * len(word))

        return filtered

    def get_violation_message(self, violations: List[Dict]) -> str:
        """
        生成违规提示消息

        Args:
            violations: 违规列表

        Returns:
            提示消息
        """
        if not violations:
            return ""

        # 按严重程度排序
        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_violations = sorted(
            violations, key=lambda x: severity_order.get(x.get("severity", "low"), 2)
        )

        high_severity = [v for v in sorted_violations if v.get("severity") == "high"]

        if high_severity:
            categories = set(v["category"] for v in high_severity)
            return f"内容包含不当信息：{', '.join(categories)}。请修改后重新提交。"

        return "内容可能包含不当信息，请检查后重新提交。"


# 全局实例
_content_filter = None


def get_content_filter() -> ContentSafetyFilter:
    """获取内容过滤器实例"""
    global _content_filter
    if _content_filter is None:
        _content_filter = ContentSafetyFilter()
    return _content_filter


def check_content_safety(content: str) -> Tuple[bool, List[Dict]]:
    """检查内容安全性（快捷函数）"""
    return get_content_filter().check_content(content)


def filter_sensitive_content(content: str) -> str:
    """过滤敏感内容（快捷函数）"""
    return get_content_filter().filter_content(content)
