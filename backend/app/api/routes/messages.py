"""
消息路由 - 支持文件上传
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import tempfile
import uuid

from app.api.dependencies import get_db, get_current_user
from app.services.conversation_service import MessageService, ConversationService
from app.services.document_parser import DocumentParser
from app.models import Message

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageCreate(BaseModel):
    """创建消息请求"""

    content: str = Field(..., min_length=1)
    message_type: str = Field(default="text", description="消息类型：text, file")


@router.post("/upload", response_model=dict)
async def upload_document(
    conversation_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    上传文档并解析内容

    支持格式：Markdown (.md), Word (.docx), PDF (.pdf)
    """
    # 验证会话所有权
    conv_service = ConversationService(db)
    conversation = conv_service.get_conversation(conversation_id, current_user["id"])

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 验证文件类型
    allowed_extensions = {".md", ".docx", ".pdf"}
    file_ext = os.path.splitext(file.filename or "")[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持：{', '.join(allowed_extensions)}",
        )

    # 保存临时文件
    temp_dir = tempfile.gettempdir()
    temp_filename = f"{uuid.uuid4()}{file_ext}"
    temp_path = os.path.join(temp_dir, temp_filename)

    try:
        # 读取文件内容
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # 解析文档
        parser = DocumentParser()

        if file_ext == ".md":
            parsed = parser.parse_markdown(content.decode("utf-8"))
        elif file_ext == ".docx":
            parsed = parser.parse_docx(temp_path)
        elif file_ext == ".pdf":
            parsed = parser.parse_pdf(temp_path)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式")

        # 检测缺失的章节
        missing_sections = parser.detect_missing_sections(parsed)

        # 创建用户消息（包含文件信息）
        msg_service = MessageService(db)
        user_message = msg_service.create_message(
            conversation_id=conversation_id,
            sender_type="user",
            content=f"上传了文档：{file.filename}",
            message_type="file",
            metadata={
                "filename": file.filename,
                "file_type": file_ext,
                "parsed_content": parsed.get("full_content", ""),
                "title": parsed.get("title"),
                "sections": parsed.get("sections", []),
            },
        )

        # 生成 AI 响应 - 分析文档并提问
        ai_content = _generate_document_analysis_response(parsed, missing_sections)

        agent_message = msg_service.create_message(
            conversation_id=conversation_id,
            sender_type="agent",
            content=ai_content,
            message_type="text",
        )

        return {
            "user_message": _message_to_dict(user_message),
            "agent_message": _message_to_dict(agent_message),
            "parsed_document": {
                "title": parsed.get("title"),
                "section_count": len(parsed.get("sections", [])),
                "missing_sections": missing_sections,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件处理失败：{str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _generate_document_analysis_response(
    parsed_doc: dict, missing_sections: List[dict]
) -> str:
    """生成文档分析响应"""

    title = parsed_doc.get("title", "未命名文档")
    sections = parsed_doc.get("sections", [])

    response = f"# 文档分析结果\n\n"
    response += f"## 文档标题：{title}\n\n"
    response += f"## 已识别的章节 ({len(sections)}个)\n\n"

    for section in sections:
        response += f"- **{section.get('title', '无标题')}**\n"

    if missing_sections:
        response += f"\n## 缺失的关键信息 ({len(missing_sections)}个)\n\n"
        response += "为了生成更完整的 PRD，建议您补充以下信息：\n\n"

        for i, missing in enumerate(missing_sections, 1):
            response += f"### {i}. {missing['section']}\n"
            response += "**建议问题：**\n"
            for q in missing.get("suggested_questions", [])[:2]:  # 只显示前 2 个问题
                response += f"- {q}\n"
            response += "\n"
    else:
        response += "\n✅ **文档结构完整**，没有发现缺失的关键章节。\n\n"
        response += "您现在可以：\n"
        response += "1. 要求我基于此文档生成 PRD\n"
        response += "2. 继续补充更多细节\n"
        response += "3. 上传其他相关文档\n"

    response += "\n---\n\n**接下来您想做什么？** 请告诉我您的需求。"

    return response


def _message_to_dict(msg: Message) -> dict:
    """将 SQLAlchemy Message 对象转换为字典"""
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "sender_type": msg.sender_type,
        "content": msg.content,
        "message_type": msg.message_type,
        "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
    }


# 需要导入 BaseModel 和 Field
from pydantic import BaseModel, Field
