"""向 PostgreSQL tools 表幂等插入 Agent Hub 工具行（前端侧栏入口）。

用法: python scripts/seed_agent_hub_tool.py          # 默认 dry-run
      python scripts/seed_agent_hub_tool.py --apply  # 实际插入
"""
import sys

sys.path.insert(0, ".")

from app.config.database import get_pooled_db_connection, release_db_connection

TOOL_ROW = {
    "id": "agent-hub",
    "title": "Agent 订阅中心",
    "description": "管理各 Agent CLI 的供应商与订阅套餐：一键切换、套餐额度用量显示（含 OpenDesign 等）、额度手动调整",
    "icon": "fa-random",
    "icon_color": "bg-indigo-500",
    "category": "开发工具",
    "status": "online",
    "rating": 5.0,
    "usage_count": 0,
    "show_pc": True,
    "show_mobile": True,
    "require_login": True,
}


def main() -> None:
    apply = "--apply" in sys.argv
    conn = get_pooled_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM tools WHERE id = %s", (TOOL_ROW["id"],))
    exists = cur.fetchone()["c"]
    if exists:
        print(f"✅ tools 行 id={TOOL_ROW['id']} 已存在，跳过（幂等）")
        release_db_connection(conn)
        return
    if not apply:
        print(f"[dry-run] 将插入工具行: id={TOOL_ROW['id']} title={TOOL_ROW['title']}（--apply 生效）")
        release_db_connection(conn)
        return
    cur.execute(
        """
        INSERT INTO tools (id, title, description, icon, icon_color, category,
                           status, rating, usage_count, show_pc, show_mobile,
                           require_login)
        VALUES (%(id)s, %(title)s, %(description)s, %(icon)s, %(icon_color)s, %(category)s,
                %(status)s, %(rating)s, %(usage_count)s, %(show_pc)s,
                %(show_mobile)s, %(require_login)s)
        """,
        TOOL_ROW,
    )
    conn.commit()
    cur.execute("SELECT id, title FROM tools WHERE id = %s", (TOOL_ROW["id"],))
    row = cur.fetchone()
    print(f"✅ 已插入 tools 行: {row['id']} / {row['title']}")
    release_db_connection(conn)


if __name__ == "__main__":
    main()
