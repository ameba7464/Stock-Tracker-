"""simplify subscription model

Revision ID: 20251207_2126
Revises: 36ebfda600fc
Create Date: 2025-12-07 21:26:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251207_2126'
down_revision = '36ebfda600fc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Simplify subscription model - keep only has_access and status."""
    
    # Drop dependent views first
    op.execute("DROP VIEW IF EXISTS v_active_users CASCADE")
    
    # Drop columns we don't need (checking if they exist first)
    op.execute("""
        DO $$ 
        BEGIN
            -- Drop Stripe-related columns
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='stripe_customer_id') THEN
                ALTER TABLE subscriptions DROP COLUMN stripe_customer_id CASCADE;
            END IF;
            
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='stripe_subscription_id') THEN
                ALTER TABLE subscriptions DROP COLUMN stripe_subscription_id CASCADE;
            END IF;
            
            -- Drop quota columns
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='quota_used') THEN
                ALTER TABLE subscriptions DROP COLUMN quota_used CASCADE;
            END IF;
            
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='quota_limit') THEN
                ALTER TABLE subscriptions DROP COLUMN quota_limit CASCADE;
            END IF;
            
            -- Drop billing period columns
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='current_period_start') THEN
                ALTER TABLE subscriptions DROP COLUMN current_period_start CASCADE;
            END IF;
            
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='current_period_end') THEN
                ALTER TABLE subscriptions DROP COLUMN current_period_end CASCADE;
            END IF;
            
            -- Drop plan_type column
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='plan_type') THEN
                ALTER TABLE subscriptions DROP COLUMN plan_type CASCADE;
            END IF;
        END $$;
    """)
    
    # Drop old enums if they exist
    op.execute("DROP TYPE IF EXISTS plan_type CASCADE")
    op.execute("DROP TYPE IF EXISTS subscription_status CASCADE")
    
    # Convert status column to string if it isn't already
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='status') THEN
                -- Change status column type to VARCHAR
                ALTER TABLE subscriptions ALTER COLUMN status TYPE VARCHAR;
                ALTER TABLE subscriptions ALTER COLUMN status SET DEFAULT 'unpaid';
            ELSE
                -- Add status column if it doesn't exist
                ALTER TABLE subscriptions ADD COLUMN status VARCHAR NOT NULL DEFAULT 'unpaid';
            END IF;
        END $$;
    """)
    
    # Add has_access column if it doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='subscriptions' AND column_name='has_access') THEN
                ALTER TABLE subscriptions ADD COLUMN has_access BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Restore original subscription model."""
    
    # Recreate enums
    op.execute("CREATE TYPE plan_type AS ENUM ('free', 'starter', 'pro', 'enterprise')")
    op.execute("CREATE TYPE subscription_status AS ENUM ('trial', 'active', 'expired', 'cancelled')")
    
    # Drop new columns
    op.drop_column('subscriptions', 'has_access')
    op.drop_column('subscriptions', 'status')
    
    # Restore old columns
    op.add_column('subscriptions', sa.Column('plan_type', postgresql.ENUM('free', 'starter', 'pro', 'enterprise', name='plan_type'), nullable=False, server_default='free'))
    op.add_column('subscriptions', sa.Column('status', postgresql.ENUM('trial', 'active', 'expired', 'cancelled', name='subscription_status'), nullable=False, server_default='trial'))
    op.add_column('subscriptions', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('stripe_subscription_id', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('quota_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('subscriptions', sa.Column('quota_limit', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('subscriptions', sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('subscriptions', sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True))
