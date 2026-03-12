"""add course platform tables

Revision ID: 20260307_course_platform
Revises: 5472dbd39274
Create Date: 2026-03-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '20260307_course_platform'
down_revision = '5472dbd39274'  # 依赖于 Product Manager Agent 表的迁移
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建课程分类表
    op.create_table('course_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='分类名称'),
        sa.Column('slug', sa.String(length=50), nullable=False, comment='分类标识符'),
        sa.Column('parent_id', sa.Integer(), nullable=True, comment='父分类 ID'),
        sa.Column('sort_order', sa.Integer(), server_default='0', comment='排序'),
        sa.Column('icon', sa.String(length=50), nullable=True, comment='图标'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['course_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_course_categories_slug'), 'course_categories', ['slug'], unique=True)

    # 2. 创建课程主表
    op.create_table('courses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False, comment='课程标题'),
        sa.Column('slug', sa.String(length=100), nullable=False, comment='课程标识符'),
        sa.Column('description', sa.Text(), nullable=False, comment='课程描述'),
        sa.Column('cover_image', sa.String(length=500), nullable=True, comment='封面图 URL'),
        sa.Column('category_id', sa.Integer(), nullable=True, comment='分类 ID'),
        sa.Column('instructor_id', sa.String(length=64), nullable=True, comment='讲师 ID'),
        sa.Column('price', sa.DECIMAL(10, 2), server_default='0', nullable=True, comment='价格'),
        sa.Column('status', sa.String(length=20), server_default='draft', nullable=True, comment='状态'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['course_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_courses_slug'), 'courses', ['slug'], unique=True)

    # 3. 创建课程章节表
    op.create_table('course_chapters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False, comment='课程 ID'),
        sa.Column('slug', sa.String(length=100), nullable=False, comment='章节标识符'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='章节标题'),
        sa.Column('order', sa.Integer(), server_default='0', comment='章节顺序'),
        sa.Column('content', sa.Text(), nullable=False, comment='章节内容'),
        sa.Column('chapter_type', sa.String(length=50), server_default='story', comment='类型'),
        sa.Column('video_url', sa.String(length=500), nullable=True, comment='视频链接'),
        sa.Column('is_locked', sa.Boolean(), server_default='0', comment='是否锁定'),
        sa.Column('duration_minutes', sa.Integer(), server_default='0', comment='学习时长'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_chapters_course_id'), 'course_chapters', ['course_id'], unique=False)

    # 4. 创建课程测验表
    op.create_table('course_quizzes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False, comment='章节 ID'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='测验标题'),
        sa.Column('passing_score', sa.Integer(), server_default='60', comment='及格分数'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['course_chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. 创建测验题目表
    op.create_table('course_quiz_questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False, comment='测验 ID'),
        sa.Column('question_text', sa.Text(), nullable=False, comment='题目内容'),
        sa.Column('question_type', sa.String(length=20), server_default='single', comment='类型'),
        sa.Column('correct_answer', sa.String(length=100), nullable=False, comment='正确答案'),
        sa.Column('explanation', sa.Text(), nullable=True, comment='答案解析'),
        sa.Column('order', sa.Integer(), server_default='0', comment='题目顺序'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['course_quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. 创建测验选项表
    op.create_table('course_quiz_options',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False, comment='题目 ID'),
        sa.Column('option_text', sa.Text(), nullable=False, comment='选项内容'),
        sa.Column('option_index', sa.Integer(), nullable=False, comment='选项索引'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['course_quiz_questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. 创建课程资源表
    op.create_table('course_resources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False, comment='章节 ID'),
        sa.Column('resource_type', sa.String(length=50), nullable=False, comment='资源类型'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='资源标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='资源内容'),
        sa.Column('file_url', sa.String(length=500), nullable=True, comment='文件 URL'),
        sa.Column('file_size', sa.Integer(), nullable=True, comment='文件大小'),
        sa.Column('extra_data', sa.Text(), nullable=True, comment='额外元数据'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['course_chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_resources_chapter_id'), 'course_resources', ['chapter_id'], unique=False)

    # 8. 创建用户课程关联表
    op.create_table('course_enrollments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False, comment='用户 ID'),
        sa.Column('course_id', sa.Integer(), nullable=False, comment='课程 ID'),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='报名时间'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
        sa.Column('status', sa.String(length=20), server_default='active', comment='状态'),
        sa.Column('progress_percent', sa.Float(), server_default='0', comment='进度百分比'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'course_id', name='uq_course_user_course')
    )
    op.create_index(op.f('ix_course_enrollments_user_id'), 'course_enrollments', ['user_id'], unique=False)

    # 9. 创建学习进度表
    op.create_table('course_progress',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False, comment='用户 ID'),
        sa.Column('chapter_id', sa.Integer(), nullable=False, comment='章节 ID'),
        sa.Column('status', sa.String(length=20), server_default='not_started', comment='状态'),
        sa.Column('quiz_score', sa.Float(), nullable=True, comment='测验分数'),
        sa.Column('quiz_passed', sa.Boolean(), server_default='0', comment='测验是否通过'),
        sa.Column('video_progress', sa.Integer(), server_default='0', comment='视频进度'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='最后访问时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['course_chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'chapter_id', name='uq_course_user_chapter')
    )
    op.create_index(op.f('ix_course_progress_user_id'), 'course_progress', ['user_id'], unique=False)

    # 10. 创建课程互动表
    op.create_table('course_interactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False, comment='用户 ID'),
        sa.Column('course_id', sa.Integer(), nullable=False, comment='课程 ID'),
        sa.Column('interaction_type', sa.String(length=20), nullable=False, comment='互动类型'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'course_id', 'interaction_type', name='uq_course_user_interaction')
    )
    op.create_index(op.f('ix_course_interactions_user_id'), 'course_interactions', ['user_id'], unique=False)

    # 11. 创建课程评价表
    op.create_table('course_reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False, comment='用户 ID'),
        sa.Column('course_id', sa.Integer(), nullable=False, comment='课程 ID'),
        sa.Column('rating', sa.Integer(), nullable=False, comment='评分'),
        sa.Column('comment', sa.Text(), nullable=True, comment='评论内容'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_reviews_user_id'), 'course_reviews', ['user_id'], unique=False)

    # 12. 创建课程统计表
    op.create_table('course_statistics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False, comment='课程 ID'),
        sa.Column('view_count', sa.Integer(), server_default='0', comment='浏览次数'),
        sa.Column('enroll_count', sa.Integer(), server_default='0', comment='报名人数'),
        sa.Column('like_count', sa.Integer(), server_default='0', comment='点赞数'),
        sa.Column('bookmark_count', sa.Integer(), server_default='0', comment='收藏数'),
        sa.Column('review_count', sa.Integer(), server_default='0', comment='评价数'),
        sa.Column('avg_rating', sa.Float(), server_default='0', comment='平均评分'),
        sa.Column('completed_count', sa.Integer(), server_default='0', comment='完成人数'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id')
    )


def downgrade() -> None:
    # 逆序删除表
    op.drop_table('course_statistics')
    op.drop_table('course_reviews')
    op.drop_table('course_interactions')
    op.drop_table('course_progress')
    op.drop_table('course_enrollments')
    op.drop_table('course_resources')
    op.drop_table('course_quiz_options')
    op.drop_table('course_quiz_questions')
    op.drop_table('course_quizzes')
    op.drop_table('course_chapters')
    op.drop_table('courses')
    op.drop_table('course_categories')
