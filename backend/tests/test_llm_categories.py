"""LLMCategory 常量测试"""

from app.constants.llm_categories import LLMCategory


def test_category_values():
    """枚举值与数据库 String 列对齐"""
    assert LLMCategory.TEXT == "text"
    assert LLMCategory.VOICE == "voice"
    assert LLMCategory.VISION == "vision"
    assert LLMCategory.EMBEDDING == "embedding"
    assert LLMCategory.IMAGE_GEN == "image_gen"
    assert LLMCategory.OCR == "ocr"


def test_legacy_aliases():
    """旧分类别名仍可引用（向后兼容）"""
    assert LLMCategory.CHAT == "chat"
    assert LLMCategory.CODE == "code"
    assert LLMCategory.MULTIMODAL == "multimodal"
    assert LLMCategory.IMAGE_POLISH == "image_polish"


def test_category_all_contains_six():
    """ALL 应包含全部 6 个新分类"""
    assert len(LLMCategory.ALL) == 6
    assert LLMCategory.TEXT in LLMCategory.ALL
    assert LLMCategory.IMAGE_GEN in LLMCategory.ALL


def test_text_categories_excludes_image_gen():
    """TEXT_CATEGORIES 不含 image_gen（走独立 factory）"""
    assert "image_gen" not in LLMCategory.TEXT_CATEGORIES
    assert "text" in LLMCategory.TEXT_CATEGORIES
    assert "ocr" in LLMCategory.TEXT_CATEGORIES
