# Models package
from app.models.tool_models import (
    Tool,
    Category,
    ToolCreateRequest,
    CategoryCreateRequest,
    ToolsResponse,
    SearchResponse,
    CategoryResponse,
    ToolUpdateRequest,
    ToolsPaginatedResponse,
)

# Re-export from submodules
from app.models.auth_models import *
from app.models.file_models import *
from app.models.config_models import *
from app.models.search_models import *
# tool_models 的 SearchResponse 必须在 search_models 之后声明：
# 两者同名（工具搜索 tools/count vs 文件搜索 results/total），app.models 对外应导出工具版，
# 否则 /api/tools/search 会按文件搜索结构校验而 500
from app.models.tool_models import SearchResponse  # noqa: F811
from app.models.stats_models import *
from app.models.database_tool_models import *
from app.models.redis_tool_models import *
# Neo4j 图数据库工具模型：显式导入，避免 import * 带出 sqlalchemy 的 Column 等名字
from app.models.neo4j_models import (
    Neo4jConnection,
    Neo4jConnectionCreate,
    Neo4jConnectionUpdate,
    Neo4jConnectionResponse,
)  # noqa: F401
from app.models.oss_models import *
from app.models.ocr_models import *
from app.models.asr_models import *

# 产品经理 Agent 模型
from app.models.base import Base, get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.prd import PRDDocument
from app.models.competitor import CompetitorAnalysis
from app.models.llm_config import LLMConfig
# v1 起新增：供应商 / 模型拆分（详见 spec §16.3）
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.models.agent import Agent

# 应用级密钥（主密钥入库，根治多环境密钥不一致）
from app.models.app_secret import AppSecret  # noqa: F401

# CrossShare 跨设备共享模型
from app.models.cross_share import (
    Device,
    CrossMessage,
    CrossFile,
    CrossShareConfig,
)

# Contact Message 联系留言模型
from app.models.contact_message import (
    ContactMessage,
    MessageStatus,
    ContactMessageCreate,
    ContactMessageUpdate,
    ContactMessageResponse,
    ContactMessageListResponse,
)

# Password Audit Log 密码审计日志模型
from app.models.password_log_models import PasswordAuditLog

# K8s 控制台工具模型
from app.models.k8s_tool_models import *

# LLM 用户配额 + 调用流水模型
from app.models.llm_quota_models import LLMUserQuota, LLMUsageLog  # noqa: F401

# Harness Phase 1 ORM 模型
# 注：ORM Tool 以别名 HarnessTool 导出，避免覆盖上方 Pydantic Tool
from app.models.harness_models import (
    Tool as HarnessTool,
    ToolBinding,
    SessionCheckpoint,
    AgentMemory,
    Trace,
    TraceStep,
    Branch,  # Phase 3-Plan-1D 新增
)  # noqa: F401

# Harness Phase 2 Memory Long-term
from app.models.agent_memory import AgentMemoryLongTerm  # noqa: F401

# Harness Phase 3 Plan-1A: MCP Server 配置
from app.models.mcp_server import McpServer  # noqa: F401
