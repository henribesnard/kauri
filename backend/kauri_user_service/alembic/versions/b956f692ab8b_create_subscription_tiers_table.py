"""create_subscription_tiers_table

Revision ID: b956f692ab8b
Revises: 7dc92d559294
Create Date: 2025-11-07 11:30:50.171860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b956f692ab8b'
down_revision: Union[str, None] = '7dc92d559294'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create subscription_tiers reference table."""

    # Create subscription_tiers table
    op.create_table(
        'subscription_tiers',
        sa.Column('tier_id', sa.String(length=20), primary_key=True),
        sa.Column('tier_name', sa.String(length=50), nullable=False),
        sa.Column('tier_name_fr', sa.String(length=50), nullable=False),
        sa.Column('tier_description', sa.Text(), nullable=True),
        sa.Column('tier_description_fr', sa.Text(), nullable=True),

        # Quotas
        sa.Column('messages_per_day', sa.Integer(), nullable=True),  # NULL = unlimited
        sa.Column('messages_per_month', sa.Integer(), nullable=True),  # NULL = unlimited
        sa.Column('tokens_per_month', sa.BigInteger(), nullable=True),  # NULL = unlimited

        # Pricing (in FCFA)
        sa.Column('price_monthly', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('price_annual', sa.Integer(), nullable=True),

        # Features
        sa.Column('has_document_sourcing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_pdf_generation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_priority_support', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_custom_training', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_api_access', sa.Boolean(), nullable=False, server_default='false'),

        # Display
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Insert default tiers
    op.execute("""
        INSERT INTO subscription_tiers (
            tier_id, tier_name, tier_name_fr, tier_description, tier_description_fr,
            messages_per_day, messages_per_month, tokens_per_month,
            price_monthly, price_annual,
            has_document_sourcing, has_pdf_generation, has_priority_support,
            has_custom_training, has_api_access,
            display_order, is_active, is_visible
        ) VALUES
        -- FREE Plan
        (
            'free', 'Free', 'Gratuit',
            'Basic plan for students and casual users',
            'Plan de base pour étudiants et usage occasionnel',
            5, 150, 100000,
            0, NULL,
            false, false, false, false, false,
            1, true, true
        ),
        -- PRO Plan
        (
            'pro', 'Pro', 'Pro',
            'Professional plan for accountants and students',
            'Plan professionnel pour comptables et étudiants',
            100, 3000, 5000000,
            7000, 75600,
            true, true, false, false, false,
            2, true, true
        ),
        -- MAX Plan
        (
            'max', 'Max', 'Max',
            'Unlimited plan for accounting firms',
            'Plan illimité pour cabinets comptables',
            NULL, NULL, NULL,
            22000, 237600,
            true, true, true, false, false,
            3, true, true
        ),
        -- ENTERPRISE Plan
        (
            'enterprise', 'Enterprise', 'Entreprise',
            'Custom plan for large organizations',
            'Plan sur mesure pour grandes organisations',
            NULL, NULL, NULL,
            85000, NULL,
            true, true, true, true, true,
            4, true, true
        )
    """)

    # Create index
    op.create_index('ix_subscription_tiers_tier_id', 'subscription_tiers', ['tier_id'])


def downgrade() -> None:
    """Downgrade schema - Drop subscription_tiers table."""

    op.drop_index('ix_subscription_tiers_tier_id', table_name='subscription_tiers')
    op.drop_table('subscription_tiers')
