"""Initial schema for conversations and messages

Revision ID: 001
Revises:
Create Date: 2025-01-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Create indexes for conversations
    op.create_index('idx_conversation_user_updated', 'conversations', ['user_id', 'updated_at'])
    op.create_index('idx_conversation_user_archived', 'conversations', ['user_id', 'is_archived'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='check_message_role')
    )

    # Create indexes for messages
    op.create_index('idx_message_conversation_created', 'messages', ['conversation_id', 'created_at'])
    op.create_index('idx_message_deleted', 'messages', ['deleted_at'])

    # Create conversation_tags table
    op.create_table(
        'conversation_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag', sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('conversation_id', 'tag', name='uq_conversation_tag')
    )

    # Create indexes for conversation_tags
    op.create_index('idx_tag_name', 'conversation_tags', ['tag'])


def downgrade() -> None:
    # Drop tables in reverse order (due to foreign keys)
    op.drop_table('conversation_tags')
    op.drop_table('messages')
    op.drop_table('conversations')
