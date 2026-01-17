"""
Config Service - Handles configuration persistence
"""
import json
import logging
from pathlib import Path
from typing import Optional

from app.models.config_models import EditorConfig, get_default_config

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for configuration management"""
    
    def __init__(self, config_path: str):
        """
        Initialize ConfigService with config file path.
        
        Args:
            config_path: Path to the configuration JSON file
        """
        self.config_path = Path(config_path)
    
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
            logger.error(f"Invalid JSON in config file: {e}")
            return get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
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
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
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
        return json.dumps(config.model_dump(), indent=2)
    
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
