-- Migrate data from old users table
INSERT INTO tenants (id, name, slug, is_active)
VALUES ('00000000-0000-0000-0000-000000000001'::UUID, 'Default Tenant', 'default', true)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO users (
    email, telegram_id, full_name, phone, wb_api_key, 
    google_sheet_id, google_sheet_sent, tenant_id, role,
    is_active, is_admin, payment_status, created_at, updated_at
)
SELECT 
    COALESCE(email, 'user_' || telegram_id || '@telegram.bot'),
    telegram_id,
    name,
    phone,
    wb_api_key,
    google_sheet_id,
    google_sheet_sent,
    '00000000-0000-0000-0000-000000000001'::UUID,
    'USER'::user_role,
    true,
    COALESCE(is_admin, false),
    CASE 
        WHEN payment_status = 'completed' THEN 'paid'::payment_status_enum
        WHEN payment_status IS NULL THEN 'free'::payment_status_enum
        ELSE COALESCE(payment_status::text, 'free')::payment_status_enum
    END,
    created_at,
    updated_at
FROM users_old_backup
ON CONFLICT (telegram_id) DO UPDATE SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    is_admin = EXCLUDED.is_admin,
    wb_api_key = EXCLUDED.wb_api_key,
    google_sheet_id = EXCLUDED.google_sheet_id;

SELECT id, email, telegram_id, full_name, role, is_admin, payment_status 
FROM users 
ORDER BY created_at;
