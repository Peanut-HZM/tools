"""
Pydantic models for configuration - Markdown Editor
"""
from pydantic import BaseModel, Field
from typing import Literal


class EditorConfig(BaseModel):
    """Editor configuration settings"""
    theme: Literal["light", "dark"] = "dark"
    font_size: int = Field(default=14, ge=8, le=32, alias="fontSize")
    auto_save_interval: int = Field(default=30, ge=5, le=300, alias="autoSaveInterval")  # seconds
    preview_theme: str = Field(default="github", alias="previewTheme")
    show_line_numbers: bool = Field(default=True, alias="showLineNumbers")
    tab_size: int = Field(default=2, ge=1, le=8, alias="tabSize")
    use_spaces: bool = Field(default=True, alias="useSpaces")
    word_wrap: bool = Field(default=True, alias="wordWrap")
    show_minimap: bool = Field(default=False, alias="showMinimap")
    language: Literal["zh-CN", "en-US"] = "zh-CN"
    root_path: str = Field(default="", alias="rootPath")
    
    class Config:
        """Pydantic config"""
        extra = "ignore"  # Ignore extra fields when parsing
        populate_by_name = True  # Allow both snake_case and camelCase


def get_default_config() -> EditorConfig:
    """Return default configuration"""
    return EditorConfig()
