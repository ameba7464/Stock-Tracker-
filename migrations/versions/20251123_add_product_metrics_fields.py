"""Add ProductMetrics fields to Product model

Revision ID: 20251123_product_metrics
Revises: c6765dce8c18
Create Date: 2025-11-23 00:00:00.000000

Adds fields from ProductMetrics structure to Product model for new Google Sheets layout:
- Additional identifiers (nm_id, wildberries_article, vendor_code, subject_id)
- Stock breakdowns (stocks_wb, stocks_mp, fbo_stock, fbs_stock)
- Order breakdowns (orders_wb_warehouses, orders_fbs_warehouses)
- Logistics fields (in_transit_to_customer, in_transit_to_wb_warehouse)
- Analytics fields (avg_orders_per_day, conversions, buyout metrics)
- Warehouse data (stocks_by_warehouse, orders_by_warehouse)
- Aliases for compatibility (product_name, brand_name, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251123_product_metrics'
down_revision: Union[str, None] = 'c6765dce8c18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ProductMetrics fields to products table."""
    
    # Additional identifiers
    op.add_column('products', sa.Column('nm_id', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('wildberries_article', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('vendor_code', sa.String(length=255), nullable=True))
    op.add_column('products', sa.Column('subject_id', sa.Integer(), nullable=True))
    
    # Product details aliases
    op.add_column('products', sa.Column('product_name', sa.String(length=500), nullable=True))
    op.add_column('products', sa.Column('brand_name', sa.String(length=255), nullable=True))
    op.add_column('products', sa.Column('subject', sa.String(length=255), nullable=True))
    
    # Stock breakdowns
    op.add_column('products', sa.Column('stocks_total', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('stocks_wb', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('stocks_mp', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('fbo_stock', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('fbs_stock', sa.Integer(), nullable=True, server_default='0'))
    
    # Order breakdowns
    op.add_column('products', sa.Column('orders_wb_warehouses', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('orders_fbs_warehouses', sa.Integer(), nullable=True, server_default='0'))
    
    # Logistics
    op.add_column('products', sa.Column('in_way_to_client', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('in_transit_to_customer', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('in_way_from_client', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('in_transit_to_wb_warehouse', sa.Integer(), nullable=True, server_default='0'))
    
    # Analytics
    op.add_column('products', sa.Column('avg_orders_per_day', sa.Float(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('conversion_to_cart', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('conversion_to_order', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('buyout_percent', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('avg_price', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('order_sum_total', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('buyout_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('products', sa.Column('buyout_sum', sa.Integer(), nullable=True, server_default='0'))
    
    # Warehouse data (JSONB)
    op.add_column('products', sa.Column('stocks_by_warehouse', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    op.add_column('products', sa.Column('orders_by_warehouse', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    
    # Aliases
    op.add_column('products', sa.Column('turnover', sa.Float(), nullable=True))
    op.add_column('products', sa.Column('last_updated', sa.DateTime(), nullable=True))
    
    # Create indexes for new identifier fields
    op.create_index('idx_products_nm_id', 'products', ['nm_id'], unique=False)
    op.create_index('idx_products_wildberries_article', 'products', ['wildberries_article'], unique=False)
    op.create_index('idx_products_vendor_code', 'products', ['vendor_code'], unique=False)
    
    # Copy existing data to alias fields
    op.execute("UPDATE products SET product_name = name WHERE name IS NOT NULL")
    op.execute("UPDATE products SET brand_name = brand WHERE brand IS NOT NULL")
    op.execute("UPDATE products SET stocks_total = total_stock WHERE total_stock IS NOT NULL")
    op.execute("UPDATE products SET turnover = turnover_days WHERE turnover_days IS NOT NULL")
    op.execute("UPDATE products SET last_updated = last_synced_at WHERE last_synced_at IS NOT NULL")
    op.execute("UPDATE products SET in_transit_to_customer = in_way_to_client WHERE in_way_to_client IS NOT NULL")
    op.execute("UPDATE products SET in_transit_to_wb_warehouse = in_way_from_client WHERE in_way_from_client IS NOT NULL")
    op.execute("UPDATE products SET vendor_code = seller_article WHERE seller_article IS NOT NULL")


def downgrade() -> None:
    """Remove ProductMetrics fields from products table."""
    
    # Drop indexes
    op.drop_index('idx_products_vendor_code', table_name='products')
    op.drop_index('idx_products_wildberries_article', table_name='products')
    op.drop_index('idx_products_nm_id', table_name='products')
    
    # Drop columns (in reverse order)
    op.drop_column('products', 'last_updated')
    op.drop_column('products', 'turnover')
    op.drop_column('products', 'orders_by_warehouse')
    op.drop_column('products', 'stocks_by_warehouse')
    op.drop_column('products', 'buyout_sum')
    op.drop_column('products', 'buyout_count')
    op.drop_column('products', 'order_sum_total')
    op.drop_column('products', 'avg_price')
    op.drop_column('products', 'buyout_percent')
    op.drop_column('products', 'conversion_to_order')
    op.drop_column('products', 'conversion_to_cart')
    op.drop_column('products', 'avg_orders_per_day')
    op.drop_column('products', 'in_transit_to_wb_warehouse')
    op.drop_column('products', 'in_way_from_client')
    op.drop_column('products', 'in_transit_to_customer')
    op.drop_column('products', 'in_way_to_client')
    op.drop_column('products', 'orders_fbs_warehouses')
    op.drop_column('products', 'orders_wb_warehouses')
    op.drop_column('products', 'fbs_stock')
    op.drop_column('products', 'fbo_stock')
    op.drop_column('products', 'stocks_mp')
    op.drop_column('products', 'stocks_wb')
    op.drop_column('products', 'stocks_total')
    op.drop_column('products', 'subject')
    op.drop_column('products', 'brand_name')
    op.drop_column('products', 'product_name')
    op.drop_column('products', 'subject_id')
    op.drop_column('products', 'vendor_code')
    op.drop_column('products', 'wildberries_article')
    op.drop_column('products', 'nm_id')
