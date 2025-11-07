"""add_subscription_fields_to_users

Revision ID: 7dc92d559294
Revises: 
Create Date: 2025-11-07 11:30:18.503518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dc92d559294'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add subscription fields to users table."""

    # Step 1: Add columns as nullable first (zero-downtime)
    op.add_column('users', sa.Column('subscription_tier', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('subscription_status', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('subscription_start_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('subscription_end_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('trial_end_date', sa.DateTime(), nullable=True))

    # Step 2: Backfill existing users with FREE plan
    op.execute("""
        UPDATE users
        SET subscription_tier = 'free',
            subscription_status = 'active',
            subscription_start_date = created_at
        WHERE subscription_tier IS NULL
    """)

    # Step 3: Add NOT NULL constraints and defaults after backfill
    op.alter_column('users', 'subscription_tier',
                    nullable=False,
                    server_default='free')

    op.alter_column('users', 'subscription_status',
                    nullable=False,
                    server_default='active')

    # Step 4: Create indexes for performance
    op.create_index('ix_users_subscription_tier', 'users', ['subscription_tier'])
    op.create_index('ix_users_subscription_status', 'users', ['subscription_status'])


def downgrade() -> None:
    """Downgrade schema - Remove subscription fields."""

    # Drop indexes first
    op.drop_index('ix_users_subscription_status', table_name='users')
    op.drop_index('ix_users_subscription_tier', table_name='users')

    # Drop columns
    op.drop_column('users', 'trial_end_date')
    op.drop_column('users', 'subscription_end_date')
    op.drop_column('users', 'subscription_start_date')
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'subscription_tier')
