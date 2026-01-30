"""
Pydantic models for OSS operations
"""
from pydantic import BaseModel
from typing import Optional

class OssUploadResponse(BaseModel):
    url: str
    filename: str

class OssDeleteResponse(BaseModel):
    success: bool
    message: str
