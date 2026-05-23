"""
Markdown Editor API Router - Handles file, config, and search operations
"""

from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from typing import Optional, List
import os
import uuid
import io

from app.models.file_models import (
    FileNode,
    FileContent,
    SaveRequest,
    SaveResult,
    CreateRequest,
    CreateResult,
    RenameRequest,
    RenameResult,
    DeleteResult,
    RootPathResponse,
)
from app.models.config_models import EditorConfig
from app.models.search_models import FileSearchResult, ContentSearchResult
from app.services.markdown_file_service import MarkdownFileService
from app.services.markdown_config_service import MarkdownConfigService
from app.services.markdown_search_service import MarkdownSearchService
from app.services.oss_service import oss_service
from app.middleware.auth_middleware import get_current_user_id

router = APIRouter(prefix="/api/markdown-editor", tags=["markdown-editor"])


from pydantic import BaseModel


class RootPathRequest(BaseModel):
    path: str


def get_file_service(
    user_id: str = Depends(get_current_user_id),
) -> MarkdownFileService:
    """Get MarkdownFileService instance for the current user"""
    config_service = MarkdownConfigService(user_id)
    config = config_service.load_config()
    return MarkdownFileService(user_id, custom_root=config.root_path)


def get_config_service(
    user_id: str = Depends(get_current_user_id),
) -> MarkdownConfigService:
    """Get MarkdownConfigService instance for the current user"""
    return MarkdownConfigService(user_id)


def get_search_service(
    user_id: str = Depends(get_current_user_id),
) -> MarkdownSearchService:
    """Get MarkdownSearchService instance for the current user"""
    return MarkdownSearchService(user_id)


