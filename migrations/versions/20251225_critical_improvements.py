"""
Migration: Add critical security and performance improvements

Revision ID: 20251225_critical_improvements
Created: 2025-12-25
Description:
    - Add CHECK constraints for data validation
    - Add encryption column for API keys
    - Add GIN indexes for JSONB columns
    - Add triggers for automatic updated_at
    - Add audit_logs table for security tracking
    - Add missing indexes for performance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '20251225_critical_improvements'
down_revision = '20251207_2140_change_subscription_to_user'  # Update to your latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Apply critical improvements to database schema."""
    
    # ============================================================
    # 1. ADD CHECK CONSTRAINTS FOR DATA VALIDATION
    # ============================================================
    
    # Products table constraints
    op.execute("""
        ALTER TABLE products 
        ADD CONSTRAINT check_products_stock_positive 
        CHECK (total_stock >= 0);
    """)
    
    op.execute("""
        ALTER TABLE products 
        ADD CONSTRAINT check_products_orders_positive 
        CHECK (total_orders >= 0);
    """)
    
    op.execute("""
        ALTER TABLE products 
        ADD CONSTRAINT check_products_revenue_positive 
        CHECK (revenue >= 0);
    """)
    
    # Users table constraints
    op.execute("""
        ALTER TABLE users 
        ADD CONSTRAINT check_users_email_format 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');
    """)
    
    print("✓ Added CHECK constraints for data validation")
    
    # ============================================================
    # 2. ADD ENCRYPTION COLUMN FOR API KEYS
    # ============================================================
    
    # Add encrypted API key column to users
    op.add_column('users', 
        sa.Column('wb_api_key_encrypted', sa.Text(), nullable=True)
    )
    
    print("✓ Added wb_api_key_encrypted column to users")
    
    # ============================================================
    # 3. ADD GIN INDEXES FOR JSONB COLUMNS
    # ============================================================
    
    # GIN index for products.warehouse_data (fast JSONB queries)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_warehouse_data_gin 
        ON products USING GIN (warehouse_data);
    """)
    
    # GIN index for products.raw_data
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_raw_data_gin 
        ON products USING GIN (raw_data);
    """)
    
    print("✓ Added GIN indexes for JSONB columns")
    
    # ============================================================
    # 4. ADD MISSING PERFORMANCE INDEXES
    # ============================================================
    
    # Partial index for active products only
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_tenant_active 
        ON products(tenant_id, is_active) 
        WHERE is_active = true;
    """)
    
    # Index for Google Sheets integration lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_google_sheet_id 
        ON users(google_sheet_id) 
        WHERE google_sheet_id IS NOT NULL;
    """)
    
    # Index for payment status filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_payment_status 
        ON users(payment_status);
    """)
    
    print("✓ Added performance indexes")
    
    # ============================================================
    # 5. CREATE TRIGGER FUNCTION FOR updated_at
    # ============================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Apply trigger to users table
    op.execute("""
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Apply trigger to tenants table
    op.execute("""
        DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;
        CREATE TRIGGER update_tenants_updated_at
            BEFORE UPDATE ON tenants
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Apply trigger to products table (if has updated_at)
    op.execute("""
        DROP TRIGGER IF EXISTS update_products_updated_at ON products;
        CREATE TRIGGER update_products_updated_at
            BEFORE UPDATE ON products
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    print("✓ Created triggers for automatic updated_at")
    
    # ============================================================
    # 6. CREATE AUDIT LOGS TABLE
    # ============================================================
    
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('operation', sa.String(10), nullable=False),  # INSERT/UPDATE/DELETE
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('old_data', postgresql.JSONB, nullable=True),
        sa.Column('new_data', postgresql.JSONB, nullable=True),
        sa.Column('changed_fields', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for audit logs
    op.create_index('idx_audit_logs_table_name', 'audit_logs', ['table_name'])
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_logs_operation', 'audit_logs', ['operation'])
    
    # Create audit trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_trigger_func()
        RETURNS TRIGGER AS $$
        DECLARE
            user_id_val UUID;
            tenant_id_val UUID;
        BEGIN
            -- Try to get user_id and tenant_id from session or record
            user_id_val := current_setting('app.current_user_id', true)::UUID;
            tenant_id_val := current_setting('app.current_tenant_id', true)::UUID;
            
            IF TG_OP = 'DELETE' THEN
                INSERT INTO audit_logs (table_name, operation, user_id, tenant_id, old_data)
                VALUES (TG_TABLE_NAME, TG_OP, user_id_val, tenant_id_val, row_to_json(OLD)::JSONB);
                RETURN OLD;
            ELSIF TG_OP = 'UPDATE' THEN
                INSERT INTO audit_logs (table_name, operation, user_id, tenant_id, old_data, new_data)
                VALUES (TG_TABLE_NAME, TG_OP, user_id_val, tenant_id_val, row_to_json(OLD)::JSONB, row_to_json(NEW)::JSONB);
                RETURN NEW;
            ELSIF TG_OP = 'INSERT' THEN
                INSERT INTO audit_logs (table_name, operation, user_id, tenant_id, new_data)
                VALUES (TG_TABLE_NAME, TG_OP, user_id_val, tenant_id_val, row_to_json(NEW)::JSONB);
                RETURN NEW;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                -- If audit logging fails, don't block the main operation
                RAISE WARNING 'Audit logging failed: %', SQLERRM;
                RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Apply audit trigger to critical tables (optional, can enable per table)
    # Uncomment to enable audit logging for users table:
    # op.execute("""
    #     CREATE TRIGGER audit_users AFTER INSERT OR UPDATE OR DELETE ON users
    #         FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
    # """)
    
    print("✓ Created audit_logs table and trigger function")
    
    # ============================================================
    # 7. ADD SOFT DELETE COLUMNS (OPTIONAL)
    # ============================================================
    
    # Add soft delete to tenants
    op.add_column('tenants',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('tenants',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Index for filtering non-deleted tenants
    op.create_index('idx_tenants_is_deleted', 'tenants', ['is_deleted'])
    
    print("✓ Added soft delete columns to tenants")
    
    print("\n" + "="*60)
    print("CRITICAL IMPROVEMENTS APPLIED SUCCESSFULLY")
    print("="*60)
    print("\nNext steps:")
    print("1. Generate ENCRYPTION_KEY:")
    print("   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
    print("\n2. Add to .env:")
    print("   ENCRYPTION_KEY=<generated_key>")
    print("\n3. Encrypt existing API keys:")
    print("   python -m stock_tracker.scripts.migrate_api_keys")
    print("\n4. Enable audit logging for tables as needed")
    print("="*60)


def downgrade():
    """Rollback critical improvements."""
    
    # Drop soft delete columns
    op.drop_index('idx_tenants_is_deleted', 'tenants')
    op.drop_column('tenants', 'deleted_at')
    op.drop_column('tenants', 'is_deleted')
    
    # Drop audit triggers and table
    op.execute("DROP TRIGGER IF EXISTS audit_users ON users;")
    op.execute("DROP FUNCTION IF EXISTS audit_trigger_func();")
    op.drop_index('idx_audit_logs_operation', 'audit_logs')
    op.drop_index('idx_audit_logs_created_at', 'audit_logs')
    op.drop_index('idx_audit_logs_tenant_id', 'audit_logs')
    op.drop_index('idx_audit_logs_user_id', 'audit_logs')
    op.drop_index('idx_audit_logs_table_name', 'audit_logs')
    op.drop_table('audit_logs')
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_products_updated_at ON products;")
    op.execute("DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;")
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop performance indexes
    op.execute("DROP INDEX IF EXISTS idx_users_payment_status;")
    op.execute("DROP INDEX IF EXISTS idx_users_google_sheet_id;")
    op.execute("DROP INDEX IF EXISTS idx_products_tenant_active;")
    
    # Drop GIN indexes
    op.execute("DROP INDEX IF EXISTS idx_products_raw_data_gin;")
    op.execute("DROP INDEX IF EXISTS idx_products_warehouse_data_gin;")
    
    # Drop encryption column
    op.drop_column('users', 'wb_api_key_encrypted')
    
    # Drop CHECK constraints
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_users_email_format;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_products_revenue_positive;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_products_orders_positive;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS check_products_stock_positive;")
    
    print("✓ Rolled back critical improvements")
