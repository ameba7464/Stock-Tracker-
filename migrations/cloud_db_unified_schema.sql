-- =====================================================
-- Unified Database Schema for Stock Tracker
-- Combines Telegram Bot + FastAPI Admin Panel
-- =====================================================

-- ==================== EXTENSIONS ====================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==================== ENUMS ====================
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('OWNER', 'ADMIN', 'USER', 'VIEWER');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE subscription_status AS ENUM ('trial', 'active', 'expired', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE payment_status_enum AS ENUM ('free', 'trial', 'paid', 'expired');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ==================== TENANTS ====================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS ix_tenants_is_active ON tenants(is_active);

-- ==================== USERS (UNIFIED) ====================
-- Backup old users table
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        ALTER TABLE users RENAME TO users_old_backup;
    END IF;
END $$;

-- Create new unified users table
CREATE TABLE IF NOT EXISTS users (
    -- Core identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- NULL for telegram-only users
    
    -- Telegram integration
    telegram_id BIGINT UNIQUE,
    telegram_username VARCHAR(100),
    
    -- Personal info
    full_name VARCHAR(255),
    phone VARCHAR(20),
    
    -- Wildberries integration
    wb_api_key TEXT,
    wb_api_key_encrypted TEXT, -- Encrypted version
    
    -- Google Sheets integration
    google_sheet_id VARCHAR(255),
    google_sheet_sent BOOLEAN NOT NULL DEFAULT false,
    
    -- Multi-tenancy
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    role user_role NOT NULL DEFAULT 'USER',
    
    -- Access control
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    
    -- Payment & subscription
    payment_status payment_status_enum NOT NULL DEFAULT 'free',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    
    -- Activity tracking
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_telegram_id ON users(telegram_id) WHERE telegram_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS ix_users_tenant_role ON users(tenant_id, role);
CREATE INDEX IF NOT EXISTS ix_users_is_admin ON users(is_admin) WHERE is_admin = true;
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS ix_users_payment_status ON users(payment_status);

-- ==================== SUBSCRIPTIONS ====================
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(50) NOT NULL,
    status subscription_status NOT NULL DEFAULT 'trial',
    price DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'RUB',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    auto_renew BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS ix_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS ix_subscriptions_expires_at ON subscriptions(expires_at);

-- ==================== REFRESH TOKENS ====================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ==================== PRODUCTS ====================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    wb_article VARCHAR(100) NOT NULL,
    wb_nm_id BIGINT,
    name VARCHAR(500),
    brand VARCHAR(255),
    category VARCHAR(255),
    price DECIMAL(10, 2),
    discount INTEGER,
    rating DECIMAL(3, 2),
    reviews_count INTEGER,
    in_stock BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS ix_products_wb_article ON products(wb_article);
CREATE INDEX IF NOT EXISTS ix_products_wb_nm_id ON products(wb_nm_id);

-- ==================== STOCK HISTORY ====================
CREATE TABLE IF NOT EXISTS stock_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_name VARCHAR(255),
    quantity INTEGER NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_stock_history_product_id ON stock_history(product_id);
CREATE INDEX IF NOT EXISTS ix_stock_history_recorded_at ON stock_history(recorded_at);

-- ==================== SALES ====================
CREATE TABLE IF NOT EXISTS sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    wb_order_id VARCHAR(100),
    sale_date DATE NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    commission DECIMAL(10, 2),
    net_amount DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sales_user_id ON sales(user_id);
CREATE INDEX IF NOT EXISTS ix_sales_product_id ON sales(product_id);
CREATE INDEX IF NOT EXISTS ix_sales_sale_date ON sales(sale_date);

-- ==================== ANALYTICS CACHE ====================
CREATE TABLE IF NOT EXISTS analytics_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,
    period VARCHAR(20) NOT NULL, -- daily, weekly, monthly
    data JSONB NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analytics_cache_user_id ON analytics_cache(user_id);
CREATE INDEX IF NOT EXISTS ix_analytics_cache_metric_type ON analytics_cache(metric_type);
CREATE INDEX IF NOT EXISTS ix_analytics_cache_expires_at ON analytics_cache(expires_at);

-- ==================== AUDIT LOG ====================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    admin_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_admin_user_id ON audit_log(admin_user_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log(created_at);

-- ==================== SYSTEM MONITORING ====================
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15, 2) NOT NULL,
    tags JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_system_metrics_metric_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS ix_system_metrics_recorded_at ON system_metrics(recorded_at);

-- ==================== NOTIFICATIONS ====================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT false,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at);

-- ==================== DATA MIGRATION ====================
-- Migrate data from old users table
DO $$
DECLARE
    default_tenant_id UUID;
BEGIN
    -- Create default tenant if not exists
    INSERT INTO tenants (id, name, slug, is_active)
    VALUES ('00000000-0000-0000-0000-000000000001'::UUID, 'Default Tenant', 'default', true)
    ON CONFLICT (id) DO NOTHING;
    
    default_tenant_id := '00000000-0000-0000-0000-000000000001'::UUID;
    
    -- Migrate data if old table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users_old_backup') THEN
        INSERT INTO users (
            email,
            telegram_id,
            full_name,
            phone,
            wb_api_key,
            google_sheet_id,
            google_sheet_sent,
            tenant_id,
            role,
            is_active,
            is_admin,
            payment_status,
            created_at,
            updated_at
        )
        SELECT 
            COALESCE(email, 'user_' || telegram_id || '@telegram.bot'),
            telegram_id,
            name,
            phone,
            wb_api_key,
            google_sheet_id,
            google_sheet_sent,
            default_tenant_id,
            'USER'::user_role,
            true,
            COALESCE(is_admin, false),
            COALESCE(payment_status::text, 'free')::payment_status_enum,
            created_at,
            updated_at
        FROM users_old_backup
        ON CONFLICT (telegram_id) DO NOTHING
        ON CONFLICT (email) DO NOTHING;
        
        RAISE NOTICE 'Data migration completed successfully';
    END IF;
END $$;

-- ==================== TRIGGERS ====================
-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;
    CREATE TRIGGER update_tenants_updated_at
        BEFORE UPDATE ON tenants
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON subscriptions;
    CREATE TRIGGER update_subscriptions_updated_at
        BEFORE UPDATE ON subscriptions
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    DROP TRIGGER IF EXISTS update_products_updated_at ON products;
    CREATE TRIGGER update_products_updated_at
        BEFORE UPDATE ON products
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
END $$;

-- ==================== VIEWS ====================
-- Active users with subscriptions
CREATE OR REPLACE VIEW v_active_users AS
SELECT 
    u.id,
    u.email,
    u.telegram_id,
    u.full_name,
    u.role,
    u.is_admin,
    u.payment_status,
    u.last_login_at,
    t.name as tenant_name,
    s.plan_name,
    s.expires_at as subscription_expires_at
FROM users u
LEFT JOIN tenants t ON u.tenant_id = t.id
LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active'
WHERE u.is_active = true;

-- Admin dashboard statistics
CREATE OR REPLACE VIEW v_admin_stats AS
SELECT
    (SELECT COUNT(*) FROM users WHERE is_active = true) as total_users,
    (SELECT COUNT(*) FROM users WHERE payment_status = 'paid') as paid_users,
    (SELECT COUNT(*) FROM users WHERE payment_status = 'trial') as trial_users,
    (SELECT COUNT(*) FROM users WHERE is_admin = true) as admin_users,
    (SELECT COUNT(*) FROM products) as total_products,
    (SELECT COUNT(*) FROM sales WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days') as sales_last_30_days;

-- ==================== GRANTS ====================
-- Grant permissions to stocktracker user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stocktracker;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stocktracker;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO stocktracker;

-- ==================== COMPLETION ====================
SELECT 'Database migration completed successfully!' as status;
