"""
Markdown Editor API Router - Handles file, config, and search operations
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List

from app.models.file_models import (
    FileNode, FileContent, SaveRequest, SaveResult,
    CreateRequest, CreateResult, RenameRequest, RenameResult,
    DeleteResult, RootPathResponse
)
from app.models.config_models import EditorConfig
from app.models.search_models import FileSearchResult, ContentSearchResult
from app.services.markdown_file_service import MarkdownFileService
from app.services.markdown_config_service import MarkdownConfigService
from app.services.markdown_search_service import MarkdownSearchService
from app.middleware.auth_middleware import get_current_user_id

router = APIRouter(prefix="/api/markdown-editor", tags=["markdown-editor"])


from pydantic import BaseModel

class RootPathRequest(BaseModel):
    path: str

def get_file_service(user_id: str = Depends(get_current_user_id)) -> MarkdownFileService:
    """Get MarkdownFileService instance for the current user"""
    config_service = MarkdownConfigService(user_id)
    config = config_service.load_config()
    return MarkdownFileService(user_id, custom_root=config.root_path)


def get_config_service(user_id: str = Depends(get_current_user_id)) -> MarkdownConfigService:
    """Get MarkdownConfigService instance for the current user"""
    return MarkdownConfigService(user_id)


def get_search_service(user_id: str = Depends(get_current_user_id)) -> MarkdownSearchService:
    """Get MarkdownSearchService instance for the current user"""
    return MarkdownSearchService(user_id)


# ==================== File Operations ====================

@router.get("/files/root", response_model=RootPathResponse)
async def get_root_path(user_id: str = Depends(get_current_user_id)):
    """Get current user's root directory path"""
    service = get_file_service(user_id)
    root_path = service.get_root_path()
    return RootPathResponse(
        path=root_path,
        exists=True
    )


@router.post("/files/root", response_model=RootPathResponse)
async def update_root_path(
    request: RootPathRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Update user's root directory path"""
    # Verify path exists
    import os
    if not os.path.exists(request.path) or not os.path.isdir(request.path):
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")
        
    # Update config
    config_service = MarkdownConfigService(user_id)
    config = config_service.load_config()
    config.root_path = request.path
    config_service.save_config(config)
    
    return RootPathResponse(
        path=request.path,
        exists=True
    )


@router.get("/files/tree", response_model=FileNode)
async def get_directory_tree(
    root: Optional[str] = Query(default="", description="Relative path from root"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get directory tree structure.
    Returns only Markdown files and directories containing them.
    """
    try:
        service = get_file_service(user_id)
        return service.get_directory_tree(root)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/files/read", response_model=FileContent)
async def read_file(
    path: str = Query(..., description="Relative path to the file"),
    user_id: str = Depends(get_current_user_id)
):
    """Read file content with metadata."""
    try:
        service = get_file_service(user_id)
        return service.read_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/files/save", response_model=SaveResult)
async def save_file(
    request: SaveRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Save content to an existing file."""
    try:
        service = get_file_service(user_id)
        result = service.save_file(request.path, request.content)
        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/files/create", response_model=CreateResult)
async def create_file(
    request: CreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new file."""
    try:
        service = MarkdownFileService(user_id)
        result = service.create_file(request.path, request.content or "")
        if not result.success:
            if "already exists" in result.message.lower():
                raise HTTPException(status_code=409, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.delete("/files/delete", response_model=DeleteResult)
async def delete_file(
    path: str = Query(..., description="Relative path to the file"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a file."""
    try:
        service = MarkdownFileService(user_id)
        result = service.delete_file(path)
        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/files/rename", response_model=RenameResult)
async def rename_file(
    request: RenameRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Rename a file."""
    try:
        service = MarkdownFileService(user_id)
        result = service.rename_file(request.old_path, request.new_path)
        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "already exists" in result.message.lower():
                raise HTTPException(status_code=409, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/files/directory/create", response_model=CreateResult)
async def create_directory(
    path: str = Query(..., description="Relative path for the new directory"),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new directory."""
    try:
        service = MarkdownFileService(user_id)
        result = service.create_directory(path)
        if not result.success:
            if "already exists" in result.message.lower():
                raise HTTPException(status_code=409, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.delete("/files/directory/delete", response_model=DeleteResult)
async def delete_directory(
    path: str = Query(..., description="Relative path to the directory"),
    recursive: bool = Query(default=False, description="Delete non-empty directories"),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a directory. Requires recursive=True to delete non-empty directories."""
    try:
        service = MarkdownFileService(user_id)
        result = service.delete_directory(path, recursive)
        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "not empty" in result.message.lower():
                raise HTTPException(status_code=400, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ==================== Config Operations ====================

@router.get("/config", response_model=EditorConfig)
async def get_config(user_id: str = Depends(get_current_user_id)):
    """Get current user's configuration. Returns default if no config exists."""
    try:
        service = MarkdownConfigService(user_id)
        return service.load_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading config: {str(e)}")


@router.post("/config", response_model=EditorConfig)
async def save_config(
    config: EditorConfig,
    user_id: str = Depends(get_current_user_id)
):
    """Save user configuration."""
    try:
        service = MarkdownConfigService(user_id)
        success = service.save_config(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving config: {str(e)}")


# ==================== Search Operations ====================

@router.get("/search/files", response_model=List[FileSearchResult])
async def search_files(
    keyword: str = Query(..., description="Search keyword for file names"),
    user_id: str = Depends(get_current_user_id)
):
    """Search files by name. Returns files with names containing the keyword."""
    try:
        service = MarkdownSearchService(user_id)
        return service.search_files(keyword)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/search/content", response_model=List[ContentSearchResult])
async def search_content(
    keyword: str = Query(..., description="Search keyword or regex pattern"),
    regex: bool = Query(default=False, description="Treat keyword as regex pattern"),
    case_sensitive: bool = Query(default=False, description="Case-sensitive search"),
    user_id: str = Depends(get_current_user_id)
):
    """Search content in all markdown files. Returns files with matching content."""
    try:
        service = MarkdownSearchService(user_id)
        return service.search_content(keyword, regex=regex, case_sensitive=case_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
