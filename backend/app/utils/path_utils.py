"""
Path validation utilities for security
"""
import os
from pathlib import Path
from typing import Tuple, Optional


def validate_path(path: str, root_path: Optional[str] = None):
    """
    Validate that a path is safe and within the root directory.
    
    Args:
        path: The path to validate (can be relative or absolute)
        root_path: The root directory that all paths must be within
        
    Returns:
        Tuple of (is_valid, error_message or resolved_path)
    """
    if root_path is None:
        if path in ("", "."):
            return True
        normalized = normalize_path(path)
        if os.path.isabs(normalized):
            return False
        parts = [p for p in normalized.split("/") if p]
        if ".." in parts:
            return False
        return True
    if not path:
        return False, "Path cannot be empty"
    
    # Check for obvious traversal attempts
    if '..' in path:
        return False, "Path traversal detected: '..' not allowed"
    
    # Normalize paths
    root = Path(root_path).resolve()
    
    # Handle relative paths
    if not os.path.isabs(path):
        target = (root / path).resolve()
    else:
        target = Path(path).resolve()
    
    # Check if target is within root
    try:
        target.relative_to(root)
    except ValueError:
        return False, f"Path is outside allowed root directory"
    
    return True, str(target)


def is_hidden(name: str) -> bool:
    """Check if a file or directory name is hidden (starts with .)"""
    return name.startswith('.')


def is_markdown_file(name: str) -> bool:
    """Check if a file is a Markdown file"""
    lower_name = name.lower()
    return lower_name.endswith('.md') or lower_name.endswith('.markdown')


def get_relative_path(full_path: str, root_path: str) -> str:
    """Get the relative path from root"""
    root = Path(root_path).resolve()
    target = Path(full_path).resolve()
    try:
        return str(target.relative_to(root))
    except ValueError:
        return str(target)


def normalize_path(path: str) -> str:
    """Normalize path separators to forward slashes"""
    normalized = path.replace('\\', '/')
    while '//' in normalized:
        normalized = normalized.replace('//', '/')
    return normalized

def is_safe_path(root_path: str, target_path: str) -> bool:
    root = Path(root_path).resolve()
    target = Path(target_path).resolve()
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False

def join_user_path(user_id: str, relative_path: str, base_path: str = "./data/users") -> str:
    user_root = Path(get_user_root_path(user_id, base_path)).resolve()
    target = user_root / relative_path if relative_path else user_root
    return str(target)


def get_user_root_path(user_id: str, base_path: str = "./data/users") -> str:
    """
    Get the root path for a user's markdown files.
    
    Args:
        user_id: The user's ID
        base_path: Base path for user data storage
        
    Returns:
        Full path to user's markdown files directory
    """
    return str(Path(base_path) / user_id / "markdown-files")


def ensure_user_directory(user_id: str, base_path: str = "./data/users") -> str:
    """
    Ensure user's markdown files directory exists.

    Args:
        user_id: The user's ID
        base_path: Base path for user data storage

    Returns:
        Full path to user's markdown files directory
    """
    user_root = Path(base_path) / user_id / "markdown-files"
    user_root.mkdir(parents=True, exist_ok=True)

    # Also create config directory
    config_dir = user_root / ".markdown-editor"
    config_dir.mkdir(parents=True, exist_ok=True)

    return str(user_root)


# ---------------------------------------------------------------------------
# 文件类型工具函数
# ---------------------------------------------------------------------------

# 文件类型映射表：类型名 -> 支持的扩展名列表
FILE_TYPE_MAP: dict[str, list[str]] = {
    'markdown': ['.md', '.markdown'],
    'html': ['.html', '.htm'],
    'text': [
        '.txt', '.log', '.json', '.yaml', '.yml',
        '.xml', '.csv', '.ini', '.cfg', '.toml',
    ],
    'image': [
        '.png', '.jpg', '.jpeg', '.gif', '.svg',
        '.webp', '.bmp', '.ico',
    ],
    'code': [
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java',
        '.go', '.rs', '.c', '.cpp', '.h', '.css',
        '.scss', '.sh', '.sql',
    ],
}

