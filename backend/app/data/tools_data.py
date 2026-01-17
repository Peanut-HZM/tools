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
        icon="fa-file-alt",
        iconColor="bg-indigo-500",
        title="Markdown编辑器",
        description="功能强大的Markdown编辑器，支持实时预览、语法高亮、文件管理等功能",
        rating=4.9,
        usageCount="3.8K",
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
