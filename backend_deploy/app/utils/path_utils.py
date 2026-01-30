"""
Path validation utilities for security
"""
import os
from pathlib import Path
from typing import Tuple


def validate_path(path: str, root_path: str) -> Tuple[bool, str]:
    """
    Validate that a path is safe and within the root directory.
    
    Args:
        path: The path to validate (can be relative or absolute)
        root_path: The root directory that all paths must be within
        
    Returns:
        Tuple of (is_valid, error_message or resolved_path)
    """
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
    return path.replace('\\', '/')


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
