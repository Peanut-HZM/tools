"""LLM 模型分类枚举

数据库 LLMModel.category 为 String 列，本常量类统一字符串字面量。
新增分类时同步更新 ALL / TEXT_CATEGORIES。

分类说明：
  - text: 文本生成（对话、代码、问答、提示词润色等纯文本 LLM）
  - vision: 视觉理解（图片理解、图文混合输入）
  - image_gen: 图像生成（由 harness ImageGenTool 处理，非文本类）
  - voice: 语音合成 / 识别
  - embedding: 向量嵌入
  - ocr: OCR 文档 / 图片文字识别
"""


class LLMCategory:
    """LLM 模型分类（对应 LLMModel.category）"""

    TEXT = "text"
    """文本生成（对话 / 代码 / 问答 / 润色等）"""

    VISION = "vision"
    """视觉理解（图片理解、图文混合输入）"""

    IMAGE_GEN = "image_gen"
    """图像生成（由 harness ImageGenTool 处理，非文本类）"""

    VOICE = "voice"
    """语音合成 / 识别"""

    EMBEDDING = "embedding"
    """向量嵌入"""

    OCR = "ocr"
    """OCR 文档 / 图片文字识别"""

    ALL = (
        TEXT,
        VISION,
        IMAGE_GEN,
        VOICE,
        EMBEDDING,
        OCR,
    )
    """全部有效分类"""

LLMCategory.TEXT_CATEGORIES = tuple(
    c for c in LLMCategory.ALL if c != LLMCategory.IMAGE_GEN
)
"""走 LLMFactory 的文本类分类（除 image_gen 外）"""


# ------------------------------------------------------------------
# 向后兼容别名（旧代码 / 旧数据库记录仍可引用）
# ------------------------------------------------------------------

LLMCategory.CHAT = "chat"
LLMCategory.CODE = "code"
LLMCategory.MULTIMODAL = "multimodal"
LLMCategory.IMAGE_POLISH = "image_polish"

LEGACY_TO_NEW_CATEGORY = {
    "chat": "text",
    "code": "text",
    "image_polish": "text",
    "multimodal": "vision",
}
"""旧分类 → 新分类映射，用于数据迁移"""
