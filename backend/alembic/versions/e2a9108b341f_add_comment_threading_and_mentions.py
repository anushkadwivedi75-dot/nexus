"""add_comment_threading_and_mentions

Revision ID: e2a9108b341f
Revises: 510526a5ced7
Create Date: 2026-11-04 20:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e2a9108b341f'
down_revision: Union[str, Sequence[str], None] = '510526a5ced7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add parent_comment_id and version columns to comments
    op.add_column('comments', sa.Column('parent_comment_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('comments', sa.Column('version', sa.Integer(), server_default='1', nullable=False))

    # 2. Add unique constraint on (workspace_id, task_id, id) for composite FK targeting
    op.create_unique_constraint(
        'uq_comments_workspace_task_id',
        'comments',
        ['workspace_id', 'task_id', 'id']
    )

    # 3. Add composite self-referencing foreign key ensuring replies share workspace and task
    op.create_foreign_key(
        'fk_comments_parent_comment',
        'comments',
        'comments',
        ['workspace_id', 'task_id', 'parent_comment_id'],
        ['workspace_id', 'task_id', 'id'],
        ondelete='CASCADE'
    )

    # 4. Add indexes on comments for pagination, parent lookup, and workspace scoping
    op.create_index(
        'idx_comments_task_created_id',
        'comments',
        ['task_id', 'created_at', 'id'],
        unique=False
    )
    op.create_index(
        'idx_comments_parent_id',
        'comments',
        ['parent_comment_id'],
        unique=False
    )
    op.create_index(
        'idx_comments_workspace_task',
        'comments',
        ['workspace_id', 'task_id'],
        unique=False
    )

    # 5. Create comment_mentions table
    op.create_table(
        'comment_mentions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mentioned_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_comment_mentions'),
        sa.ForeignKeyConstraint(
            ['comment_id'],
            ['comments.id'],
            name='fk_comment_mentions_comment',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id', 'mentioned_user_id'],
            ['workspace_members.workspace_id', 'workspace_members.user_id'],
            name='fk_comment_mentions_member',
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('comment_id', 'mentioned_user_id', name='uq_comment_mentions_unique')
    )
    op.create_index(
        'idx_comment_mentions_user',
        'comment_mentions',
        ['workspace_id', 'mentioned_user_id'],
        unique=False
    )


def downgrade() -> None:
    # 1. Drop comment_mentions table and indexes
    op.drop_index('idx_comment_mentions_user', table_name='comment_mentions')
    op.drop_table('comment_mentions')

    # 2. Drop comments indexes and constraints
    op.drop_index('idx_comments_workspace_task', table_name='comments')
    op.drop_index('idx_comments_parent_id', table_name='comments')
    op.drop_index('idx_comments_task_created_id', table_name='comments')
    op.drop_constraint('fk_comments_parent_comment', 'comments', type_='foreignkey')
    op.drop_constraint('uq_comments_workspace_task_id', 'comments', type_='unique')

    # 3. Drop columns
    op.drop_column('comments', 'version')
    op.drop_column('comments', 'parent_comment_id')

