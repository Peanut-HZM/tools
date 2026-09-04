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

