import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import time
import uuid

from app.models.history_models import HistoryItem

logger = logging.getLogger(__name__)

HISTORY_DATA_PATH = os.environ.get("HISTORY_DATA_PATH", "./data/history")

class HistoryService:
    def __init__(self):
        self.history_file = Path(HISTORY_DATA_PATH) / "history.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history({})

    def _load_history(self) -> Dict[str, List[dict]]:
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
        return {}

    def _save_history(self, history: Dict[str, List[dict]]) -> bool:
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            return False

    def add_history(self, user_id: str, file_name: str, file_size: int, content: str) -> HistoryItem:
        history_data = self._load_history()
        
        if user_id not in history_data:
            history_data[user_id] = []
            
        new_item = HistoryItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            file_name=file_name,
            file_size=file_size,
            content=content,
            created_at=int(time.time() * 1000)
        )
        
        # Add to beginning of list
        history_data[user_id].insert(0, new_item.model_dump())
        
        # Limit to last 50 items per user to prevent huge files
        if len(history_data[user_id]) > 50:
            history_data[user_id] = history_data[user_id][:50]
            
        self._save_history(history_data)
        return new_item

    def get_user_history(self, user_id: str) -> List[HistoryItem]:
        history_data = self._load_history()
        user_history = history_data.get(user_id, [])
        return [HistoryItem(**item) for item in user_history]

    def delete_history(self, user_id: str, history_id: str) -> bool:
        history_data = self._load_history()
        if user_id in history_data:
            original_len = len(history_data[user_id])
            history_data[user_id] = [item for item in history_data[user_id] if item['id'] != history_id]
            if len(history_data[user_id]) < original_len:
                self._save_history(history_data)
                return True
        return False
