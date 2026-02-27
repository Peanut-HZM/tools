#!/usr/bin/env python3
"""
数据库迁移脚本：创建agents表并初始化默认Agent
"""

import sys

sys.path.insert(0, "/Users/huazhongmin/IdeaProjects/tools/backend")

from app.config.database import get_db_connection


def migrate():
    """执行迁移"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 创建agents表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                icon VARCHAR(50) DEFAULT 'fa-robot',
                icon_color VARCHAR(100) DEFAULT 'bg-blue-500',
                category VARCHAR(50) DEFAULT 'AI工具',
                is_active BOOLEAN DEFAULT TRUE,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # 检查是否已有数据
        cur.execute("SELECT COUNT(*) as count FROM agents;")
        result = cur.fetchone()

        if result["count"] == 0:
            # 初始化默认Agent：产品经理助手
            cur.execute("""
                INSERT INTO agents (id, name, description, system_prompt, icon, icon_color, category, is_active, is_default)
                VALUES (
                    gen_random_uuid(),
                    '产品经理助手',
                    '智能产品经理助手，支持竞品分析、PRD生成、需求梳理等功能',
                    '你是一个专业的产品经理助手，帮助用户进行产品规划和设计。\n\n你的职责包括：\n1. 理解用户需求，进行需求澄清\n2. 协助进行市场研究和竞品分析\n3. 设计产品架构和功能模块\n4. 撰写详细的产品需求文档（PRD）\n\n请用中文回复，保持专业、友好、有条理的对话风格。如果用户的需求不够清晰，请主动提问帮助澄清。',
                    'fa-user-tie',
                    'bg-gradient-to-r from-blue-500 to-indigo-500',
                    'AI工具',
                    TRUE,
                    TRUE
                );
            """)

            # 初始化默认Agent：代码助手
            cur.execute("""
                INSERT INTO agents (id, name, description, system_prompt, icon, icon_color, category, is_active, is_default)
                VALUES (
                    gen_random_uuid(),
                    '代码助手',
                    '智能编程助手，支持代码编写、调试、优化、代码审查等功能',
                    '你是一位资深软件工程师和编程专家。你的职责包括：\n\n1. 帮助用户编写高质量代码\n2. 协助调试和解决技术问题\n3. 提供代码优化建议\n4. 解释技术概念和最佳实践\n\n请用中文回复，代码注释使用英文。保持专业、耐心、有条理的风格。',
                    'fa-code',
                    'bg-gradient-to-r from-green-500 to-emerald-500',
                    '开发工具',
                    TRUE,
                    FALSE
                );
            """)

            # 初始化默认Agent：写作助手
            cur.execute("""
                INSERT INTO agents (id, name, description, system_prompt, icon, icon_color, category, is_active, is_default)
                VALUES (
                    gen_random_uuid(),
                    '写作助手',
                    '智能写作助手，支持文案创作、内容优化、翻译润色等功能',
                    '你是一位资深文字工作者和写作专家。你的职责包括：\n\n1. 协助用户创作各类文案和内容\n2. 提供写作建议和优化方案\n3. 帮助翻译和润色文字\n4. 提供创意思路和灵感\n\n请用中文回复，保持专业、有创意、易读的写作风格。',
                    'fa-pen-fancy',
                    'bg-gradient-to-r from-purple-500 to-pink-500',
                    'AI工具',
                    TRUE,
                    FALSE
                );
            """)

            print("✅ 已创建agents表并初始化3个默认Agent")
        else:
            print("✅ agents表已存在，跳过初始化")

        conn.commit()

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
