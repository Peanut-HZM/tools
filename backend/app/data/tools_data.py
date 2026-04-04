from app.models import Tool

# 只保留已实现的工具：图片下载、视频下载、JSON 格式化、万年历、AI 助手
TOOLS_DATA = [
    Tool(
        id="image-downloader",
        icon="fa-download",
        iconColor="bg-cyan-500",
        title="网页图片下载",
        description="粘贴网页 URL，自动下载该网页的所有图片，支持所有格式",
        rating=4.9,
        usageCount="1.6K",
        category="实用工具",
    ),
    Tool(
        id="video-downloader",
        icon="fa-video",
        iconColor="bg-purple-600",
        title="网页视频下载",
        description="粘贴网页 URL，自动提取并下载视频资源，支持 MP4、WebM、HLS 等格式",
        rating=4.8,
        usageCount="2.1K",
        category="实用工具",
    ),
    Tool(
        id="json-formatter",
        icon="fa-code",
        iconColor="bg-green-500",
        title="JSON 格式化",
        description="粘贴 JSON 字符串，自动格式化并美化显示，支持语法检查和错误提示",
        rating=4.9,
        usageCount="3.2K",
        category="开发工具",
    ),
    Tool(
        id="calendar",
        icon="fa-calendar-alt",
        iconColor="bg-red-500",
        title="万年历",
        description="查看日历，显示法定节假日和调休安排，支持年份切换",
        rating=4.7,
        usageCount="1.8K",
        category="实用工具",
    ),
    Tool(
        id="ai-assistant",
        icon="fa-robot",
        iconColor="bg-gradient-to-r from-purple-500 to-pink-500",
        title="AI 助手",
        description="智能 AI 对话助手，支持多种场景的智能问答和内容生成",
        rating=4.9,
        usageCount="5.2K",
        category="AI 工具",
    ),
    Tool(
        id="key-generator",
        icon="fa-key",
        iconColor="bg-yellow-500",
        title="密钥生成器",
        description="生成各种加密算法的密钥，支持 RSA、ECDSA、AES、HMAC 等常用算法",
        rating=4.8,
        usageCount="2.5K",
        category="开发工具",
    ),
    Tool(
        id="markdown-editor",
        icon="fa-pen-to-square",
        iconColor="bg-blue-600",
        title="Markdown 编辑器",
        description="功能强大的 Markdown 编辑器，支持实时预览、语法高亮、文件管理等功能",
        rating=4.9,
        usageCount="3.8K",
        category="开发工具",
    ),
    Tool(
        id="markitdown-converter",
        icon="fa-file-export",
        iconColor="bg-orange-500",
        title="文档转 Markdown",
        description="支持将 Word, Excel, PDF 等文档一键转换为 Markdown，并支持在线预览和编辑",
        rating=4.9,
        usageCount="New",
        category="开发工具",
    ),
    Tool(
        id="ocr-tool",
        icon="fa-file-image",
        iconColor="bg-indigo-500",
        title="OCR 文字识别",
        description="基于 Umi-OCR 的离线文字识别，支持截图、批量图片识别和排版解析",
        rating=4.9,
        usageCount="New",
        category="AI 工具",
    ),
    Tool(
        id="asr-tool",
        icon="fa-microphone",
        iconColor="bg-emerald-500",
        title="语音识别",
        description="基于 FunASR 的高精度语音识别，支持多种音频格式转文字",
        rating=4.8,
        usageCount="New",
        category="AI 工具",
    ),
    Tool(
        id="database-tool",
        icon="fa-database",
        iconColor="bg-blue-500",
        title="数据库管理工具",
        description="统一管理多个数据库连接，执行 SQL 脚本，浏览数据库结构",
        rating=5.0,
        usageCount="New",
        category="开发工具",
    ),
    Tool(
        id="redis-tool",
        icon="fa-server",
        iconColor="bg-red-600",
        title="Redis 管理",
        description="Redis 多连接管理，支持 Key 的增删查改",
        rating=4.9,
        usageCount="New",
        category="开发工具",
    ),
    Tool(
        id="ssh-tool",
        icon="fa-terminal",
        iconColor="bg-slate-600",
        title="SSH 管理",
        description="集中管理 SSH 连接配置，提供在线终端操作",
        rating=4.9,
        usageCount="New",
        category="开发工具",
    ),
    Tool(
        id="product-manager",
        icon="fa-user-tie",
        iconColor="bg-gradient-to-r from-blue-500 to-indigo-500",
        title="产品经理 Agent",
        description="智能产品经理助手，支持竞品分析、PRD 生成、需求梳理等功能",
        rating=4.9,
        usageCount="New",
        category="AI 工具",
    ),
    Tool(
        id="cross-share",
        icon="fa-share-alt",
        iconColor="bg-indigo-500",
        title="CrossShare 设备传传",
        description="跨设备消息和文件共享工具，登录即用，全平台同步",
        rating=4.9,
        usageCount="New",
        category="实用工具",
    ),
    Tool(
        id="course-platform",
        icon="fa-graduation-cap",
        iconColor="bg-cyan-500",
        title="技术分享",
        description="技术课程学习平台，提供高质量的技術课程和实战练习",
        rating=5.0,
        usageCount="New",
        category="学习工具",
    ),
    Tool(
        id="cursor-history",
        icon="fa-clock-rotate-left",
        iconColor="bg-violet-500",
        title="Cursor 对话历史",
        description="浏览和搜索本地 Cursor AI 的历史对话记录，支持按项目和会话分组查看",
        rating=4.9,
        usageCount="New",
        category="开发工具",
    ),
    Tool(
        id="http-api-client",
        icon="fa-plug",
        iconColor="bg-purple-600",
        title="HTTP API 客户端",
        description="功能强大的 HTTP API 调试工具，支持请求管理、环境变量、认证配置等功能",
        rating=5.0,
        usageCount="New",
        category="开发工具",
    ),
]


def get_all_tools():
    return TOOLS_DATA


def search_tools(query: str):
    query_lower = query.lower()
    return [
        tool
        for tool in TOOLS_DATA
        if query_lower in tool.title.lower() or query_lower in tool.description.lower()
    ]


def get_tools_by_category(category: str):
    if category == "全部工具":
        return TOOLS_DATA
    return [tool for tool in TOOLS_DATA if tool.category == category]
