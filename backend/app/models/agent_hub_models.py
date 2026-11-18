"""Agent Hub ORM 模型 — Agent 订阅与供应商中心

设计文档: docs/plans/2026-11-18-agent-hub-design.md
整合 cc-switch（供应商管理/一键切换/订阅用量）与 magpie（多 agent 配置改写/额度聚合）的核心能力。

3 张新表（前缀 agent_hub_，不动既有表）：
- agent_hub_providers      供应商/订阅源（apikey 即加）
- agent_hub_subscriptions  订阅套餐（用量显示主体；manual 模式额度手动维护）
- agent_hub_switches       每个 agent 的当前激活指针
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Index
from app.models.base import Base  # 与既有 ORM 同一 Base（复用 create_all / engine）


def _uuid() -> str:
    return str(uuid.uuid4())


class AgentHubProvider(Base):
    """供应商/订阅源。多数预设只需粘贴一个 api_key 即可创建。"""
    __tablename__ = "agent_hub_providers"

    id = Column(String(64), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    # 查询器/写入器分派键: claude_official/codex_official/opendesign/kimi/zhipu/minimax/
    # zenmux/opencode_go/deepseek/openrouter/siliconflow/newapi/sub2api/generic_balance/manual
    kind = Column(String(50), nullable=False, index=True)
    # 作用对象 agent: claude/codex/gemini/kimi/opencode/zcode/minimax
    app = Column(String(50), nullable=False, index=True)
    base_url = Column(String(500), default="")
    api_key = Column(String(500), default="")            # 推理/连接 key
    usage_api_key = Column(String(500), default="")      # 用量查询专用凭据（如 OpenDesign controlKey）
    usage_base_url = Column(String(500), default="")     # 用量查询专用地址（控制面）
    extra_json = Column(Text, default="{}")              # 预设注入的附加配置（模型映射等）
    category = Column(String(30), default="third_party")  # official/aggregator/third_party/manual
    website_url = Column(String(500), default="")
    notes = Column(Text, default="")
    enabled = Column(Integer, default=1)                  # 0=不显示（「只显示已配置且可显示」开关）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentHubSubscription(Base):
    """订阅套餐 — 用量显示主体。manual 模式额度由用户手动维护（支持手动增加）。"""
    __tablename__ = "agent_hub_subscriptions"

    id = Column(String(64), primary_key=True, default=_uuid)
    provider_id = Column(String(64), default="")          # 可空：独立订阅
    name = Column(String(200), nullable=False)
    kind = Column(String(50), nullable=False, index=True)  # 与查询器分派键一致
    credential = Column(String(500), default="")           # 查询凭据（空则回落 provider.usage_api_key/api_key）
    credential_source = Column(String(20), default="manual")  # provider/manual/agent_file
    agent_app = Column(String(50), default="")             # agent_file 模式的凭据来源 agent
    base_url = Column(String(500), default="")             # 查询用 base_url（如 newapi 站点）
    extra_json = Column(Text, default="{}")                # 查询器附加参数（userId 等）
    # manual 模式额度字段（额度支持手动增加 ✅）
    total_quota = Column(Float, default=0)
    used_quota = Column(Float, default=0)
    quota_unit = Column(String(20), default="credits")     # credits/USD/tokens/requests/percent
    window_type = Column(String(20), default="none")       # 5h/7d/30d/monthly/none
    window_reset_at = Column(String(40), default="")       # ISO 时间，仅用户手填，不自动推算
    enabled = Column(Integer, default=1)                   # 未启用/未配置凭据 → 不显示
    last_queried_at = Column(String(40), default="")
    last_query_json = Column(Text, default="")             # 最近一次成功查询缓存（keep-last-good）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_agent_hub_sub_enabled_kind", "enabled", "kind"),
    )


class AgentHubSwitch(Base):
    """每个 agent 的当前激活供应商指针。"""
    __tablename__ = "agent_hub_switches"

    agent = Column(String(50), primary_key=True)
    provider_id = Column(String(64), default="")
    switched_at = Column(String(40), default="")
