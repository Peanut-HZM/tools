"""LLMCategory 常量测试"""

from app.constants.llm_categories import LLMCategory


def test_category_values():
    """枚举值与数据库 String 列对齐"""
    assert LLMCategory.CHAT == "chat"
    assert LLMCategory.CODE == "code"
    assert LLMCategory.VOICE == "voice"
    assert LLMCategory.VISION == "vision"
    assert LLMCategory.MULTIMODAL == "multimodal"
    assert LLMCategory.EMBEDDING == "embedding"
    assert LLMCategory.IMAGE_POLISH == "image_polish"
    assert LLMCategory.IMAGE_GEN == "image_gen"


def test_category_all_contains_eight():
    """ALL 应包含全部 8 个值"""
    assert len(LLMCategory.ALL) == 8
    assert LLMCategory.CHAT in LLMCategory.ALL
    assert LLMCategory.IMAGE_GEN in LLMCategory.ALL


def test_text_categories_excludes_image_gen():
    """TEXT_CATEGORIES 不含 image_gen（走独立 factory）"""
    assert "image_gen" not in LLMCategory.TEXT_CATEGORIES
    assert "chat" in LLMCategory.TEXT_CATEGORIES
    assert "image_polish" in LLMCategory.TEXT_CATEGORIES