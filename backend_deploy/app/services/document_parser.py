"""
文档解析服务
支持 Markdown、Word、PDF 格式
"""

from typing import Dict, List, Optional, Any
import re


class DocumentParser:
    """文档解析器"""

    @staticmethod
    def parse_markdown(content: str) -> Dict[str, Any]:
        """解析 Markdown 文档"""
        sections = DocumentParser._extract_sections(content)
        return {
            "title": DocumentParser._extract_title(content),
            "sections": sections,
            "full_content": content,
        }

    @staticmethod
    def parse_docx(file_path: str) -> Dict[str, Any]:
        """解析 Word 文档"""
        try:
            from docx import Document

            doc = Document(file_path)
            content = "\n".join(
                [para.text for para in doc.paragraphs if para.text.strip()]
            )
            return DocumentParser.parse_markdown(content)
        except ImportError:
            raise ValueError("python-docx not installed")

    @staticmethod
    def parse_pdf(file_path: str) -> Dict[str, Any]:
        """解析 PDF 文档"""
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                content = "\n".join(
                    [page.extract_text() or "" for page in reader.pages]
                )
            return DocumentParser.parse_markdown(content)
        except ImportError:
            raise ValueError("PyPDF2 not installed")

    @staticmethod
    def _extract_title(content: str) -> Optional[str]:
        """提取文档标题"""
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return lines[0][:50] if lines else None

    @staticmethod
    def _extract_sections(content: str) -> List[Dict[str, str]]:
        """提取章节结构"""
        sections = []
        lines = content.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            header_match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
            if header_match:
                if current_section:
                    sections.append(
                        {
                            "title": current_section,
                            "level": len(header_match.group(1)),
                            "content": "\n".join(current_content).strip(),
                        }
                    )
                current_section = header_match.group(2)
                current_content = []
            else:
                current_content.append(line)

        if current_section:
            sections.append(
                {
                    "title": current_section,
                    "level": 1,
                    "content": "\n".join(current_content).strip(),
                }
            )

        return sections

    @staticmethod
    def detect_missing_sections(parsed_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检测缺失的关键信息

        返回缺失的章节和建议问题
        """
        existing_titles = [s["title"].lower() for s in parsed_doc.get("sections", [])]

        required_sections = [
            {
                "key": "background",
                "keywords": ["背景", "项目", "产品定位"],
                "name": "项目背景",
            },
            {
                "key": "users",
                "keywords": ["用户", "目标用户", "用户画像"],
                "name": "目标用户",
            },
            {
                "key": "features",
                "keywords": ["功能", "需求", "feature"],
                "name": "功能需求",
            },
            {
                "key": "architecture",
                "keywords": ["架构", "设计", "流程"],
                "name": "架构设计",
            },
            {
                "key": "timeline",
                "keywords": ["时间", "计划", "roadmap", "里程碑"],
                "name": "项目计划",
            },
        ]

        missing = []
        for req in required_sections:
            found = any(
                any(kw in title for kw in req["keywords"]) for title in existing_titles
            )
            if not found:
                missing.append(
                    {
                        "section": req["name"],
                        "key": req["key"],
                        "suggested_questions": DocumentParser._get_questions_for_section(
                            req["key"]
                        ),
                    }
                )

        return missing

    @staticmethod
    def _get_questions_for_section(section_key: str) -> List[str]:
        """根据缺失的章节生成建议问题"""
        questions_map = {
            "background": [
                "这个产品要解决什么核心问题？",
                "产品的核心价值主张是什么？",
                "目标市场是什么？",
            ],
            "users": [
                "目标用户是谁？他们的特征是什么？",
                "用户的主要痛点是什么？",
                "用户在什么场景下会使用这个产品？",
            ],
            "features": [
                "核心功能有哪些？",
                "MVP 版本应该包含哪些功能？",
                "功能的优先级如何排序？",
            ],
            "architecture": [
                "产品的整体架构是怎样的？",
                "用户的主要操作流程是什么？",
                "有哪些关键的技术选型？",
            ],
            "timeline": [
                "项目的时间规划是怎样的？",
                "MVP 预计多久可以上线？",
                "后续的版本迭代计划是什么？",
            ],
        }
        return questions_map.get(section_key, ["请补充相关信息"])
