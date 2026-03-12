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
