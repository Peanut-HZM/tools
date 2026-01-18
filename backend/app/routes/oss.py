from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.oss_service import oss_service
from app.models.oss_models import OssUploadResponse, OssDeleteResponse
from app.middleware.auth_middleware import get_current_user_id
import uuid
import os

router = APIRouter(prefix="/api/oss", tags=["oss"])

@router.post("/upload", response_model=OssUploadResponse)
async def upload_file(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)):
    """
    Upload a file to OSS
    Returns the public URL and the generated filename
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Generate a unique filename to avoid collisions
    # Use the original extension if present
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Organize files by user_id
    object_name = f"uploads/{user_id}/{unique_filename}"
    
    # Get file size (seek to end, tell, seek back)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    url = oss_service.upload_file(
        object_name=object_name, 
        data=file.file,
        size=size,
        content_type=file.content_type,
        uploaded_by=user_id
    )
    
    if not url:
        raise HTTPException(status_code=500, detail="Failed to upload file to OSS")
        
    return OssUploadResponse(url=url, filename=unique_filename)

@router.delete("/files/{filename}", response_model=OssDeleteResponse)
async def delete_file(filename: str, user_id: str = Depends(get_current_user_id)):
    """
    Delete a file from OSS
    Only allows deleting files belonging to the current user
    """
    # Security check: Ensure user can only delete their own files
    # The object name structure is uploads/{user_id}/{filename}
    object_name = f"uploads/{user_id}/{filename}"
    
    success = oss_service.delete_file(object_name)
    
    if not success:
        # Note: OSS delete is idempotent, so if the file doesn't exist it returns success usually.
        # If it returns False, it means something went wrong with the request.
        raise HTTPException(status_code=500, detail="Failed to delete file from OSS")
        
    return OssDeleteResponse(success=True, message="File deleted successfully")
