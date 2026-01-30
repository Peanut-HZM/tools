"""
Markdown Config Service - Handles configuration persistence with user isolation
"""
import json
import logging
from pathlib import Path
from typing import Optional

from app.models.config_models import EditorConfig, get_default_config
from app.utils.path_utils import ensure_user_directory

logger = logging.getLogger(__name__)


class MarkdownConfigService:
    """Service for configuration management with user isolation"""
    
    def __init__(self, user_id: str, base_path: str = "./data/users"):
        """
        Initialize MarkdownConfigService with user-specific config path.
        
        Args:
            user_id: The user's ID for config isolation
            base_path: Base path for user data storage
        """
        self.user_id = user_id
        self.base_path = base_path
        
        # Ensure user directory exists
        user_root = ensure_user_directory(user_id, base_path)
        self.config_path = Path(user_root) / ".markdown-editor" / "config.json"
    
    def load_config(self) -> EditorConfig:
        """
        Load configuration from JSON file.
        Returns default config if file doesn't exist or is invalid.
        
        Returns:
            EditorConfig object
        """
        if not self.config_path.exists():
            return get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return EditorConfig(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file for user {self.user_id}: {e}")
            return get_default_config()
        except Exception as e:
            logger.error(f"Error loading config for user {self.user_id}: {e}")
            return get_default_config()
    
    def save_config(self, config: EditorConfig) -> bool:
        """
        Save configuration to JSON file.
        
        Args:
            config: EditorConfig object to save
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use by_alias=True to save with camelCase keys for frontend compatibility
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(by_alias=True), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config for user {self.user_id}: {e}")
            return False
    
    def get_default_config(self) -> EditorConfig:
        """Return default configuration"""
        return get_default_config()
    
    def serialize_config(self, config: EditorConfig) -> str:
        """
        Serialize configuration to JSON string.
        
        Args:
            config: EditorConfig object
            
        Returns:
            JSON string representation
        """
        return json.dumps(config.model_dump(by_alias=True), indent=2)
    
    def deserialize_config(self, json_str: str) -> Optional[EditorConfig]:
        """
        Deserialize configuration from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            EditorConfig object or None if invalid
        """
        try:
            data = json.loads(json_str)
            return EditorConfig(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error deserializing config: {e}")
            return None
