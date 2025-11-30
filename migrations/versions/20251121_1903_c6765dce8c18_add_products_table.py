"""Add products table

Revision ID: c6765dce8c18
Revises: 
Create Date: 2025-11-21 19:03:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c6765dce8c18'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('marketplace_article', sa.String(length=100), nullable=False),
        sa.Column('seller_article', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=True),
        sa.Column('brand', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('size', sa.String(length=100), nullable=True),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        sa.Column('total_stock', sa.Integer(), nullable=True, default=0),
        sa.Column('available_stock', sa.Integer(), nullable=True, default=0),
        sa.Column('reserved_stock', sa.Integer(), nullable=True, default=0),
        sa.Column('total_orders', sa.Integer(), nullable=True, default=0),
        sa.Column('cancelled_orders', sa.Integer(), nullable=True, default=0),
        sa.Column('revenue', sa.Float(), nullable=True, default=0.0),
        sa.Column('warehouse_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('turnover_days', sa.Float(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_tenant_marketplace_article', 'products', ['tenant_id', 'marketplace_article'], unique=True)
    op.create_index('idx_tenant_seller_article', 'products', ['tenant_id', 'seller_article'], unique=False)
    op.create_index('idx_tenant_last_synced', 'products', ['tenant_id', 'last_synced_at'], unique=False)
    op.create_index('idx_tenant_active', 'products', ['tenant_id', 'is_active'], unique=False)
    op.create_index('ix_products_marketplace_article', 'products', ['marketplace_article'], unique=False)
    op.create_index('ix_products_tenant_id', 'products', ['tenant_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_products_tenant_id', table_name='products')
    op.drop_index('ix_products_marketplace_article', table_name='products')
    op.drop_index('idx_tenant_active', table_name='products')
    op.drop_index('idx_tenant_last_synced', table_name='products')
    op.drop_index('idx_tenant_seller_article', table_name='products')
    op.drop_index('idx_tenant_marketplace_article', table_name='products')
    
    # Drop table
    op.drop_table('products')