@router.post("/files/upload", response_model=SaveResult)
async def upload_markdown_file(
    file: UploadFile = File(...),
    path: str = Query(default="", description="Target relative path (folder)"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Upload a Markdown file to OSS and save it in the user's workspace.
    If path is provided, it will be saved in that folder.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Check extension
    filename = file.filename
    if not filename.lower().endswith((".md", ".markdown")):
        raise HTTPException(
            status_code=400, detail="Only Markdown files (.md, .markdown) are allowed"
        )

    try:
        service = get_file_service(user_id)

        # Read content
        content_bytes = await file.read()
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400, detail="File must be UTF-8 encoded text"
            )

        # Construct target path
        target_path = os.path.join(path, filename) if path else filename
        target_path = target_path.replace("\\", "/")  # Normalize separators

        # Use existing save_file logic which handles OSS upload
        result = service.save_file(target_path, content)

        if not result.success:
            raise HTTPException(
                status_code=500, detail=result.error or "Failed to save file"
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ==================== File Operations ====================


@router.get("/files/root", response_model=RootPathResponse)
async def get_root_path(user_id: str = Depends(get_current_user_id)):
    """Get current user's root directory path"""
    service = get_file_service(user_id)
    root_path = service.get_root_path()
    return RootPathResponse(path=root_path, exists=True)


@router.post("/files/root", response_model=RootPathResponse)
async def update_root_path(
    request: RootPathRequest, user_id: str = Depends(get_current_user_id)
):
    """Update user's root directory path"""
    # Verify path exists
    import os

    if not os.path.exists(request.path) or not os.path.isdir(request.path):
        raise HTTPException(
            status_code=400, detail="Path does not exist or is not a directory"
        )

    # Update config
    config_service = MarkdownConfigService(user_id)
    config = config_service.load_config()
    config.root_path = request.path
    config_service.save_config(config)

    return RootPathResponse(path=request.path, exists=True)


@router.get("/files/tree", response_model=FileNode)
async def get_directory_tree(
    root: Optional[str] = Query(default="", description="Relative path from root"),
    user_id: str = Depends(get_current_user_id),
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
    user_id: str = Depends(get_current_user_id),
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
async def save_file(request: SaveRequest, user_id: str = Depends(get_current_user_id)):
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
    request: CreateRequest, user_id: str = Depends(get_current_user_id)
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
    user_id: str = Depends(get_current_user_id),
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
    request: RenameRequest, user_id: str = Depends(get_current_user_id)
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
    user_id: str = Depends(get_current_user_id),
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
    user_id: str = Depends(get_current_user_id),
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
    config: EditorConfig, user_id: str = Depends(get_current_user_id)
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
    user_id: str = Depends(get_current_user_id),
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
    user_id: str = Depends(get_current_user_id),
):
    """Search content in all markdown files. Returns files with matching content."""
    try:
        service = MarkdownSearchService(user_id)
        return service.search_content(
            keyword, regex=regex, case_sensitive=case_sensitive
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


# ==================== OSS Operations ====================


class OssUploadMarkdownResponse(BaseModel):
    """Response model for OSS markdown upload"""

    success: bool
    file_path: str
    url: str
    filename: str
    message: str


class OssReadMarkdownResponse(BaseModel):
    """Response model for reading markdown from OSS"""

    success: bool
    content: str
    filename: str
    message: str


class OssSaveMarkdownRequest(BaseModel):
    """Request model for saving markdown to OSS"""

    file_path: str
    content: str


class OssSaveMarkdownResponse(BaseModel):
    """Response model for saving markdown to OSS"""

    success: bool
    message: str


@router.post("/oss/upload", response_model=OssUploadMarkdownResponse)
async def upload_markdown_to_oss(
    file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)
):
    """
    Upload a Markdown file to OSS.
    Only accepts .md, .markdown, .txt files.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    # Validate file type
    allowed_extensions = {".md", ".markdown", ".txt"}
    file_extension = os.path.splitext(file.filename or "")[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only {', '.join(allowed_extensions)} files are allowed",
        )

    try:
        # Read file content
        content = await file.read()
        file_size = len(content)

        # Generate unique filename
        original_filename = file.filename or f"document{file_extension}"
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Organize files by user_id in OSS
        object_name = f"markdown/{user_id}/{unique_filename}"

        # Upload to OSS
        file_obj = io.BytesIO(content)
        url = oss_service.upload_file(
            object_name=object_name,
            data=file_obj,
            size=file_size,
            content_type=file.content_type or "text/markdown",
            uploaded_by=user_id,
        )

        if not url:
            raise HTTPException(status_code=500, detail="Failed to upload file to OSS")

        return OssUploadMarkdownResponse(
            success=True,
            file_path=object_name,
            url=url,
            filename=original_filename,
            message="File uploaded successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@router.get("/oss/read", response_model=OssReadMarkdownResponse)
async def read_markdown_from_oss(
    file_path: str = Query(..., description="OSS file path"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Read a Markdown file from OSS.
    Only allows reading files belonging to the current user.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    # Security check: Ensure user can only read their own files
    if not file_path.startswith(f"markdown/{user_id}/"):
        raise HTTPException(
            status_code=403, detail="Access denied: You can only read your own files"
        )

    try:
        # Get object from OSS
        result = oss_service.get_object(file_path)
        content = result.read().decode("utf-8")

        filename = os.path.basename(file_path)

        return OssReadMarkdownResponse(
            success=True,
            content=content,
            filename=filename,
            message="File read successfully",
        )
    except Exception as e:
        if "not found" in str(e).lower() or "NoSuchKey" in str(e):
            raise HTTPException(status_code=404, detail="File not found in OSS")
        raise HTTPException(status_code=500, detail=f"Read error: {str(e)}")


@router.post("/oss/save", response_model=OssSaveMarkdownResponse)
async def save_markdown_to_oss(
    request: OssSaveMarkdownRequest, user_id: str = Depends(get_current_user_id)
):
    """
    Save Markdown content to OSS.
    Only allows saving files belonging to the current user.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    # Security check: Ensure user can only save their own files
    if not request.file_path.startswith(f"markdown/{user_id}/"):
        raise HTTPException(
            status_code=403, detail="Access denied: You can only save your own files"
        )

    try:
        # Convert content to bytes
        content_bytes = request.content.encode("utf-8")
        file_size = len(content_bytes)

        # Upload to OSS
        file_obj = io.BytesIO(content_bytes)
        url = oss_service.upload_file(
            object_name=request.file_path,
            data=file_obj,
            size=file_size,
            content_type="text/markdown",
            uploaded_by=user_id,
        )

        if not url:
            raise HTTPException(status_code=500, detail="Failed to save file to OSS")

        return OssSaveMarkdownResponse(success=True, message="File saved successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save error: {str(e)}")


class OssFileInfo(BaseModel):
    """OSS file information model"""

    file_path: str
    filename: str
    size: int
    last_modified: Optional[str] = None


@router.get("/oss/list", response_model=List[OssFileInfo])
async def list_oss_markdown_files(user_id: str = Depends(get_current_user_id)):
    """
    List all Markdown files in OSS for the current user.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    try:
        # List files from OSS (filtered by user)
        prefix = f"markdown/{user_id}/"
        files = []

        # Get files from OSS directly
        for item in oss_service.list_files(prefix=prefix, max_keys=1000):
            if item["key"].endswith((".md", ".markdown", ".txt")):
                files.append(
                    OssFileInfo(
                        file_path=item["key"],
                        filename=os.path.basename(item["key"]),
                        size=item["size"],
                        last_modified=item["last_modified"].isoformat()
                        if item["last_modified"]
                        else None,
                    )
                )

        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List error: {str(e)}")


# ==================== Version History API ====================

from app.services.oss_version_service import oss_version_service


class VersionInfoResponse(BaseModel):
    version_id: str
    created_at: str
    size: int
    content_preview: str


class ListVersionsResponse(BaseModel):
    success: bool
    file_path: str
    versions: List[VersionInfoResponse]
    total: int
    limit: int
    offset: int


class ReadVersionResponse(BaseModel):
    success: bool
    version_id: str
    file_path: str
    content: str
    created_at: str
    size: int


class RollbackResponse(BaseModel):
    success: bool
    file_path: str
    rolled_to_version: str
    new_version_id: str
    message: str


@router.get("/oss/versions", response_model=ListVersionsResponse)
async def list_file_versions(
    file_path: str = Query(..., description="File path in OSS"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
):
    """
    List all versions for a specific file.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    # Security check
    if not file_path.startswith(f"markdown/{user_id}/"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        versions = oss_version_service.list_versions(user_id, file_path, limit, offset)

        version_responses = [
            VersionInfoResponse(
                version_id=v["version_id"],
                created_at=v["created_at"],
                size=v["size"],
                content_preview=v["content_preview"],
            )
            for v in versions
        ]

        return ListVersionsResponse(
            success=True,
            file_path=file_path,
            versions=version_responses,
            total=len(version_responses),
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list versions: {str(e)}"
        )


@router.get("/oss/versions/read", response_model=ReadVersionResponse)
async def read_file_version(
    file_path: str = Query(..., description="File path in OSS"),
    version_id: str = Query(..., description="Version ID"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Read content of a specific version.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    # Security check
    if not file_path.startswith(f"markdown/{user_id}/"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        success, content = oss_version_service.read_version(
            user_id, file_path, version_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return ReadVersionResponse(
            success=True,
            version_id=version_id,
            file_path=file_path,
            content=content,
            created_at="",
            size=len(content.encode("utf-8")),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read version: {str(e)}")


@router.post("/oss/versions/rollback", response_model=RollbackResponse)
async def rollback_to_version(
    request: dict, user_id: str = Depends(get_current_user_id)
):
    """
    Rollback to a specific version.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    file_path = request.get("file_path")
    version_id = request.get("version_id")

    if not file_path or not version_id:
        raise HTTPException(
            status_code=400, detail="file_path and version_id are required"
        )

    # Security check
    if not file_path.startswith(f"markdown/{user_id}/"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        success, new_version_id = oss_version_service.rollback_to_version(
            user_id, file_path, version_id
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to rollback")

        return RollbackResponse(
            success=True,
            file_path=file_path,
            rolled_to_version=version_id,
            new_version_id=new_version_id,
            message="Rollback successful",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback: {str(e)}")


@router.delete("/oss/versions/delete")
async def delete_file_version(
    file_path: str = Query(..., description="File path in OSS"),
    version_id: str = Query(..., description="Version ID"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a specific version.
    """
    if not oss_service.is_available():
        raise HTTPException(status_code=503, detail="OSS service is not configured")

    # Security check
    if not file_path.startswith(f"markdown/{user_id}/"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        success = oss_version_service.delete_version(user_id, file_path, version_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete version")

        return {"success": True, "message": "Version deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete version: {str(e)}"
        )
