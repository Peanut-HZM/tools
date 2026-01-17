"""
File API Router - Handles file operations
"""
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.models.file_models import (
    FileNode, FileContent, SaveRequest, SaveResult,
    CreateRequest, CreateResult, RenameRequest, RenameResult,
    DeleteResult, ErrorResponse
)
from app.services.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])

# Get root path from environment or use current directory
_current_root_path = os.environ.get("MARKDOWN_EDITOR_ROOT", os.getcwd())


class SetRootRequest(BaseModel):
    """Request to set root directory"""
    path: str


class RootPathResponse(BaseModel):
    """Response with current root path"""
    path: str
    exists: bool


def get_file_service() -> FileService:
    """Get FileService instance"""
    return FileService(_current_root_path)


@router.get("/root", response_model=RootPathResponse)
async def get_root_path():
    """Get current root directory path"""
    return RootPathResponse(
        path=_current_root_path,
        exists=os.path.isdir(_current_root_path)
    )


@router.post("/root", response_model=RootPathResponse)
async def set_root_path(request: SetRootRequest):
    """Set root directory path"""
    global _current_root_path
    
    path = request.path
    
    # Validate path exists and is a directory
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
    
    _current_root_path = os.path.abspath(path)
    
    return RootPathResponse(
        path=_current_root_path,
        exists=True
    )


@router.get("/tree", response_model=FileNode)
async def get_directory_tree(
    root: Optional[str] = Query(default="", description="Relative path from root")
):
    """
    Get directory tree structure.
    Returns only Markdown files and directories containing them.
    """
    try:
        service = get_file_service()
        return service.get_directory_tree(root)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/read", response_model=FileContent)
async def read_file(
    path: str = Query(..., description="Relative path to the file")
):
    """
    Read file content with metadata.
    """
    try:
        service = get_file_service()
        return service.read_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/save", response_model=SaveResult)
async def save_file(request: SaveRequest):
    """
    Save content to an existing file.
    """
    try:
        service = get_file_service()
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


@router.post("/create", response_model=CreateResult)
async def create_file(request: CreateRequest):
    """
    Create a new file.
    """
    try:
        service = get_file_service()
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


@router.delete("/delete", response_model=DeleteResult)
async def delete_file(
    path: str = Query(..., description="Relative path to the file")
):
    """
    Delete a file.
    """
    try:
        service = get_file_service()
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


@router.post("/rename", response_model=RenameResult)
async def rename_file(request: RenameRequest):
    """
    Rename a file.
    """
    try:
        service = get_file_service()
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


@router.post("/directory/create", response_model=CreateResult)
async def create_directory(
    path: str = Query(..., description="Relative path for the new directory")
):
    """
    Create a new directory.
    """
    try:
        service = get_file_service()
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


@router.delete("/directory/delete", response_model=DeleteResult)
async def delete_directory(
    path: str = Query(..., description="Relative path to the directory"),
    recursive: bool = Query(default=False, description="Delete non-empty directories")
):
    """
    Delete a directory.
    Requires recursive=True to delete non-empty directories.
    """
    try:
        service = get_file_service()
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
