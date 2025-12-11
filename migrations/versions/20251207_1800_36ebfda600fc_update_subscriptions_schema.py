"""update_subscriptions_schema

Revision ID: 36ebfda600fc
Revises: 01c2760144a1
Create Date: 2025-12-07 18:00:59.308115+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '36ebfda600fc'
down_revision = '01c2760144a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename plan_name to plan_type
    op.alter_column('subscriptions', 'plan_name', new_column_name='plan_type')
    
    # Change user_id to tenant_id
    op.alter_column('subscriptions', 'user_id', new_column_name='tenant_id')
    
    # Update foreign key reference from users to tenants
    op.drop_constraint('subscriptions_user_id_fkey', 'subscriptions', type_='foreignkey')
    op.create_foreign_key('subscriptions_tenant_id_fkey', 'subscriptions', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    
    # Add new columns
    op.add_column('subscriptions', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('stripe_subscription_id', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('quota_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('subscriptions', sa.Column('quota_limit', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('subscriptions', sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('subscriptions', sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'], unique=False)
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'], unique=False)
    
    # Drop old columns that are no longer needed
    op.drop_column('subscriptions', 'price')
    op.drop_column('subscriptions', 'currency')
    op.drop_column('subscriptions', 'started_at')
    op.drop_column('subscriptions', 'cancelled_at')
    op.drop_column('subscriptions', 'auto_renew')
    
    # Update indexes
    op.drop_index('ix_subscriptions_user_id', table_name='subscriptions')
    op.create_index('ix_subscriptions_tenant_id', 'subscriptions', ['tenant_id'], unique=True)


def downgrade() -> None:
    # Restore old indexes
    op.drop_index('ix_subscriptions_tenant_id', table_name='subscriptions')
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=False)
    
    # Restore old columns
    op.add_column('subscriptions', sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('subscriptions', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('subscriptions', sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')))
    op.add_column('subscriptions', sa.Column('currency', sa.String(3), nullable=True, server_default='RUB'))
    op.add_column('subscriptions', sa.Column('price', sa.Numeric(10, 2), nullable=True))
    
    # Drop new indexes
    op.drop_index('ix_subscriptions_stripe_subscription_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_stripe_customer_id', table_name='subscriptions')
    
    # Drop new columns
    op.drop_column('subscriptions', 'current_period_end')
    op.drop_column('subscriptions', 'current_period_start')
    op.drop_column('subscriptions', 'quota_limit')
    op.drop_column('subscriptions', 'quota_used')
    op.drop_column('subscriptions', 'stripe_subscription_id')
    op.drop_column('subscriptions', 'stripe_customer_id')
    
    # Restore foreign key reference
    op.drop_constraint('subscriptions_tenant_id_fkey', 'subscriptions', type_='foreignkey')
    op.create_foreign_key('subscriptions_user_id_fkey', 'subscriptions', 'users', ['tenant_id'], ['id'], ondelete='CASCADE')
    
    # Restore column names
    op.alter_column('subscriptions', 'tenant_id', new_column_name='user_id')
    op.alter_column('subscriptions', 'plan_type', new_column_name='plan_name')

