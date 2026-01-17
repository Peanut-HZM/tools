"""
Property-based tests for ConfigService

**Feature: markdown-editor, Property 5: Configuration Serialization Round-Trip**
**Validates: Requirements 7.5, 10.1, 10.2, 10.3**
"""
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings

from app.models.config_models import EditorConfig
from app.services.config_service import ConfigService


# Strategy for valid theme values
theme_strategy = st.sampled_from(["light", "dark"])

# Strategy for valid font sizes
font_size_strategy = st.integers(min_value=8, max_value=32)

# Strategy for valid auto-save intervals
auto_save_strategy = st.integers(min_value=5, max_value=300)

# Strategy for valid tab sizes
tab_size_strategy = st.integers(min_value=1, max_value=8)

# Strategy for preview themes
preview_theme_strategy = st.sampled_from(["github", "gitlab", "default", "dark"])


# Strategy for generating valid EditorConfig objects
@st.composite
def editor_config_strategy(draw):
    """Generate valid EditorConfig objects"""
    return EditorConfig(
        theme=draw(theme_strategy),
        font_size=draw(font_size_strategy),
        auto_save_interval=draw(auto_save_strategy),
        preview_theme=draw(preview_theme_strategy),
        show_line_numbers=draw(st.booleans()),
        tab_size=draw(tab_size_strategy),
        use_spaces=draw(st.booleans()),
        word_wrap=draw(st.booleans()),
        show_minimap=draw(st.booleans())
    )


@given(config=editor_config_strategy())
@settings(max_examples=100)
def test_config_serialization_round_trip(config: EditorConfig):
    """
    **Feature: markdown-editor, Property 5: Configuration Serialization Round-Trip**
    
    For any valid EditorConfig object, serializing to JSON and parsing back
    SHALL produce an EditorConfig object equivalent to the original.
    
    **Validates: Requirements 7.5, 10.1, 10.2, 10.3**
    """
    with tempfile.TemporaryDirectory() as root:
        config_path = Path(root) / "config.json"
        service = ConfigService(str(config_path))
        
        # Serialize (save)
        json_str = service.serialize_config(config)
        
        # Deserialize (parse)
        restored = service.deserialize_config(json_str)
        
        assert restored is not None, "Deserialization returned None"
        
        # Verify all fields match
        assert restored.theme == config.theme
        assert restored.font_size == config.font_size
        assert restored.auto_save_interval == config.auto_save_interval
        assert restored.preview_theme == config.preview_theme
        assert restored.show_line_numbers == config.show_line_numbers
        assert restored.tab_size == config.tab_size
        assert restored.use_spaces == config.use_spaces
        assert restored.word_wrap == config.word_wrap
        assert restored.show_minimap == config.show_minimap


@given(config=editor_config_strategy())
@settings(max_examples=100)
def test_config_file_round_trip(config: EditorConfig):
    """
    **Feature: markdown-editor, Property 5: Configuration Serialization Round-Trip**
    
    For any valid EditorConfig object, saving to file and loading back
    SHALL produce an EditorConfig object equivalent to the original.
    
    **Validates: Requirements 7.5, 10.1, 10.2, 10.3**
    """
    with tempfile.TemporaryDirectory() as root:
        config_path = Path(root) / "config.json"
        service = ConfigService(str(config_path))
        
        # Save to file
        success = service.save_config(config)
        assert success, "Failed to save config"
        
        # Load from file
        restored = service.load_config()
        
        # Verify all fields match
        assert restored.theme == config.theme
        assert restored.font_size == config.font_size
        assert restored.auto_save_interval == config.auto_save_interval
        assert restored.preview_theme == config.preview_theme
        assert restored.show_line_numbers == config.show_line_numbers
        assert restored.tab_size == config.tab_size
        assert restored.use_spaces == config.use_spaces
        assert restored.word_wrap == config.word_wrap
        assert restored.show_minimap == config.show_minimap


@given(invalid_json=st.text(
    alphabet=st.characters(
        whitelist_categories=(),
        whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]|;:,.<>?'
    ),
    min_size=1,
    max_size=50
).filter(lambda x: '{' not in x))
@settings(max_examples=50)
def test_invalid_json_returns_default(invalid_json: str):
    """
    Test that invalid JSON returns default configuration.
    
    **Validates: Requirements 10.4**
    """
    with tempfile.TemporaryDirectory() as root:
        config_path = Path(root) / "config.json"
        
        # Write invalid JSON
        config_path.write_text(invalid_json)
        
        service = ConfigService(str(config_path))
        config = service.load_config()
        
        # Should return default config
        default = service.get_default_config()
        assert config.theme == default.theme
        assert config.font_size == default.font_size


def test_missing_file_returns_default():
    """
    Test that missing config file returns default configuration.
    """
    with tempfile.TemporaryDirectory() as root:
        config_path = Path(root) / "nonexistent.json"
        service = ConfigService(str(config_path))
        
        config = service.load_config()
        default = service.get_default_config()
        
        assert config.theme == default.theme
        assert config.font_size == default.font_size
