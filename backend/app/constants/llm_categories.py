"""LLM 模型分类枚举

数据库 LLMModel.category 为 String 列，本常量类统一字符串字面量。
新增分类时同步更新 ALL / TEXT_CATEGORIES。
"""


class LLMCategory:
    """LLM 模型分类（对应 LLMModel.category）"""

    CHAT = "chat"
    """对话 / 文本生成"""

    CODE = "code"
    """代码生成"""

    VOICE = "voice"
    """语音合成 / 识别"""

    VISION = "vision"
    """图像理解"""

    MULTIMODAL = "multimodal"
    """图文混合输入/输出"""

    EMBEDDING = "embedding"
    """向量嵌入"""

    IMAGE_POLISH = "image_polish"
    """图像提示词润色"""

    IMAGE_GEN = "image_gen"
    """图像生成（走 ImageGenFactory，非文本类）"""

    ALL = (
        CHAT,
        CODE,
        VOICE,
        VISION,
        MULTIMODAL,
        EMBEDDING,
        IMAGE_POLISH,
        IMAGE_GEN,
    )
    """全部有效分类"""

    # 在类体外定义，避免生成器表达式闭包内无法解析类体名称的问题
LLMCategory.TEXT_CATEGORIES = tuple(
    c for c in LLMCategory.ALL if c != LLMCategory.IMAGE_GEN
)
"""走 LLMFactory 的文本类分类"""