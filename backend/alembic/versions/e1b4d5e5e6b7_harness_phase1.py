"""harness phase1

Revision ID: e1b4d5e5e6b7
Revises: migrate_model_categories_20260824
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'e1b4d5e5e6b7'
down_revision: Union[str, None] = 'migrate_model_categories_20260824'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 扩展 agents 表 ===
    # 使用 batch_alter_table 确保 SQLite 和 PostgreSQL 兼容
    with op.batch_alter_table('agents') as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('welcome_message', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('default_model_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('fallback_model_ids', sa.JSON(), server_default='[]'))
        batch_op.add_column(sa.Column('generation_params', sa.JSON(), server_default='{}'))
        batch_op.add_column(sa.Column('memory_short_term_policy', sa.String(20), server_default='sliding_window'))
        batch_op.add_column(sa.Column('memory_short_term_window', sa.Integer(), server_default='20'))
        batch_op.add_column(sa.Column('memory_long_term_enabled', sa.Boolean(), server_default=sa.text('0')))
        batch_op.add_column(sa.Column('memory_long_term_config', sa.JSON(), server_default='{}'))
        batch_op.add_column(sa.Column('max_steps_per_turn', sa.Integer(), server_default='20'))
        batch_op.add_column(sa.Column('tool_timeout_seconds', sa.Integer(), server_default='60'))
        batch_op.add_column(sa.Column('error_strategy', sa.String(20), server_default='fallback_message'))
        batch_op.add_column(sa.Column('max_retries', sa.Integer(), server_default='2'))
        batch_op.add_column(sa.Column('can_handoff_to', sa.JSON(), server_default='[]'))
        batch_op.add_column(sa.Column('handoff_instruction', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('input_guardrails', sa.JSON(), server_default='[]'))
        batch_op.add_column(sa.Column('output_guardrails', sa.JSON(), server_default='[]'))
        batch_op.add_column(sa.Column('guardrail_on_violation', sa.String(20), server_default='block'))
        batch_op.add_column(sa.Column('visibility', sa.String(20), server_default='public'))
        batch_op.add_column(sa.Column('owner_id', sa.Uuid(), nullable=True))

    # 填充 slug：跨数据库兼容的 Python 侧逻辑
    import re
    bind = op.get_bind()
    agents = bind.execute(sa.text("SELECT id, name FROM agents WHERE slug IS NULL")).fetchall()
    for agent_id, name in agents:
        base_slug = re.sub(r'[^a-zA-Z0-9一-龥]+', '-', name or 'agent').lower().strip('-')
        base_slug = base_slug[:45]
        new_slug = base_slug
        counter = 1
        while bind.execute(sa.text("SELECT 1 FROM agents WHERE slug = :s"), {"s": new_slug}).fetchone():
            new_slug = f"{base_slug}-{counter}"
            counter += 1
        bind.execute(sa.text("UPDATE agents SET slug = :s WHERE id = :id"), {"s": new_slug, "id": agent_id})

    # NOT NULL + UNIQUE 约束
    dialect_name = bind.dialect.name
    if dialect_name == 'postgresql':
        op.alter_column('agents', 'slug', nullable=False)
        op.create_unique_constraint('uq_agents_slug', 'agents', ['slug'])
    else:
        # SQLite batch 模式：重建表以应用约束
        with op.batch_alter_table('agents') as batch_op:
            batch_op.alter_column('slug', nullable=False)
            batch_op.create_unique_constraint('uq_agents_slug', ['slug'])

    # === 扩展 conversations 表 ===
    # 先添加 nullable 的 agent_id，以便数据迁移
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.add_column(sa.Column('agent_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('metadata', sa.JSON(), server_default='{}'))

    # 历史会话填默认 agent（如已有默认）或创建系统默认
    bind = op.get_bind()
    default_agent = bind.execute(sa.text("SELECT id FROM agents WHERE is_default = 1 LIMIT 1")).fetchone()
    if default_agent:
        default_agent_id = default_agent[0]
    else:
        import uuid
        new_id = str(uuid.uuid4())
        bind.execute(sa.text(
            "INSERT INTO agents (id, name, slug, description, system_prompt, is_default, is_active, visibility) "
            "VALUES (:id, '默认助手', 'default-assistant', '默认 AI 助手', '你是一个友好的 AI 助手。', 1, 1, 'public')"
        ), {"id": new_id})
        default_agent_id = new_id
    bind.execute(sa.text("UPDATE conversations SET agent_id = :aid WHERE agent_id IS NULL"), {"aid": default_agent_id})

    # 应用 NOT NULL + FK + 索引
    if dialect_name == 'postgresql':
        op.alter_column('conversations', 'agent_id', nullable=False)
        op.create_foreign_key('fk_conversations_agent_id', 'conversations', 'agents', ['agent_id'], ['id'])
        op.create_index('ix_conversations_user_agent_status', 'conversations', ['user_id', 'agent_id', 'status'])
    else:
        with op.batch_alter_table('conversations') as batch_op:
            batch_op.alter_column('agent_id', nullable=False)
            batch_op.create_foreign_key('fk_conversations_agent_id', 'agents', ['agent_id'], ['id'])
        # 注意：ix_conversations_user_agent_status 索引引用了 status 列，
    # 但当前 conversations 模型中无此列，暂不创建此索引。
    # 后续 Task 若添加 status 列，应补建此索引。
    # op.create_index('ix_conversations_user_agent_status', 'conversations', ['user_id', 'agent_id', 'status'])

    # === 扩展 messages 表 ===
    with op.batch_alter_table('messages') as batch_op:
        batch_op.add_column(sa.Column('tool_calls', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('tool_call_id', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('tool_name', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('attachments', sa.JSON(), server_default='[]'))

    # === 创建 tools 表 ===
    op.create_table(
        'tools',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('parameters_schema', sa.JSON(), nullable=False),
        sa.Column('returns_schema', sa.JSON(), nullable=True),
        sa.Column('is_available_condition', sa.JSON(), server_default='{}'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )

    # === 创建 agent_tools 表 ===
    op.create_table(
        'agent_tools',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('agent_id', sa.Uuid(), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_id', sa.Uuid(), sa.ForeignKey('tools.id'), nullable=False),
        sa.Column('parameter_overrides', sa.JSON(), server_default='{}'),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.UniqueConstraint('agent_id', 'tool_id'),
    )
    op.create_index('ix_agent_tools_agent_id', 'agent_tools', ['agent_id'])

    # === 创建 session_checkpoints 表 ===
    op.create_table(
        'session_checkpoints',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('conversation_id', sa.Uuid(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('phase', sa.String(20), nullable=False),
        sa.Column('messages_ref', sa.Uuid(), nullable=True),
        sa.Column('agent_state', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_index('ix_checkpoints_conv_step', 'session_checkpoints', ['conversation_id', 'step_index'])

    # === 创建 agent_memories 表 ===
    op.create_table(
        'agent_memories',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('agent_id', sa.Uuid(), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('scope', sa.String(20), server_default='agent_user'),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_conversation_id', sa.Uuid(), nullable=True),
        sa.Column('source_message_id', sa.Uuid(), nullable=True),
        sa.Column('importance', sa.Float(), server_default='0.5'),
        sa.Column('access_count', sa.Integer(), server_default='0'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_index('ix_memories_agent_user_scope', 'agent_memories', ['agent_id', 'user_id', 'scope'])

    # === 创建 agent_traces 表 ===
    op.create_table(
        'agent_traces',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('input_text', sa.Text(), nullable=False),
        sa.Column('output_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('total_steps', sa.Integer(), server_default='0'),
        sa.Column('total_tokens', sa.Integer(), server_default='0'),
        sa.Column('total_duration_ms', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_traces_agent_started', 'agent_traces', ['agent_id', 'started_at'])
    op.create_index('ix_traces_user_started', 'agent_traces', ['user_id', 'started_at'])

    # === 创建 trace_steps 表 ===
    op.create_table(
        'trace_steps',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('trace_id', sa.Uuid(), sa.ForeignKey('agent_traces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(20), nullable=False),
        sa.Column('tool_name', sa.String(100), nullable=True),
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), server_default='0'),
        sa.Column('duration_ms', sa.Integer(), server_default='0'),
        sa.Column('input_summary', sa.Text(), nullable=True),
        sa.Column('output_summary', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_index('ix_trace_steps_trace_id', 'trace_steps', ['trace_id'])


def downgrade() -> None:
    op.drop_table('trace_steps')
    op.drop_table('agent_traces')
    op.drop_table('agent_memories')
    op.drop_table('session_checkpoints')
    op.drop_table('agent_tools')
    op.drop_table('tools')

    with op.batch_alter_table('messages') as batch_op:
        batch_op.drop_column('attachments')
        batch_op.drop_column('tool_name')
        batch_op.drop_column('tool_call_id')
        batch_op.drop_column('tool_calls')

    # 索引 ix_conversations_user_agent_status 未创建（status 列不存在），无需 drop
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.drop_constraint('fk_conversations_agent_id', type_='foreignkey')
        batch_op.drop_column('metadata')
        batch_op.drop_column('agent_id')

    with op.batch_alter_table('agents') as batch_op:
        batch_op.drop_constraint('uq_agents_slug', type_='unique')
        batch_op.drop_column('owner_id')
        batch_op.drop_column('visibility')
        batch_op.drop_column('guardrail_on_violation')
        batch_op.drop_column('output_guardrails')
        batch_op.drop_column('input_guardrails')
        batch_op.drop_column('handoff_instruction')
        batch_op.drop_column('can_handoff_to')
        batch_op.drop_column('max_retries')
        batch_op.drop_column('error_strategy')
        batch_op.drop_column('tool_timeout_seconds')
        batch_op.drop_column('max_steps_per_turn')
        batch_op.drop_column('memory_long_term_config')
        batch_op.drop_column('memory_long_term_enabled')
        batch_op.drop_column('memory_short_term_window')
        batch_op.drop_column('memory_short_term_policy')
        batch_op.drop_column('generation_params')
        batch_op.drop_column('fallback_model_ids')
        batch_op.drop_column('default_model_id')
        batch_op.drop_column('welcome_message')
        batch_op.drop_column('slug')
