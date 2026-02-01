from app.models import Tool

# 只保留已实现的工具：图片下载、视频下载、JSON格式化、万年历、AI助手
TOOLS_DATA = [
    Tool(
        id="image-downloader",
        icon="fa-download",
        iconColor="bg-cyan-500",
        title="网页图片下载",
        description="粘贴网页URL，自动下载该网页的所有图片，支持所有格式",
        rating=4.9,
        usageCount="1.6K",
        category="实用工具"
    ),
    Tool(
        id="video-downloader",
        icon="fa-video",
        iconColor="bg-purple-600",
        title="网页视频下载",
        description="粘贴网页URL，自动提取并下载视频资源，支持MP4、WebM、HLS等格式",
        rating=4.8,
        usageCount="2.1K",
        category="实用工具"
    ),
    Tool(
        id="json-formatter",
        icon="fa-code",
        iconColor="bg-green-500",
        title="JSON格式化",
        description="粘贴JSON字符串，自动格式化并美化显示，支持语法检查和错误提示",
        rating=4.9,
        usageCount="3.2K",
        category="开发工具"
    ),
    Tool(
        id="calendar",
        icon="fa-calendar-alt",
        iconColor="bg-red-500",
        title="万年历",
        description="查看日历，显示法定节假日和调休安排，支持年份切换",
        rating=4.7,
        usageCount="1.8K",
        category="实用工具"
    ),
    Tool(
        id="ai-assistant",
        icon="fa-robot",
        iconColor="bg-gradient-to-r from-purple-500 to-pink-500",
        title="AI助手",
        description="智能AI对话助手，支持多种场景的智能问答和内容生成",
        rating=4.9,
        usageCount="5.2K",
        category="AI工具"
    ),
    Tool(
        id="key-generator",
        icon="fa-key",
        iconColor="bg-yellow-500",
        title="密钥生成器",
        description="生成各种加密算法的密钥，支持RSA、ECDSA、AES、HMAC等常用算法",
        rating=4.8,
        usageCount="2.5K",
        category="开发工具"
    ),
    Tool(
        id="markdown-editor",
        icon="fa-pen-to-square",
        iconColor="bg-blue-600",
        title="Markdown编辑器",
        description="功能强大的Markdown编辑器，支持实时预览、语法高亮、文件管理等功能",
        rating=4.9,
        usageCount="3.8K",
        category="开发工具"
    ),
    Tool(
        id="markitdown-converter",
        icon="fa-file-export",
        iconColor="bg-orange-500",
        title="文档转 Markdown",
        description="支持将 Word, Excel, PDF 等文档一键转换为 Markdown，并支持在线预览和编辑",
        rating=4.9,
        usageCount="New",
        category="开发工具"
    ),
    Tool(
        id="ocr-tool",
        icon="fa-file-image",
        iconColor="bg-indigo-500",
        title="OCR 文字识别",
        description="基于 Umi-OCR 的离线文字识别，支持截图、批量图片识别和排版解析",
        rating=4.9,
        usageCount="New",
        category="AI工具"
    ),
    Tool(
        id="asr-tool",
        icon="fa-microphone",
        iconColor="bg-emerald-500",
        title="语音识别",
        description="基于 FunASR 的高精度语音识别，支持多种音频格式转文字",
        rating=4.8,
        usageCount="New",
        category="AI工具"
    ),
    Tool(
        id="database-tool",
        icon="fa-database",
        iconColor="bg-blue-500",
        title="数据库管理工具",
        description="统一管理多个数据库连接，执行SQL脚本，浏览数据库结构",
        rating=5.0,
        usageCount="New",
        category="开发工具"
    ),
    Tool(
        id="redis-tool",
        icon="fa-server",
        iconColor="bg-red-600",
        title="Redis 管理",
        description="Redis 多连接管理，支持 Key 的增删查改",
        rating=4.9,
        usageCount="New",
        category="开发工具"
    )
]

def get_all_tools():
    return TOOLS_DATA

def search_tools(query: str):
    query_lower = query.lower()
    return [
        tool for tool in TOOLS_DATA
        if query_lower in tool.title.lower() or query_lower in tool.description.lower()
    ]

def get_tools_by_category(category: str):
    if category == "全部工具":
        return TOOLS_DATA
    return [tool for tool in TOOLS_DATA if tool.category == category]
