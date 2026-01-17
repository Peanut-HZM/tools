"""
Pydantic models for configuration
"""
from pydantic import BaseModel, Field
from typing import Literal


class EditorConfig(BaseModel):
    """Editor configuration settings"""
    theme: Literal["light", "dark"] = "light"
    font_size: int = Field(default=14, ge=8, le=32)
    auto_save_interval: int = Field(default=30, ge=5, le=300)  # seconds
    preview_theme: str = "github"
    show_line_numbers: bool = True
    tab_size: int = Field(default=2, ge=1, le=8)
    use_spaces: bool = True
    word_wrap: bool = True
    show_minimap: bool = False
    
    class Config:
        """Pydantic config"""
        extra = "ignore"  # Ignore extra fields when parsing


def get_default_config() -> EditorConfig:
    """Return default configuration"""
    return EditorConfig()
