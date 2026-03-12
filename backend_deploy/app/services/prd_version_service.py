"""
PRD 版本管理服务
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import PRDDocument


class PRDVersionService:
    """PRD 版本服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_versions(self, conversation_id: str) -> List[PRDDocument]:
        """获取所有版本"""
        return (
            self.db.query(PRDDocument)
            .filter(PRDDocument.conversation_id == conversation_id)
            .order_by(desc(PRDDocument.version_number))
            .all()
        )

    def get_version(self, prd_id: str) -> Optional[PRDDocument]:
        """获取指定版本"""
        return self.db.query(PRDDocument).filter(PRDDocument.id == prd_id).first()

    def create_version(
        self, conversation_id: str, content: str, status: str = "draft"
    ) -> PRDDocument:
        """创建新版本"""
        latest = (
            self.db.query(PRDDocument)
            .filter(PRDDocument.conversation_id == conversation_id)
            .order_by(desc(PRDDocument.version_number))
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

    def rollback_to_version(
        self, conversation_id: str, target_version: int
    ) -> Optional[PRDDocument]:
        """回滚到指定版本"""
        target = (
            self.db.query(PRDDocument)
            .filter(
                PRDDocument.conversation_id == conversation_id,
                PRDDocument.version_number == target_version,
            )
            .first()
        )

        if not target:
            return None

        # 创建新版本，内容复制自目标版本
        return self.create_version(
            conversation_id=conversation_id, content=target.content, status="draft"
        )

    def compare_versions(
        self, from_version: int, to_version: int, conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """对比两个版本"""
        from_prd = (
            self.db.query(PRDDocument)
            .filter(
                PRDDocument.conversation_id == conversation_id,
                PRDDocument.version_number == from_version,
            )
            .first()
        )

        to_prd = (
            self.db.query(PRDDocument)
            .filter(
                PRDDocument.conversation_id == conversation_id,
                PRDDocument.version_number == to_version,
            )
            .first()
        )

        if not from_prd or not to_prd:
            return None

        diff = self._generate_diff(from_prd.content, to_prd.content)

        return {
            "from_version": from_version,
            "to_version": to_version,
            "from_content": from_prd.content,
            "to_content": to_prd.content,
            "diff": diff,
        }

    def _generate_diff(self, old_content: str, new_content: str) -> str:
        """
        生成差异对比
        使用行级对比
        """
        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        diff_lines = []

        # 简化的 diff 算法
        max_len = max(len(old_lines), len(new_lines))

        for i in range(max_len):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None

            if old_line == new_line:
                diff_lines.append(f"  {old_line}")
            elif old_line and new_line:
                diff_lines.append(f"- {old_line}")
                diff_lines.append(f"+ {new_line}")
            elif old_line:
                diff_lines.append(f"- {old_line}")
            elif new_line:
                diff_lines.append(f"+ {new_line}")

        return "\n".join(diff_lines)
