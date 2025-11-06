"""add user_feedback to messages

Revision ID: 20250106_001
Revises:
Create Date: 2025-01-06 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250106_001'
down_revision = '001'  # Points to initial schema migration
branch_labels = None
depends_on = None


def upgrade():
    """Add user_feedback column to messages table"""
    op.add_column(
        'messages',
        sa.Column('user_feedback', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    # Note: Default value is handled by SQLAlchemy model (default=dict)


def downgrade():
    """Remove user_feedback column from messages table"""
    op.drop_column('messages', 'user_feedback')
