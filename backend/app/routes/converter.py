from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from app.services.converter_service import ConverterService
from app.services.history_service import HistoryService
from app.middleware.auth_middleware import get_current_user_id
from app.models.history_models import HistoryResponse

router = APIRouter(prefix="/api/converter", tags=["converter"])

@router.post("/convert")
async def convert_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Convert document (PDF, Word, Excel, etc.) to Markdown.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    try:
        service = ConverterService()
        markdown_content = await service.convert_file(file)
        
        # Save to history
        history_service = HistoryService()
        # Reset file position to get size if needed, but file is already read.
        # We can use file.size if available, or just pass 0 if unknown (or estimate from content length?)
        # UploadFile.size might not be available depending on spooling.
        # Let's try to get size from headers or just use 0.
        file_size = 0
        if file.size:
            file_size = file.size
            
        new_item = history_service.add_history(
            user_id=user_id,
            file_name=file.filename or "unknown",
            file_size=file_size,
            content=markdown_content
        )
        
        return {
            "content": markdown_content,
            "history_item": new_item
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[HistoryResponse])
async def get_history(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get conversion history for the current user.
    """
    try:
        service = HistoryService()
        return service.get_user_history(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{history_id}")
async def delete_history(
    history_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete a specific history item.
    """
    try:
        service = HistoryService()
        success = service.delete_history(user_id, history_id)
        if not success:
            raise HTTPException(status_code=404, detail="History item not found")
        return {"message": "History item deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
