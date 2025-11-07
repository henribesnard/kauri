"""create_user_usage_table

Revision ID: 5f20090c835c
Revises: b956f692ab8b
Create Date: 2025-11-07 11:31:28.565399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f20090c835c'
down_revision: Union[str, None] = 'b956f692ab8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create user_usage tracking table."""

    # Create user_usage table
    op.create_table(
        'user_usage',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),

        # Daily counters
        sa.Column('messages_today', sa.Integer(), nullable=False, server_default='0'),

        # Monthly counters
        sa.Column('messages_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_this_month', sa.BigInteger(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Create indexes
    op.create_index('ix_user_usage_user_id', 'user_usage', ['user_id'])
    op.create_index('ix_user_usage_usage_date', 'user_usage', ['usage_date'])
    op.create_index('ix_user_usage_user_date', 'user_usage', ['user_id', 'usage_date'], unique=True)

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_user_usage_user_id',
        'user_usage',
        'users',
        ['user_id'],
        ['user_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema - Drop user_usage table."""

    # Drop foreign key first
    op.drop_constraint('fk_user_usage_user_id', 'user_usage', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_user_usage_user_date', table_name='user_usage')
    op.drop_index('ix_user_usage_usage_date', table_name='user_usage')
    op.drop_index('ix_user_usage_user_id', table_name='user_usage')

    # Drop table
    op.drop_table('user_usage')
