"""
Pydantic models for search operations
"""
from pydantic import BaseModel
from typing import List


class FileSearchResult(BaseModel):
    """Result of file name search"""
    name: str
    path: str
    match: str  # The matched portion of the name


class ContentMatch(BaseModel):
    """A single content match within a file"""
    line: int
    content: str
    column: int


class ContentSearchResult(BaseModel):
    """Result of content search for a single file"""
    file: str
    matches: List[ContentMatch]


class SearchResponse(BaseModel):
    """Response for search operations"""
    results: List[FileSearchResult] | List[ContentSearchResult]
    total: int
