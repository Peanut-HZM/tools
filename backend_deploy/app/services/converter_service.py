import os
import shutil
import logging
from typing import Optional
from pathlib import Path
from fastapi import UploadFile
from markitdown import MarkItDown
import uuid
import io
from app.services.oss_service import oss_service

logger = logging.getLogger(__name__)

class ConverterService:
    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.md = MarkItDown()

    async def convert_file(self, file: UploadFile, user_id: str = "anonymous") -> str:
        """
        Convert uploaded file to markdown using MarkItDown.
        Also upload both input and output to OSS.
        """
        temp_file_path = self.temp_dir / file.filename
        try:
            # 1. Save uploaded file to temp directory
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Reset file pointer for OSS upload
            file.file.seek(0)
            file.file.seek(0, 2)
            input_size = file.file.tell()
            file.file.seek(0)
            
            # 2. Upload Input File to OSS
            # Determine extension
            ext = os.path.splitext(file.filename)[1]
            input_obj_name = f"users/{user_id}/converter/input/{uuid.uuid4()}{ext}"
            
            oss_service.upload_file(
                object_name=input_obj_name,
                data=file.file,
                size=input_size,
                content_type=file.content_type or "application/octet-stream",
                uploaded_by=user_id
            )
            
            # 3. Convert file
            result = self.md.convert(str(temp_file_path))
            
            markdown_content = ""
            if result and result.text_content:
                markdown_content = result.text_content
                
            # 4. Upload Output Markdown to OSS
            if markdown_content:
                output_obj_name = f"users/{user_id}/converter/output/{uuid.uuid4()}.md"
                md_bytes = markdown_content.encode('utf-8')
                
                oss_service.upload_file(
                    object_name=output_obj_name,
                    data=io.BytesIO(md_bytes),
                    size=len(md_bytes),
                    content_type="text/markdown",
                    uploaded_by=user_id
                )
            
            return markdown_content
            
        except Exception as e:
            logger.error(f"Error converting file {file.filename}: {str(e)}")
            raise Exception(f"Failed to convert file: {str(e)}")
        finally:
            # Clean up temp file
            if temp_file_path.exists():
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file_path}: {str(e)}")
