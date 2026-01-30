"""
Markdown File Service - Handles all file system operations with user isolation
"""
import os
import shutil
import io
from pathlib import Path
from app.services.oss_service import oss_service
from datetime import datetime
from typing import Optional, Set

from app.models.file_models import (
    FileNode, FileContent, SaveResult, CreateResult, 
    RenameResult, DeleteResult
)
from app.utils.path_utils import (
    validate_path, is_hidden, is_markdown_file, 
    get_relative_path, normalize_path, ensure_user_directory
)


class MarkdownFileService:
    """Service for file system operations with user isolation"""
    
    def __init__(self, user_id: str, base_path: str = "./data/users", custom_root: Optional[str] = None):
        """
        Initialize MarkdownFileService with user-specific root directory.
        
        Args:
            user_id: The user's ID for file isolation
            base_path: Base path for user data storage
            custom_root: Optional custom root path (overrides default sandbox)
        """
        self.user_id = user_id
        self.base_path = base_path
        
        if custom_root and os.path.exists(custom_root) and os.path.isdir(custom_root):
            self.root_path = Path(custom_root).resolve()
        else:
            self.root_path = Path(ensure_user_directory(user_id, base_path)).resolve()
        
        self._gitignore_patterns: Set[str] = set()
        self._add_default_ignores()
        self._load_gitignore()
    
    def _add_default_ignores(self) -> None:
        """Add default ignore patterns for performance and safety"""
        defaults = {
            'node_modules', '.git', '.svn', '.hg', '.idea', '.vscode', 
            '__pycache__', 'venv', 'env', 'dist', 'build', 'target',
            '.DS_Store', 'Thumbs.db'
        }
        self._gitignore_patterns.update(defaults)

    def _load_gitignore(self) -> None:
        """Load patterns from .gitignore file if it exists"""
        gitignore_path = self.root_path / '.gitignore'
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self._gitignore_patterns.add(line)
            except Exception:
                pass  # Ignore errors reading .gitignore
    
    def _is_ignored(self, name: str, is_dir: bool = False) -> bool:
        """Check if a file/directory should be ignored"""
        # Always ignore hidden files/directories (except .markdown-editor config)
        if is_hidden(name) and name != '.markdown-editor':
            return True
        
        # Check gitignore patterns (simplified matching)
        for pattern in self._gitignore_patterns:
            pattern = pattern.rstrip('/')
            if pattern == name:
                return True
            if pattern.endswith('*') and name.startswith(pattern[:-1]):
                return True
        
        return False
    
    def _validate_and_resolve(self, path: str) -> Path:
        """Validate path and return resolved Path object"""
        is_valid, result = validate_path(path, str(self.root_path))
        if not is_valid:
            raise ValueError(result)
        return Path(result)
    
    def get_root_path(self) -> str:
        """Get the user's root path"""
        return str(self.root_path)
    
    def get_directory_tree(self, path: str = "") -> FileNode:
        """
        Scan and return directory tree structure.
        Only includes Markdown files and directories containing them.
        
        Args:
            path: Relative path from root (empty string for root)
            
        Returns:
            FileNode representing the directory tree
        """
        if path:
            target_path = self._validate_and_resolve(path)
        else:
            target_path = self.root_path
        
        return self._scan_directory(target_path)
    
    def _scan_directory(self, dir_path: Path) -> FileNode:
        """Recursively scan a directory"""
        rel_path = get_relative_path(str(dir_path), str(self.root_path))
        if rel_path == '.':
            rel_path = ''
        
        node = FileNode(
            name=dir_path.name or str(self.root_path),
            path=normalize_path(rel_path),
            type="directory",
            children=[]
        )
        
        try:
            entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return node
        
        for entry in entries:
            # Skip ignored files/directories
            if self._is_ignored(entry.name, entry.is_dir()):
                continue
            
            if entry.is_dir():
                # Recursively scan subdirectory
                child_node = self._scan_directory(entry)
                # Only include directory if it has markdown files
                if child_node.children:
                    node.children.append(child_node)
            elif entry.is_file() and is_markdown_file(entry.name):
                # Include markdown files
                stat = entry.stat()
                child_rel_path = get_relative_path(str(entry), str(self.root_path))
                file_node = FileNode(
                    name=entry.name,
                    path=normalize_path(child_rel_path),
                    type="file",
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime)
                )
                node.children.append(file_node)
        
        return node

    def read_file(self, path: str) -> FileContent:
        """
        Read file content with metadata.
        
        Args:
            path: Relative path to the file
            
        Returns:
            FileContent with content and metadata
        """
        file_path = self._validate_and_resolve(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        stat = file_path.stat()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return FileContent(
            path=normalize_path(path),
            content=content,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime)
        )
    
    def save_file(self, path: str, content: str) -> SaveResult:
        """
        Save content to a file (Upload to OSS).
        
        Args:
            path: Relative path to the file
            content: Content to save
            
        Returns:
            SaveResult indicating success/failure
        """
        try:
            # Upload to OSS
            # Path should be relative to user's root, e.g., "docs/notes.md"
            # We prefix with "users/{user_id}/markdown/"
            normalized_path = path.lstrip('/')
            object_name = f"users/{self.user_id}/markdown/{normalized_path}"
            
            # Convert content to bytes
            data = content.encode('utf-8')
            size = len(data)
            file_obj = io.BytesIO(data)
            
            url = oss_service.upload_file(
                object_name=object_name,
                data=file_obj,
                size=size,
                content_type="text/markdown",
                uploaded_by=self.user_id
            )
            
            if not url:
                return SaveResult(
                    success=False,
                    message="Failed to upload to OSS"
                )
            
            return SaveResult(
                success=True,
                message="File saved successfully",
                modified=datetime.utcnow()
            )
            
        except Exception as e:
            return SaveResult(
                success=False,
                message=str(e)
            )
    
    def create_file(self, path: str, content: str = "") -> CreateResult:
        """
        Create a new file (Upload to OSS).
        
        Args:
            path: Relative path for the new file
            content: Initial content (default empty)
            
        Returns:
            CreateResult indicating success/failure
        """
        # For OSS, creating and saving are similar (put_object)
        save_result = self.save_file(path, content)
        
        return CreateResult(
            success=save_result.success,
            path=normalize_path(path),
            message=save_result.message
        )
    
    def delete_file(self, path: str) -> DeleteResult:
        """
        Delete a file (from OSS).
        
        Args:
            path: Relative path from root
            
        Returns:
            DeleteResult object
        """
        try:
            normalized_path = path.lstrip('/')
            object_name = f"users/{self.user_id}/markdown/{normalized_path}"
            
            success = oss_service.delete_file(object_name)
            
            if success:
                return DeleteResult(
                    success=True,
                    path=normalize_path(path),
                    message="File deleted successfully"
                )
            else:
                return DeleteResult(
                    success=False,
                    path=normalize_path(path),
                    message="Failed to delete file from OSS"
                )
                
        except Exception as e:
            return DeleteResult(success=False, path=normalize_path(path), message=str(e))
    
    def rename_file(self, old_path: str, new_path: str) -> RenameResult:
        """
        Rename a file.
        
        Args:
            old_path: Current relative path
            new_path: New relative path
            
        Returns:
            RenameResult indicating success/failure
        """
        try:
            old_file_path = self._validate_and_resolve(old_path)
            new_file_path = self._validate_and_resolve(new_path)
            
            if not old_file_path.exists():
                return RenameResult(
                    success=False,
                    message="Source file not found",
                    old_path=normalize_path(old_path),
                    new_path=normalize_path(new_path)
                )
            
            if new_file_path.exists():
                return RenameResult(
                    success=False,
                    message="Target file already exists",
                    old_path=normalize_path(old_path),
                    new_path=normalize_path(new_path)
                )
            
            # Ensure parent directory exists
            new_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            old_file_path.rename(new_file_path)
            
            return RenameResult(
                success=True,
                message="File renamed successfully",
                old_path=normalize_path(old_path),
                new_path=normalize_path(new_path)
            )
        except Exception as e:
            return RenameResult(
                success=False,
                message=str(e),
                old_path=normalize_path(old_path),
                new_path=normalize_path(new_path)
            )
    
    def create_directory(self, path: str) -> CreateResult:
        """
        Create a new directory.
        
        Args:
            path: Relative path for the new directory
            
        Returns:
            CreateResult indicating success/failure
        """
        try:
            dir_path = self._validate_and_resolve(path)
            
            if dir_path.exists():
                return CreateResult(
                    success=False,
                    path=normalize_path(path),
                    message="Directory already exists"
                )
            
            dir_path.mkdir(parents=True)
            
            return CreateResult(
                success=True,
                path=normalize_path(path),
                message="Directory created successfully"
            )
        except Exception as e:
            return CreateResult(
                success=False,
                path=normalize_path(path),
                message=str(e)
            )
    
    def delete_directory(self, path: str, recursive: bool = False) -> DeleteResult:
        """
        Delete a directory.
        
        Args:
            path: Relative path to the directory
            recursive: If True, delete non-empty directories
            
        Returns:
            DeleteResult indicating success/failure
        """
        try:
            dir_path = self._validate_and_resolve(path)
            
            if not dir_path.exists():
                return DeleteResult(
                    success=False,
                    message="Directory not found",
                    path=normalize_path(path)
                )
            
            if not dir_path.is_dir():
                return DeleteResult(
                    success=False,
                    message="Path is not a directory",
                    path=normalize_path(path)
                )
            
            # Check if directory is empty
            if any(dir_path.iterdir()) and not recursive:
                return DeleteResult(
                    success=False,
                    message="Directory is not empty. Use recursive=True to delete.",
                    path=normalize_path(path)
                )
            
            if recursive:
                shutil.rmtree(dir_path)
            else:
                dir_path.rmdir()
            
            return DeleteResult(
                success=True,
                message="Directory deleted successfully",
                path=normalize_path(path)
            )
        except Exception as e:
            return DeleteResult(
                success=False,
                message=str(e),
                path=normalize_path(path)
            )
    
    def get_file_modified_time(self, path: str) -> Optional[datetime]:
        """Get the last modified time of a file"""
        try:
            file_path = self._validate_and_resolve(path)
            if file_path.exists():
                return datetime.fromtimestamp(file_path.stat().st_mtime)
        except Exception:
            pass
        return None
