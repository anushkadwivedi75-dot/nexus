"""add_notification_inbox_and_deduplication

Revision ID: b3f18e9a2c41
Revises: e2a9108b341f
Create Date: 2026-11-04 21:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b3f18e9a2c41'
down_revision: Union[str, Sequence[str], None] = 'e2a9108b341f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to notifications table
    op.add_column(
        'notifications',
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False)
    )
    op.add_column('notifications', sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('notifications', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('notifications', sa.Column('deduplication_key', sa.String(length=255), nullable=True))

    # 2. Add performance indexes
    op.create_index(
        'idx_notifications_inbox',
        'notifications',
        ['recipient_id', 'archived_at', 'is_read', sa.text('created_at DESC')],
        unique=False
    )
    op.create_index(
        'idx_notifications_unread_count',
        'notifications',
        ['recipient_id'],
        unique=False,
        postgresql_where=sa.text('archived_at IS NULL AND is_read = false')
    )
    op.create_index(
        'idx_notifications_dedup',
        'notifications',
        ['workspace_id', 'recipient_id', 'deduplication_key'],
        unique=False,
        postgresql_where=sa.text('deduplication_key IS NOT NULL')
    )


def downgrade() -> None:
    # 1. Drop indexes
    op.drop_index('idx_notifications_dedup', table_name='notifications', postgresql_where=sa.text('deduplication_key IS NOT NULL'))
    op.drop_index('idx_notifications_unread_count', table_name='notifications', postgresql_where=sa.text('archived_at IS NULL AND is_read = false'))
    op.drop_index('idx_notifications_inbox', table_name='notifications')

    # 2. Drop columns
    op.drop_column('notifications', 'deduplication_key')
    op.drop_column('notifications', 'archived_at')
    op.drop_column('notifications', 'read_at')
    op.drop_column('notifications', 'payload')