# 支持预览的文件类型集合
PREVIEWABLE_TYPES: set[str] = {'markdown', 'html'}


def get_file_type(name: str) -> str:
    """根据文件名（或路径）返回文件类型分类。

    匹配规则：按扩展名在 FILE_TYPE_MAP 中查找，未命中返回 'other'。
    大小写不敏感。
    """
    lower_name = name.lower()
    for file_type, extensions in FILE_TYPE_MAP.items():
        if any(lower_name.endswith(ext) for ext in extensions):
            return file_type
    return 'other'


def get_extension(name: str) -> str:
    """返回小写扩展名（含点号），无扩展名时返回空字符串。

    与 os.path.splitext 行为一致：'.gitignore' 返回 ''，'a.tar.gz' 返回 '.gz'。
    """
    _, ext = os.path.splitext(name)
    return ext.lower()


def is_previewable(name: str) -> bool:
    """判断文件是否支持预览（当前仅 markdown 和 html）。"""
    file_type = get_file_type(name)
    return file_type in PREVIEWABLE_TYPES



# ---------------------------------------------------------------------------
# 敏感路径安全验证
# ---------------------------------------------------------------------------

# 敏感路径黑名单（禁止访问）
SENSITIVE_PATHS = [
    '/etc/shadow',
    '/etc/passwd',
    '/proc/',
    '/sys/',
    '/dev/',
    '/root/',
]


def _to_posix(path_str: str) -> str:
    """统一为 POSIX 风格并去掉 Windows 盘符（D:\etc\shadow → /etc/shadow）"""
    normalized = path_str.replace(chr(92), '/')
    if len(normalized) >= 2 and normalized[1] == ':':
        normalized = normalized[2:]
    return normalized


def is_sensitive_path(path: str) -> bool:
    """检查路径是否为系统敏感路径

    Args:
        path: 绝对路径

    Returns:
        是否为敏感路径
    """
    # Windows 上 Path.resolve() 会给 /etc/shadow 加当前盘符（D:\etc\shadow），
    # 直接前缀匹配会全部失配，导致敏感路径检测在 Windows 上完全失效。
    # 因此同时用"原始输入的 POSIX 归一化"与"resolve 后路径的 POSIX 归一化"匹配。
    resolved = Path(path).resolve()
    path_str = _to_posix(str(resolved))
    normalized_input = _to_posix(path)

    for sensitive in SENSITIVE_PATHS:
        # 对于目录前缀匹配，确保带尾部斜杠
        if sensitive.endswith('/'):
            if normalized_input.startswith(sensitive) or path_str.startswith(sensitive):
                return True
        else:
            if normalized_input == sensitive or normalized_input.startswith(sensitive + '/'):
                return True
            if path_str == sensitive or path_str.startswith(sensitive + '/'):
                return True
    return False


def validate_any_path(path: str) -> Tuple[bool, str]:
    """验证任意路径（允许访问任何非敏感路径）

    Args:
        path: 用户输入的路径（可以是绝对或相对，支持 ~ 展开）

    Returns:
        Tuple[是否有效，错误信息或解析后的绝对路径]
    """
    if not path:
        return False, "路径不能为空"

    # 展开 ~ 为用户 home 目录
    # 注意：HOME 环境变量可能被覆盖为缓存目录，需要使用 REAL_HOME
    from app.config.config import REAL_HOME
    if path.startswith('~'):
        expanded = path.replace('~', REAL_HOME, 1)
    else:
        expanded = path

    # 检查路径遍历攻击：只阻止 '..' 作为独立路径组件
    parts = Path(expanded).parts
    if '..' in parts:
        return False, "路径遍历攻击检测：不允许 '..'"

    try:
        # 解析路径
        if os.path.isabs(expanded):
            resolved = Path(expanded).resolve()
        else:
            resolved = (Path(os.getcwd()) / expanded).resolve()

        # 检查敏感路径
        if is_sensitive_path(str(resolved)):
            return False, "禁止访问系统敏感路径"

        return True, str(resolved)
    except Exception as e:
        return False, f"路径解析失败：{str(e)}"
