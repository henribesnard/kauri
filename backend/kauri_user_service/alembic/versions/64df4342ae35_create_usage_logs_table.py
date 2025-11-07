"""create_usage_logs_table

Revision ID: 64df4342ae35
Revises: 5f20090c835c
Create Date: 2025-11-07 11:31:59.986145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64df4342ae35'
down_revision: Union[str, None] = '5f20090c835c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create usage_logs audit table."""

    # Create usage_logs table for audit trail
    op.create_table(
        'usage_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),  # 'message_sent', 'quota_exceeded', etc.
        sa.Column('event_timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        # Usage details
        sa.Column('messages_count', sa.Integer(), nullable=True),
        sa.Column('tokens_count', sa.BigInteger(), nullable=True),

        # Context
        sa.Column('quota_tier', sa.String(length=20), nullable=True),
        sa.Column('quota_status', sa.String(length=20), nullable=True),  # 'allowed', 'exceeded', 'warning'
        sa.Column('request_ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),

        # Additional metadata (renamed to avoid SQLAlchemy reserved name)
        sa.Column('event_metadata', sa.JSON(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
    )

    # Create indexes for fast queries
    op.create_index('ix_usage_logs_user_id', 'usage_logs', ['user_id'])
    op.create_index('ix_usage_logs_event_type', 'usage_logs', ['event_type'])
    op.create_index('ix_usage_logs_event_timestamp', 'usage_logs', ['event_timestamp'])
    op.create_index('ix_usage_logs_user_event', 'usage_logs', ['user_id', 'event_type'])

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_usage_logs_user_id',
        'usage_logs',
        'users',
        ['user_id'],
        ['user_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema - Drop usage_logs table."""

    # Drop foreign key first
    op.drop_constraint('fk_usage_logs_user_id', 'usage_logs', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_usage_logs_user_event', table_name='usage_logs')
    op.drop_index('ix_usage_logs_event_timestamp', table_name='usage_logs')
    op.drop_index('ix_usage_logs_event_type', table_name='usage_logs')
    op.drop_index('ix_usage_logs_user_id', table_name='usage_logs')

    # Drop table
    op.drop_table('usage_logs')
