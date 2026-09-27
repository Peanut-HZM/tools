"""
Markdown File Service - Handles all file system operations with user isolation
"""
import os
import shutil
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Set, List

from app.models.file_models import (
    FileNode, FileRawContent, SaveResult, CreateResult,
    RenameResult, DeleteResult, FileItem, BrowseResponse
)
from app.utils.path_utils import (
    validate_path, validate_any_path, is_hidden, is_markdown_file,
    get_relative_path, normalize_path, ensure_user_directory,
    get_file_type, get_extension, is_previewable
)


class MarkdownFileService:
    """Service for file system operations with user isolation"""

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format byte count to human-readable string (e.g. '7.07 MB', '512.00 KB')"""
        if size < 1024:
            return f"{size} B"
        for unit in ("KB", "MB", "GB"):
            size /= 1024
            if size < 1024:
                return f"{size:.2f} {unit}"
        return f"{size:.2f} TB"
    
    def __init__(self, user_id: str, base_path: str = "./data/users", custom_root: Optional[str] = None, allow_any_path: bool = False):
        """
        Initialize MarkdownFileService with user-specific root directory.
        
        Args:
            user_id: The user's ID for file isolation
            base_path: Base path for user data storage
            custom_root: Optional custom root path (overrides default sandbox)
        """
        self.user_id = user_id
        self.base_path = base_path
        self.allow_any_path = allow_any_path
        
        if custom_root and os.path.exists(custom_root) and os.path.isdir(custom_root):
            self._root_path = Path(custom_root).resolve()
        else:
            self._root_path = Path(ensure_user_directory(user_id, base_path)).resolve()
        
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
        gitignore_path = self._root_path / '.gitignore'
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
        """验证路径并返回解析后的 Path 对象"""
        if self.allow_any_path:
            # 真正的相对路径（非 ~、非盘符/根开头、不含 .. 组件）按用户配置的
            # 根目录解析，而不是进程 CWD——否则同样的相对路径会随启动目录
            # 漂移，把文件写到 backend/ 下。其余形态保持 validate_any_path
            # 原有的敏感路径 / 路径遍历拒绝语义与报错文案。
            looks_relative = bool(path) and not path.startswith('~') \
                and not os.path.isabs(path) and not path.startswith(('/', '\\'))
            if looks_relative and '..' not in Path(path).parts:
                is_valid, result = validate_path(path, str(self._root_path))
                if not is_valid:
                    raise ValueError(result)
                return Path(result)
            is_valid, result = validate_any_path(path)
            if not is_valid:
                raise ValueError(result)
            return Path(result)
        else:
            is_valid, result = validate_path(path, str(self._root_path))
            if not is_valid:
                raise ValueError(result)
            return Path(result)
    
    def get_root_path(self) -> str:
        """Get the user's root path"""
        return str(self._root_path)
    
    def get_directory_tree(self, path: str = "", depth: int = -1) -> FileNode:
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
            target_path = Path(self._root_path)
        
        return self._scan_directory(target_path, depth)
    
    def _scan_directory(self, dir_path: Path, depth: int = -1, _rel_path: str = None) -> FileNode:
        """Recursively scan a directory — includes all file types

        性能说明：使用 os.scandir（Windows 下 is_dir/is_file/stat 复用目录
        枚举缓存，几乎无额外系统调用），相对路径通过父级缓存字符串拼接，
        避免旧实现中每个节点 2 次 Path.resolve() + 多次 Path.is_dir/is_file/
        stat 的系统调用（14 万节点曾需约 60 秒）。
        """
        if not isinstance(dir_path, Path):
            dir_path = Path(dir_path)
        if _rel_path is None:
            rel_path = get_relative_path(str(dir_path), str(self._root_path))
            if rel_path == '.':
                rel_path = ''
        else:
            rel_path = _rel_path

        node = FileNode(
            name=dir_path.name or str(self._root_path),
            path=normalize_path(rel_path),
            type="directory",
            children=[]
        )

        try:
            with os.scandir(dir_path) as it:
                entries = list(it)
        except (PermissionError, OSError):
            return node

        dir_entries: list = []
        file_entries: list = []
        for entry in entries:
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            if self._is_ignored(entry.name, is_dir):
                continue
            # 保持与原实现一致的排序语义：目录在前、文件在后，各自按名称升序
            if is_dir:
                dir_entries.append(entry)
            else:
                try:
                    if entry.is_file():
                        file_entries.append(entry)
                except OSError:
                    continue

        dir_entries.sort(key=lambda e: e.name.lower())
        file_entries.sort(key=lambda e: e.name.lower())

        child_rel_base = f"{rel_path}/" if rel_path else ""

        for entry in dir_entries:
            child_rel_path = f"{child_rel_base}{entry.name}"
            if depth == 0:
                # 如果深度限制为 0，不再递归扫描子目录
                node.children.append(FileNode(
                    name=entry.name,
                    path=normalize_path(child_rel_path),
                    type="directory",
                    children=[]
                ))
            else:
                # 递归扫描，深度减 1（-1 表示无限制）
                next_depth = depth - 1 if depth > 0 else -1
                child_node = self._scan_directory(
                    Path(entry.path), next_depth, child_rel_path
                )
                # Include directory if it has any files (not just markdown)
                if child_node.children:
                    node.children.append(child_node)

        for entry in file_entries:
            stat = entry.stat()
            node.children.append(FileNode(
                name=entry.name,
                path=normalize_path(f"{child_rel_base}{entry.name}"),
                type="file",
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                extension=get_extension(entry.name),
                file_type=get_file_type(entry.name),
                previewable=is_previewable(entry.name),
            ))

        return node

    def read_file_raw(self, path: str) -> FileRawContent:
        """
        读取文件原始内容（支持二进制文件）

        Args:
            path: 相对路径

        Returns:
            FileRawContent 包含 content_type 和编码后的数据

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 路径无效或文件过大
        """
        file_path = self._validate_and_resolve(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        # 获取文件信息
        stat = file_path.stat()
        ext = file_path.suffix.lower()

        # 确定 MIME type
        content_type = self._get_content_type(ext)

        # 文件大小限制：文本文件 10MB，二进制文件 50MB
        # 使用与读取分支相同的谓词，避免对 .js 等文件走二进制限制却以文本解码的不一致
        is_text = self._is_text_content_type(content_type)
        max_size = 10 * 1024 * 1024 if is_text else 50 * 1024 * 1024
        if stat.st_size > max_size:
            raise ValueError(
                f"文件过大：{self._format_bytes(stat.st_size)}（最大 {self._format_bytes(max_size)}）"
            )

        # 读取文件内容
        if is_text:
            # 文本文件：直接读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            except UnicodeDecodeError:
                # 如果 UTF-8 失败，尝试 latin-1（不会抛出异常）
                with open(file_path, 'r', encoding='latin-1') as f:
                    text_content = f.read()

            return FileRawContent(
                path=normalize_path(path),
                content_type=content_type,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                text=text_content
            )
        else:
            # 二进制文件：base64 编码
            with open(file_path, 'rb') as f:
                binary_data = f.read()
            encoded_data = base64.b64encode(binary_data).decode('utf-8')

            return FileRawContent(
                path=normalize_path(path),
                content_type=content_type,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                data=encoded_data
            )

    def _get_content_type(self, ext: str) -> str:
        """获取文件 MIME type

        Args:
            ext: 文件扩展名（含点号）

        Returns:
            MIME type 字符串
        """
        mime_types = {
            # 文本类型
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.yaml': 'text/yaml',
            '.yml': 'text/yaml',
            '.toml': 'text/plain',
            '.ini': 'text/plain',
            '.conf': 'text/plain',
            # 代码类型
            '.js': 'text/javascript',
            '.ts': 'text/typescript',
            '.tsx': 'text/typescript',
            '.jsx': 'text/javascript',
            '.py': 'text/x-python',
            '.java': 'text/x-java',
            '.go': 'text/x-go',
            '.rs': 'text/x-rust',
            '.c': 'text/x-c',
            '.cpp': 'text/x-c++',
            '.h': 'text/x-c',
            '.hpp': 'text/x-c++',
            '.rb': 'text/x-ruby',
            '.php': 'text/x-php',
            '.sql': 'text/x-sql',
            '.sh': 'text/x-sh',
            '.bash': 'text/x-sh',
            '.scss': 'text/css',
            '.sass': 'text/css',
            '.less': 'text/css',
            # 文档类型
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            # 图片类型
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.ico': 'image/x-icon',
            # 音视频类型
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            # 压缩包类型
            '.zip': 'application/zip',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
        }
        return mime_types.get(ext, 'application/octet-stream')

    def _is_text_content_type(self, content_type: str) -> bool:
        """判断 content_type 是否为文本类型

        Args:
            content_type: MIME type 字符串

        Returns:
            是否为文本类型
        """
        # 文本类型判断规则
        if content_type.startswith('text/'):
            return True
        # 某些 application 类型也是文本
        text_application_types = {
            'application/json',
            'application/xml',
            'application/javascript',
            'application/typescript',
            'application/x-sh',
            'application/x-shellscript',
            'application/x-yaml',
            'application/toml',
            'application/x-ini',
            'application/x-httpd-php',
        }
        return content_type in text_application_types

    def save_file(self, path: str, content: str) -> SaveResult:
        """
        Save content to a file.
        
        Args:
            path: Relative path to the file
            content: Content to save
            
        Returns:
            SaveResult indicating success/failure
        """
        file_path = self._validate_and_resolve(path)
        if file_path.exists() and not file_path.is_file():
            return SaveResult(success=False, message="Path is not a file")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return SaveResult(
            success=True,
            message="File saved successfully",
            modified=datetime.utcnow()
        )
    
    def create_file(self, path: str, content: str = "") -> CreateResult:
        """
        Create a new file.
        
        Args:
            path: Relative path for the new file
            content: Initial content (default empty)
            
        Returns:
            CreateResult indicating success/failure
        """
        file_path = self._validate_and_resolve(path)
        if file_path.exists():
            return CreateResult(success=False, path=normalize_path(path), message="File already exists")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return CreateResult(success=True, path=normalize_path(path), message="File created successfully")
    
    def delete_file(self, path: str) -> DeleteResult:
        """
        Delete a file.
        
        Args:
            path: Relative path from root
            
        Returns:
            DeleteResult object
        """
        file_path = self._validate_and_resolve(path)
        try:
            if not file_path.exists():
                return DeleteResult(success=False, path=normalize_path(path), message="File not found")
            if not file_path.is_file():
                return DeleteResult(success=False, path=normalize_path(path), message="Path is not a file")
            file_path.unlink()
            return DeleteResult(success=True, path=normalize_path(path), message="File deleted successfully")
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

    def list_directory(self, path: str = "") -> dict:
        """
        List contents of a directory for the browser dialog.
        Returns directories and files separately.

        Args:
            path: Relative path of directory to browse (empty string for root)

        Returns:
            dict with current_path, breadcrumbs, directories, files
        """
        root_path = (
            self._root_path
            if isinstance(self._root_path, Path)
            else Path(self._root_path)
        )
        if path:
            target_path = self._validate_and_resolve(path)
        else:
            target_path = root_path

        if not target_path.exists() or not target_path.is_dir():
            raise ValueError(f"Directory not found: {path}")

        directories = []
        files = []

        try:
            entries = sorted(
                target_path.iterdir(),
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
        except PermissionError:
            return {
                "current_path": str(target_path),
                "breadcrumbs": [],
                "directories": [],
                "files": [],
            }

        for entry in entries:
            if self._is_ignored(entry.name, entry.is_dir()):
                continue

            entry_rel_path = get_relative_path(str(entry), str(self._root_path))

            if entry.is_dir():
                try:
                    has_children = any(
                        not self._is_ignored(c.name, c.is_dir())
                        for c in entry.iterdir()
                    )
                except PermissionError:
                    has_children = False
                directories.append({
                    "name": entry.name,
                    "path": normalize_path(entry_rel_path),
                    "has_children": has_children,
                })
            elif entry.is_file():
                stat = entry.stat()
                files.append({
                    "name": entry.name,
                    "path": normalize_path(entry_rel_path),
                    "extension": get_extension(entry.name),
                    "file_type": get_file_type(entry.name),
                    "previewable": is_previewable(entry.name),
                    "size": stat.st_size,
                })

        breadcrumbs = self._build_breadcrumbs(target_path)

        return {
            "current_path": normalize_path(
                get_relative_path(str(target_path), str(self._root_path))
            ),
            "breadcrumbs": breadcrumbs,
            "directories": directories,
            "files": files,
        }

    def _build_breadcrumbs(self, target_path: Path) -> list:
        """Build breadcrumb navigation from root to target.

        Args:
            target_path: Absolute path to build breadcrumbs for

        Returns:
            List of dicts with 'name' and 'path' keys
        """
        root = (
            self._root_path
            if isinstance(self._root_path, Path)
            else Path(self._root_path)
        ).resolve()
        # 根目录面包屑使用固定的"根目录"名称，而不是 root.name
        breadcrumbs = [{"name": "根目录", "path": ""}]

        try:
            relative = target_path.relative_to(root)
        except ValueError:
            return breadcrumbs

        current_parts: list = []
        for part in relative.parts:
            current_parts.append(part)
            breadcrumbs.append({
                "name": part,
                "path": normalize_path("/".join(current_parts)),
            })

        return breadcrumbs

    def get_file_paths(self, relative_path: str) -> dict:
        """
        Get absolute and relative paths for a file.

        Args:
            relative_path: Relative path to the file (from root)

        Returns:
            dict with absolute_path, relative_path, file_name, root_path
        """
        resolved = self._validate_and_resolve(relative_path)
        return {
            "absolute_path": str(resolved),
            "relative_path": normalize_path(relative_path),
            "file_name": resolved.name,
            "root_path": str(self._root_path),
        }

    # ---------------------------------------------------------------------------
    # Task 3: 任意路径浏览 & 文件操作
    # ---------------------------------------------------------------------------

    def browse_directory(self, path: str = "", page: int = 1, page_size: int = 100) -> BrowseResponse:
        """浏览任意目录（支持分页）

        Args:
            path: 目标路径（空字符串表示根目录；allow_any_path 模式下默认为 /）
            page: 页码（从 1 开始）
            page_size: 每页数量（默认 100）

        Returns:
            BrowseResponse 包含文件列表和分页信息
        """
        if path:
            target_path = self._validate_and_resolve(path)
        elif self.allow_any_path:
            target_path = Path("/").resolve()
        else:
            target_path = self._root_path

        if not target_path.exists() or not target_path.is_dir():
            raise ValueError(f"目录不存在：{path}")

        # 获取所有条目
        try:
            entries = sorted(
                target_path.iterdir(),
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
        except PermissionError:
            raise ValueError(f"无权限访问目录：{path}")

        # 过滤隐藏文件和忽略文件
        items = []
        for entry in entries:
            if self._is_ignored(entry.name, entry.is_dir()):
                continue

            stat = entry.stat()
            item = FileItem(
                name=entry.name,
                path=str(entry),
                type="directory" if entry.is_dir() else "file",
                size=stat.st_size if entry.is_file() else 0,
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                extension=get_extension(entry.name) if entry.is_file() else "",
                is_previewable=is_previewable(entry.name) if entry.is_file() else False,
            )
            items.append(item)

        # 分页
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = items[start:end]

        # 构建面包屑
        breadcrumbs = self._build_breadcrumbs_for_any_path(target_path)

        return BrowseResponse(
            current_path=str(target_path),
            breadcrumbs=breadcrumbs,
            items=paginated_items,
            total=total,
            has_more=end < total,
        )

    def _build_breadcrumbs_for_any_path(self, target_path: Path) -> List[dict]:
        """为任意路径构建面包屑导航"""
        breadcrumbs: List[dict] = []
        resolved = target_path.resolve()

        # 根目录
        breadcrumbs.append({"name": "/", "path": "/"})

        # 逐级构建路径
        current = ""
        for part in resolved.parts:
            if part == '/':
                continue
            current = current + "/" + part
            breadcrumbs.append({"name": part, "path": current})

        return breadcrumbs

    def copy_item(self, source_path: str, target_path: str) -> dict:
        """复制文件或文件夹

        Args:
            source_path: 源路径
            target_path: 目标路径

        Returns:
            dict with success and message
        """
        source = self._validate_and_resolve(source_path)
        target = self._validate_and_resolve(target_path)

        if not source.exists():
            return {"success": False, "message": "源路径不存在"}

        if target.exists():
            return {"success": False, "message": "目标路径已存在"}

        try:
            if source.is_dir():
                shutil.copytree(str(source), str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(target))

            return {"success": True, "message": "复制成功"}
        except Exception as e:
            return {"success": False, "message": f"复制失败：{str(e)}"}

    def move_item(self, source_path: str, target_path: str) -> dict:
        """移动文件或文件夹

        Args:
            source_path: 源路径
            target_path: 目标路径

        Returns:
            dict with success and message
        """
        source = self._validate_and_resolve(source_path)
        target = self._validate_and_resolve(target_path)

        if not source.exists():
            return {"success": False, "message": "源路径不存在"}

        if target.exists():
            return {"success": False, "message": "目标路径已存在"}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            return {"success": True, "message": "移动成功"}
        except Exception as e:
            return {"success": False, "message": f"移动失败：{str(e)}"}

    def get_download_path(self, path: str) -> Path:
        """获取文件下载路径（验证文件存在且不是敏感路径）

        Args:
            path: 文件路径

        Returns:
            解析后的文件路径

        Raises:
            ValueError: 文件不存在或路径无效
        """
        file_path = self._validate_and_resolve(path)

        if not file_path.exists():
            raise ValueError(f"文件不存在：{path}")

        if not file_path.is_file():
            raise ValueError(f"路径不是文件：{path}")

        # 文件大小限制 100MB
        if file_path.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("文件过大（最大 100MB）")

        return file_path

    def get_file_info(self, path: str) -> dict:
        """获取文件或目录的详细信息

        Args:
            path: 文件/目录路径

        Returns:
            dict 包含 name, path, type, size, modified_at, extension, is_previewable

        Raises:
            ValueError: 路径不存在
        """
        file_path = self._validate_and_resolve(path)

        if not file_path.exists():
            raise ValueError(f"路径不存在：{path}")

        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path),
            "type": "directory" if file_path.is_dir() else "file",
            "size": stat.st_size if file_path.is_file() else 0,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": get_extension(file_path.name) if file_path.is_file() else "",
            "is_previewable": is_previewable(file_path.name) if file_path.is_file() else False,
        }

    def delete_item(self, path: str) -> dict:
        """删除文件或文件夹

        自动判断类型并执行删除。

        Args:
            path: 文件/文件夹路径

        Returns:
            dict with success and message
        """
        target = self._validate_and_resolve(path)

        if not target.exists():
            return {"success": False, "message": "路径不存在"}

        if target.is_dir():
            result = self.delete_directory(path, recursive=True)
            return {"success": result.success, "message": result.message}
        else:
            result = self.delete_file(path)
            return {"success": result.success, "message": result.message}

    def rename_item(self, source_path: str, new_name: str) -> dict:
        """重命名文件或文件夹

        验证源路径和目标路径均合法后执行重命名。

        Args:
            source_path: 源路径
            new_name: 新名称

        Returns:
            dict with success and message
        """
        source = self._validate_and_resolve(source_path)

        if not source.exists():
            return {"success": False, "message": "源路径不存在"}

        # 构造目标路径并验证其合法性
        target = source.parent / new_name
        try:
            target = self._validate_and_resolve(str(target))
        except ValueError as e:
            return {"success": False, "message": str(e)}

        if target.exists():
            return {"success": False, "message": "目标路径已存在"}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            return {"success": True, "message": "重命名成功"}
        except Exception as e:
            return {"success": False, "message": f"重命名失败：{str(e)}"}

    def upload_file(self, parent_path: str, filename: str, content_bytes: bytes) -> dict:
        """上传文件到指定目录

        验证父路径合法性，检查文件大小限制，写入文件。

        Args:
            parent_path: 目标目录路径
            filename: 文件名
            content_bytes: 文件内容

        Returns:
            dict with success and message
        """
        MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

        if len(content_bytes) > MAX_UPLOAD_SIZE:
            return {"success": False, "message": "文件过大（最大 100MB）"}

        target_dir = self._validate_and_resolve(parent_path)

        if not target_dir.is_dir():
            return {"success": False, "message": "目标路径不是目录"}

        target_file = target_dir / filename

        # 验证目标文件路径合法性
        try:
            target_file = self._validate_and_resolve(str(target_file))
        except ValueError as e:
            return {"success": False, "message": str(e)}

        if target_file.exists():
            return {"success": False, "message": "目标文件已存在"}

        try:
            target_file.write_bytes(content_bytes)
            return {"success": True, "message": "上传成功"}
        except Exception as e:
            return {"success": False, "message": f"上传失败：{str(e)}"}
