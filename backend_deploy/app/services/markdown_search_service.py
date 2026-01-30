"""
Markdown Search Service - Handles file and content search with user isolation
"""
import os
import re
from pathlib import Path
from typing import List

from app.models.search_models import FileSearchResult, ContentMatch, ContentSearchResult
from app.utils.path_utils import is_hidden, is_markdown_file, normalize_path, get_relative_path, ensure_user_directory


class MarkdownSearchService:
    """Service for search operations with user isolation"""
    
    def __init__(self, user_id: str, base_path: str = "./data/users"):
        """
        Initialize MarkdownSearchService with user-specific root directory.
        
        Args:
            user_id: The user's ID for search isolation
            base_path: Base path for user data storage
        """
        self.user_id = user_id
        self.base_path = base_path
        self.root_path = Path(ensure_user_directory(user_id, base_path)).resolve()
    
    def _get_all_markdown_files(self) -> List[Path]:
        """Get all markdown files in the user's root directory recursively"""
        markdown_files = []
        
        for root, dirs, files in os.walk(self.root_path):
            # Filter out hidden directories
            dirs[:] = [d for d in dirs if not is_hidden(d)]
            
            for file in files:
                if is_markdown_file(file) and not is_hidden(file):
                    markdown_files.append(Path(root) / file)
        
        return markdown_files
    
    def search_files(self, keyword: str) -> List[FileSearchResult]:
        """
        Search files by name.
        
        Args:
            keyword: The search keyword (case-insensitive)
            
        Returns:
            List of FileSearchResult matching the keyword
        """
        if not keyword:
            return []
        
        results = []
        keyword_lower = keyword.lower()
        
        for file_path in self._get_all_markdown_files():
            name = file_path.name
            name_lower = name.lower()
            
            if keyword_lower in name_lower:
                rel_path = get_relative_path(str(file_path), str(self.root_path))
                results.append(FileSearchResult(
                    name=name,
                    path=normalize_path(rel_path),
                    match=keyword
                ))
        
        return results
    
    def search_content(
        self,
        keyword: str,
        regex: bool = False,
        case_sensitive: bool = False
    ) -> List[ContentSearchResult]:
        """
        Search content in all markdown files.
        
        Args:
            keyword: The search keyword or regex pattern
            regex: If True, treat keyword as regex pattern
            case_sensitive: If True, perform case-sensitive search
            
        Returns:
            List of ContentSearchResult with matches
        """
        if not keyword:
            return []
        
        results = []
        
        # Compile pattern
        if regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(keyword, flags)
            except re.error:
                # Invalid regex, return empty results
                return []
        else:
            # Escape special regex characters for literal search
            escaped = re.escape(keyword)
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(escaped, flags)
        
        for file_path in self._get_all_markdown_files():
            try:
                content = file_path.read_text(encoding='utf-8')
            except Exception:
                continue
            
            matches = []
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, start=1):
                for match in pattern.finditer(line):
                    matches.append(ContentMatch(
                        line=line_num,
                        content=line.strip(),
                        column=match.start() + 1
                    ))
            
            if matches:
                rel_path = get_relative_path(str(file_path), str(self.root_path))
                results.append(ContentSearchResult(
                    file=normalize_path(rel_path),
                    matches=matches
                ))
        
        return results
