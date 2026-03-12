from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HistoryItem(BaseModel):
    id: str
    user_id: str
    file_name: str
    file_size: int
    content: str
    created_at: int  # Timestamp

class HistoryItemCreate(BaseModel):
    file_name: str
    file_size: int
    content: str

class HistoryResponse(BaseModel):
    id: str
    file_name: str
    file_size: int
    content: str
    created_at: int
