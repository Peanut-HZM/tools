#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import get_db_connection
from app.data.tools_data import get_all_tools

TOOL_ID = "token-usage"


def main():
    print("=== Token Usage Stats Tool Migration ===")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, category, status FROM tools WHERE id = %s", (TOOL_ID,)
    )
    row = cursor.fetchone()

    if row:
        print(
            f"✓ Tool exists: title='{row['title']}', category='{row['category']}', status='{row['status']}'"
        )
        conn.close()
        return

    print("Tool not found. Inserting from TOOLS_DATA...")

    tools_data = get_all_tools()
    target = next((t for t in tools_data if t.id == TOOL_ID), None)

    if not target:
        print("✗ ERROR: Tool not found in TOOLS_DATA!")
        conn.close()
        sys.exit(1)

    cursor.execute(
        """INSERT INTO tools
        (id, title, description, icon, icon_color, category, status, usage_count, rating, sort_order, show_pc, show_mobile, require_login)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING""",
        (
            target.id,
            target.title,
            target.description,
            target.icon,
            target.icon_color,
            target.category,
            "online",
            target.usage_count,
            target.rating,
            999,
            True,
            True,
            False,
        ),
    )
    conn.commit()

    cursor.execute(
        "SELECT id, title, category, status, show_pc, show_mobile FROM tools WHERE id = %s",
        (TOOL_ID,),
    )
    result = cursor.fetchone()
    if result:
        print(
            f"✓ Tool added: ID={result['id']}, Title={result['title']}, Category={result['category']}, Status={result['status']}"
        )
        print(f"  Show PC={result['show_pc']}, Show Mobile={result['show_mobile']}")
        print("  Visit http://localhost:5178/admin/tools and http://localhost:5178/")
    else:
        print("✗ Failed to insert!")
        conn.close()
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
