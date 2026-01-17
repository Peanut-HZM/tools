"""
Config API Router - Handles configuration operations
"""
import os
from fastapi import APIRouter, HTTPException

from app.models.config_models import EditorConfig
from app.services.config_service import ConfigService

router = APIRouter(prefix="/api/config", tags=["config"])

# Get config path from environment or use default
ROOT_PATH = os.environ.get("MARKDOWN_EDITOR_ROOT", os.getcwd())
CONFIG_PATH = os.path.join(ROOT_PATH, ".markdown-editor", "config.json")


def get_config_service() -> ConfigService:
    """Get ConfigService instance"""
    return ConfigService(CONFIG_PATH)


@router.get("", response_model=EditorConfig)
async def get_config():
    """
    Get current configuration.
    Returns default configuration if no config file exists.
    """
    try:
        service = get_config_service()
        return service.load_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading config: {str(e)}")


@router.post("", response_model=EditorConfig)
async def save_config(config: EditorConfig):
    """
    Save configuration.
    """
    try:
        service = get_config_service()
        success = service.save_config(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving config: {str(e)}")
