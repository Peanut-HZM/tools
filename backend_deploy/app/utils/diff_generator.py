"""
差异生成工具
用于比较两个版本文本的差异
"""

from typing import Dict, List, Tuple


def generate_diff(old_text: str, new_text: str) -> str:
    """
    生成两个文本的差异

    使用简单的行级比较算法
    返回格式化的差异字符串
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff_lines = []

    # 使用简单的最长公共子序列 (LCS) 算法
    lcs = compute_lcs(old_lines, new_lines)

    old_idx = 0
    new_idx = 0
    lcs_idx = 0

    while old_idx < len(old_lines) or new_idx < len(new_lines):
        # 检查当前行是否在 LCS 中
        if lcs_idx < len(lcs):
            lcs_line = lcs[lcs_idx]

            # 删除不在 LCS 中的旧行
            while old_idx < len(old_lines) and old_lines[old_idx] != lcs_line:
                diff_lines.append(f"- {old_lines[old_idx].rstrip()}")
                old_idx += 1

            # 添加不在 LCS 中的新行
            while new_idx < len(new_lines) and new_lines[new_idx] != lcs_line:
                diff_lines.append(f"+ {new_lines[new_idx].rstrip()}")
                new_idx += 1

            # 匹配的行
            if old_idx < len(old_lines) and new_idx < len(new_lines):
                diff_lines.append(f"  {old_lines[old_idx].rstrip()}")
                old_idx += 1
                new_idx += 1
                lcs_idx += 1
        else:
            # 处理剩余的行
            while old_idx < len(old_lines):
                diff_lines.append(f"- {old_lines[old_idx].rstrip()}")
                old_idx += 1

            while new_idx < len(new_lines):
                diff_lines.append(f"+ {new_lines[new_idx].rstrip()}")
                new_idx += 1

    return "\n".join(diff_lines)


def compute_lcs(seq1: List[str], seq2: List[str]) -> List[str]:
    """
    计算两个序列的最长公共子序列
    """
    m, n = len(seq1), len(seq2)

    # 创建 DP 表
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # 填充 DP 表
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # 回溯构建 LCS
    lcs = []
    i, j = m, n
    while i > 0 and j > 0:
        if seq1[i - 1] == seq2[j - 1]:
            lcs.append(seq1[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] > dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    lcs.reverse()
    return lcs


def format_diff_view(diff_text: str, context_lines: int = 3) -> Dict[str, List[str]]:
    """
    格式化差异视图，分为添加、删除和未变更的行

    Args:
        diff_text: 差异文本
        context_lines: 上下文行数

    Returns:
        包含 additions, deletions, unchanged 的字典
    """
    additions = []
    deletions = []
    unchanged = []

    for line in diff_text.splitlines():
        if line.startswith("+ "):
            additions.append(line[2:])
        elif line.startswith("- "):
            deletions.append(line[2:])
        else:
            unchanged.append(line[2:] if line.startswith("  ") else line)

    return {
        "additions": additions,
        "deletions": deletions,
        "unchanged": unchanged,
        "summary": generate_summary(additions, deletions),
    }


def generate_summary(additions: List[str], deletions: List[str]) -> str:
    """
    生成差异摘要
    """
    added_lines = len(additions)
    deleted_lines = len(deletions)

    if added_lines == 0 and deleted_lines == 0:
        return "没有变更"

    parts = []
    if added_lines > 0:
        parts.append(f"新增 {added_lines} 行")
    if deleted_lines > 0:
        parts.append(f"删除 {deleted_lines} 行")

    return ", ".join(parts)


def generate_word_diff(old_text: str, new_text: str) -> List[Dict[str, str]]:
    """
    生成词级差异（更细粒度）

    Returns:
        差异列表，每项包含 type (added/deleted/unchanged) 和 text
    """
    old_words = old_text.split()
    new_words = new_text.split()

    lcs = compute_lcs(old_words, new_words)

    result = []
    old_idx = 0
    new_idx = 0
    lcs_idx = 0

    while old_idx < len(old_words) or new_idx < len(new_words):
        if lcs_idx < len(lcs):
            lcs_word = lcs[lcs_idx]

            while old_idx < len(old_words) and old_words[old_idx] != lcs_word:
                result.append({"type": "deleted", "text": old_words[old_idx]})
                old_idx += 1

            while new_idx < len(new_words) and new_words[new_idx] != lcs_word:
                result.append({"type": "added", "text": new_words[new_idx]})
                new_idx += 1

            if old_idx < len(old_words) and new_idx < len(new_words):
                result.append({"type": "unchanged", "text": old_words[old_idx]})
                old_idx += 1
                new_idx += 1
                lcs_idx += 1
        else:
            while old_idx < len(old_words):
                result.append({"type": "deleted", "text": old_words[old_idx]})
                old_idx += 1

            while new_idx < len(new_words):
                result.append({"type": "added", "text": new_words[new_idx]})
                new_idx += 1

    return result
