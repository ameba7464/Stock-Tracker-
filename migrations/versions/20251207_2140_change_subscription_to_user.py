"""change subscription from tenant to user

Revision ID: 20251207_2140
Revises: 20251207_2126
Create Date: 2025-12-07 21:40:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251207_2140'
down_revision = '20251207_2126'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change subscription relationship from tenant to user."""
    
    # Drop existing subscriptions table and recreate with user_id
    op.execute("DROP TABLE IF EXISTS subscriptions CASCADE")
    
    # Create new subscriptions table with user_id
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('has_access', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(), nullable=False, server_default='unpaid'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create indexes
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=True)


def downgrade() -> None:
    """Restore subscription relationship to tenant."""
    
    # Drop new table
    op.drop_table('subscriptions')
    
    # Recreate old table with tenant_id
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('has_access', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(), nullable=False, server_default='unpaid'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id')
    )
    
    op.create_index('ix_subscriptions_tenant_id', 'subscriptions', ['tenant_id'], unique=True)
