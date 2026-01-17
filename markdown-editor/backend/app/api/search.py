"""
Search API Router - Handles search operations
"""
import os
from fastapi import APIRouter, HTTPException, Query
from typing import List

from app.models.search_models import FileSearchResult, ContentSearchResult
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])

# Get root path from environment or use current directory
ROOT_PATH = os.environ.get("MARKDOWN_EDITOR_ROOT", os.getcwd())


def get_search_service() -> SearchService:
    """Get SearchService instance"""
    return SearchService(ROOT_PATH)


@router.get("/files", response_model=List[FileSearchResult])
async def search_files(
    keyword: str = Query(..., description="Search keyword for file names")
):
    """
    Search files by name.
    Returns files with names containing the keyword (case-insensitive).
    """
    try:
        service = get_search_service()
        return service.search_files(keyword)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/content", response_model=List[ContentSearchResult])
async def search_content(
    keyword: str = Query(..., description="Search keyword or regex pattern"),
    regex: bool = Query(default=False, description="Treat keyword as regex pattern"),
    case_sensitive: bool = Query(default=False, description="Case-sensitive search")
):
    """
    Search content in all markdown files.
    Returns files with matching content and line information.
    """
    try:
        service = get_search_service()
        return service.search_content(keyword, regex=regex, case_sensitive=case_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
