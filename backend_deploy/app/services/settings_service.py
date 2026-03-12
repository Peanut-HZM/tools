"""
System Settings Service - Handles global system configuration
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any
from app.config.config import settings

logger = logging.getLogger(__name__)

SETTINGS_DATA_PATH = settings.USERS_DATA_PATH

class SettingsService:
    """Service for managing system settings"""
    
    def __init__(self):
        """Initialize SettingsService"""
        self.settings_file = Path(SETTINGS_DATA_PATH) / "system_settings.json"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists"""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.settings_file.exists():
            # Default settings
            self._save_settings({
                "allow_registration": True,
                "enable_email_verify": False,
                "enable_phone_verify": False
            })
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Ensure new fields exist
                    if "enable_email_verify" not in settings:
                        settings["enable_email_verify"] = False
                    if "enable_phone_verify" not in settings:
                        settings["enable_phone_verify"] = False
                    return settings
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        return {
            "allow_registration": True,
            "enable_email_verify": False,
            "enable_phone_verify": False
        }
    
    def _save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to JSON file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
            
    def get_settings(self) -> Dict[str, Any]:
        """Get all system settings"""
        return self._load_settings()
        
    def update_setting(self, key: str, value: Any) -> bool:
        """Update a specific setting"""
        settings = self._load_settings()
        settings[key] = value
        return self._save_settings(settings)
        
    def is_registration_allowed(self) -> bool:
        """Check if user registration is allowed"""
        settings = self._load_settings()
        return settings.get("allow_registration", True)

    def is_email_verify_enabled(self) -> bool:
        """Check if email verification is enabled"""
        settings = self._load_settings()
        return settings.get("enable_email_verify", False)
        
    def is_phone_verify_enabled(self) -> bool:
        """Check if phone verification is enabled"""
        settings = self._load_settings()
        return settings.get("enable_phone_verify", False)

# Singleton instance
settings_service = SettingsService()
