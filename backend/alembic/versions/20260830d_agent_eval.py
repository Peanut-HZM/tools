"""P3-⑨ Agent 评估框架 — agent_eval_runs / agent_eval_cases 表

迁移幂等，可重复运行。
"""
from alembic import op

revision = "20260830d"
down_revision = "20260830c"  # 接 P2-③ sandbox_enabled 迁移
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_eval_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID NOT NULL,
            user_id UUID NOT NULL,
            name VARCHAR(200) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            total_cases INTEGER NOT NULL DEFAULT 0,
            passed_cases INTEGER NOT NULL DEFAULT 0,
            avg_score FLOAT NOT NULL DEFAULT 0,
            total_duration_ms INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_eval_runs_agent ON agent_eval_runs (agent_id)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_eval_cases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id UUID NOT NULL REFERENCES agent_eval_runs(id) ON DELETE CASCADE,
            input TEXT NOT NULL,
            expected TEXT NOT NULL,
            actual_output TEXT,
            score FLOAT NOT NULL DEFAULT 0,
            judge_reasoning TEXT,
            latency_ms INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_eval_cases_run ON agent_eval_cases (run_id)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS agent_eval_cases")
    op.execute("DROP TABLE IF EXISTS agent_eval_runs")
