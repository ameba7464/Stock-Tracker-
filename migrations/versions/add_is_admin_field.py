"""Add is_admin field to users table

Revision ID: add_is_admin_field
Revises: 20251123_product_metrics
Create Date: 2025-12-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_is_admin_field'
down_revision = '20251123_product_metrics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_admin column to users table."""
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Create index for faster admin queries
    op.create_index(
        'ix_users_is_admin',
        'users',
        ['is_admin'],
        unique=False
    )


def downgrade() -> None:
    """Remove is_admin column from users table."""
    op.drop_index('ix_users_is_admin', table_name='users')
    op.drop_column('users', 'is_admin')
