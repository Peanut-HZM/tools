import os
import shutil
import logging
from typing import Optional
from pathlib import Path
from fastapi import UploadFile
from markitdown import MarkItDown

logger = logging.getLogger(__name__)

class ConverterService:
    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.md = MarkItDown()

    async def convert_file(self, file: UploadFile) -> str:
        """
        Convert uploaded file to markdown using MarkItDown.
        """
        temp_file_path = self.temp_dir / file.filename
        try:
            # Save uploaded file to temp directory
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Convert file
            result = self.md.convert(str(temp_file_path))
            
            # Return text content
            if result and result.text_content:
                return result.text_content
            return ""
            
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
