"""
PRD 生成服务
处理 PRD 文档的生成和管理
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import PRDDocument


class PRDGeneratorService:
    """PRD 生成服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_prd(
        self, conversation_id: str, content: str, status: str = "draft"
    ) -> PRDDocument:
        """创建 PRD 文档"""
        # 获取当前最大版本号
        latest = (
            self.db.query(PRDDocument)
            .filter(PRDDocument.conversation_id == conversation_id)
            .order_by(PRDDocument.version_number.desc())
            .first()
        )

        version_number = 1 if not latest else latest.version_number + 1

        prd = PRDDocument(
            conversation_id=conversation_id,
            version_number=version_number,
            content=content,
            status=status,
        )

        self.db.add(prd)
        self.db.commit()
        self.db.refresh(prd)
        return prd

    def get_prd(self, prd_id: str) -> Optional[PRDDocument]:
        """获取 PRD 文档"""
        return self.db.query(PRDDocument).filter(PRDDocument.id == prd_id).first()

    def list_prds(
        self, conversation_id: str, skip: int = 0, limit: int = 50
    ) -> List[PRDDocument]:
        """获取会话的所有 PRD 版本"""
        return (
            self.db.query(PRDDocument)
            .filter(PRDDocument.conversation_id == conversation_id)
            .order_by(PRDDocument.version_number.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(self, prd_id: str, status: str) -> Optional[PRDDocument]:
        """更新 PRD 状态"""
        prd = self.get_prd(prd_id)
        if not prd:
            return None

        prd.status = status
        self.db.commit()
        self.db.refresh(prd)
        return prd

    def update_section(
        self, prd_id: str, section_title: str, section_content: str
    ) -> Optional[PRDDocument]:
        """更新 PRD 特定章节内容"""
        prd = self.get_prd(prd_id)
        if not prd:
            return None

        # 查找并替换章节内容
        import re
        
        # 匹配章节标题（支持 1-3 级标题）
        section_pattern = f"(#+\\s+{re.escape(section_title)}\\n)(.*?)(?=\\n#+\\s|$)"
        match = re.search(section_pattern, prd.content, re.DOTALL | re.IGNORECASE)
        
        if match:
            # 找到章节，替换内容
            old_section = match.group(0)
            header = match.group(1)
            new_section = f"{header}{section_content}\n\n"
            prd.content = prd.content.replace(old_section, new_section)
        else:
            # 章节不存在，添加到文档末尾
            prd.content += f"\n\n## {section_title}\n\n{section_content}\n\n"
        
        self.db.commit()
        self.db.refresh(prd)
        return prd

    async def generate_partial_prd(
        self,
        conversation_id: str,
        sections: List[str],
        context: List[Dict[str, str]],
        llm_service
    ) -> str:
        """
        生成 PRD 的指定章节
        
        Args:
            conversation_id: 会话 ID
            sections: 要生成的章节列表
            context: 对话上下文
            llm_service: LLM 服务实例
        
        Returns:
            生成的 PRD 内容
        """
        # 构建提示词
        section_list = ", ".join(sections)
        prompt = f"请为以下章节生成详细的 PRD 内容：{section_list}\n\n"
        
        # 添加对话上下文
        if context:
            prompt += "基于以下对话内容：\n"
            for msg in context[-10:]:  # 只使用最近 10 条消息
                sender = "用户" if msg.get("sender_type") == "user" else "AI"
                prompt += f"{sender}: {msg.get('content', '')}\n"
        
        prompt += "\n请生成专业、详细的产品需求文档内容。"
        
        # 调用 LLM 生成内容
        try:
            response = await llm_service.generate(prompt)
            return response
        except Exception as e:
            # 生成失败时返回模板
            return "\n\n".join([f"## {section}\n\n[待生成内容]" for section in sections])
        """更新 PRD 状态"""
        prd = self.get_prd(prd_id)
        if not prd:
            return None

        prd.status = status
        self.db.commit()
        self.db.refresh(prd)
        return prd

    async def generate_prd_content(
        self, context: List[Dict[str, str]], llm_service
    ) -> str:
        """
        使用 LLM 生成 PRD 内容

        Args:
            context: 对话上下文
            llm_service: LLM 服务实例

        Returns:
            PRD 内容 (Markdown 格式)
        """
        from app.services.llm.base import Message, GenerationConfig

        # 构建系统提示
        system_prompt = """你是一位资深产品经理，请根据用户的需求对话，生成一份完整的产品需求文档(PRD)。

PRD 应该包含以下章节：
1. 项目背景 - 产品定位、核心价值、目标用户
2. 竞品分析 - 市场调研、竞品对比、差异化策略
3. 产品架构 - 信息架构、功能模块
4. 功能需求 - 核心功能描述、用户流程
5. 非功能需求 - 性能、安全、兼容性
6. 数据需求 - 核心指标、埋点需求
7. 版本规划 - MVP功能、后续版本路线图
8. 附录 - 术语表、参考资料

请使用 Markdown 格式输出，流程图使用 Mermaid 语法。"""

        messages = [
            Message(role="system", content=system_prompt),
            *[Message(role=msg["role"], content=msg["content"]) for msg in context],
        ]

        config = GenerationConfig(temperature=0.7, max_tokens=4000)
        result = await llm_service.generate(messages, config)

        return result.content


class StageManager:
    """阶段管理器"""

    STAGES = [
        "requirement_clarification",  # 需求澄清
        "market_research",  # 市场研究
        "architecture_design",  # 架构设计
        "detailed_design",  # 详细设计
        "integration_output",  # 整合输出
    ]

    @classmethod
    def get_next_stage(cls, current_stage: str, context: List[Dict[str, str]]) -> str:
        """根据当前阶段和上下文，决定下一阶段"""
        try:
            current_idx = cls.STAGES.index(current_stage)
            if current_idx < len(cls.STAGES) - 1:
                return cls.STAGES[current_idx + 1]
            return current_stage
        except ValueError:
            return cls.STAGES[0]

    @classmethod
    def should_generate_prd(cls, stage: str) -> bool:
        """判断是否应该生成 PRD"""
        return stage in ["detailed_design", "integration_output"]

    @classmethod
    def should_analyze_competitor(cls, stage: str) -> bool:
        """判断是否应该进行竞品分析"""
        return stage == "market_research"
