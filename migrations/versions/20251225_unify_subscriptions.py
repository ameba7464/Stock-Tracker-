"""
Migration: Unify subscription system
Created: 2025-12-25

Purpose:
- Create subscription records for all existing telegram users
- Prepare for unified subscription system (telegram bot + admin panel)
- Enable easy transition from free to paid model via feature flag
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers
revision = '20251225_unify_subscriptions'
down_revision = '20251207_2140_change_subscription_to_user'


def upgrade():
    """
    Создание записей subscriptions для всех telegram пользователей.
    
    Логика:
    1. Все существующие пользователи с telegram_id получают бесплатный доступ
    2. status = 'FREE', has_access = TRUE
    3. Это защищает legacy users при переходе на платную модель
    """
    
    # Step 1: Создать enum для subscription status если его еще нет
    subscription_status_enum = postgresql.ENUM(
        'FREE', 'TRIAL', 'PAID', 'EXPIRED',
        name='subscription_status',
        create_type=False
    )
    
    # Проверяем существует ли enum
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type 
            WHERE typname = 'subscription_status'
        );
    """))
    enum_exists = result.scalar()
    
    if not enum_exists:
        # Создаем enum если его нет
        subscription_status_enum.create(conn, checkfirst=True)
        print("✓ Created subscription_status enum")
    
    
    # Step 2: Расширить таблицу subscriptions новыми полями
    print("Adding new columns to subscriptions table...")
    
    # Добавляем колонки для дат
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        # Проверяем какие колонки уже существуют
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_columns = [col['name'] for col in inspector.get_columns('subscriptions')]
        
        # Добавляем только те колонки, которых нет
        if 'trial_ends_at' not in existing_columns:
            batch_op.add_column(
                sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True)
            )
            print("  ✓ Added trial_ends_at")
        
        if 'subscription_starts_at' not in existing_columns:
            batch_op.add_column(
                sa.Column('subscription_starts_at', sa.DateTime(timezone=True), nullable=True)
            )
            print("  ✓ Added subscription_starts_at")
        
        if 'subscription_ends_at' not in existing_columns:
            batch_op.add_column(
                sa.Column('subscription_ends_at', sa.DateTime(timezone=True), nullable=True)
            )
            print("  ✓ Added subscription_ends_at")
        
        # Метаданные для платежей
        if 'payment_provider' not in existing_columns:
            batch_op.add_column(
                sa.Column('payment_provider', sa.String(50), nullable=True)
            )
            print("  ✓ Added payment_provider")
        
        if 'payment_external_id' not in existing_columns:
            batch_op.add_column(
                sa.Column('payment_external_id', sa.String(255), nullable=True)
            )
            print("  ✓ Added payment_external_id")
        
        if 'last_payment_at' not in existing_columns:
            batch_op.add_column(
                sa.Column('last_payment_at', sa.DateTime(timezone=True), nullable=True)
            )
            print("  ✓ Added last_payment_at")
    
    
    # Step 3: Изменить тип колонки status на enum
    print("Converting status column to enum...")
    
    # Сначала создаем временную колонку с enum типом
    op.execute("""
        ALTER TABLE subscriptions 
        ADD COLUMN IF NOT EXISTS status_new subscription_status;
    """)
    
    # Копируем данные, приводя к верхнему регистру
    op.execute("""
        UPDATE subscriptions
        SET status_new = CASE 
            WHEN UPPER(status) = 'PAID' THEN 'PAID'::subscription_status
            WHEN UPPER(status) = 'UNPAID' THEN 'FREE'::subscription_status
            WHEN UPPER(status) = 'FREE' THEN 'FREE'::subscription_status
            WHEN UPPER(status) = 'TRIAL' THEN 'TRIAL'::subscription_status
            WHEN UPPER(status) = 'EXPIRED' THEN 'EXPIRED'::subscription_status
            ELSE 'FREE'::subscription_status
        END
        WHERE status_new IS NULL;
    """)
    
    # Удаляем старую колонку и переименовываем новую
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS status;")
    op.execute("ALTER TABLE subscriptions RENAME COLUMN status_new TO status;")
    
    # Устанавливаем NOT NULL и default
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN status SET NOT NULL,
        ALTER COLUMN status SET DEFAULT 'FREE'::subscription_status;
    """)
    
    print("  ✓ Status column converted to enum")
    
    
    # Step 4: Создать subscriptions для всех telegram пользователей
    print("Creating subscription records for telegram users...")
    
    op.execute(sa.text("""
        INSERT INTO subscriptions (
            id,
            user_id,
            status,
            has_access,
            subscription_starts_at,
            created_at,
            updated_at
        )
        SELECT 
            gen_random_uuid(),
            u.id,
            'FREE'::subscription_status,
            TRUE,
            NOW(),
            NOW(),
            NOW()
        FROM users u
        WHERE u.telegram_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM subscriptions s 
              WHERE s.user_id = u.id
          );
    """))
    
    print(f"  ✓ Created subscription records for telegram users")
    
    
    # Step 5: Добавить индексы для производительности
    print("Creating indexes...")
    
    # Индекс по статусу
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_status 
        ON subscriptions(status);
    """)
    
    # Частичный индекс для активных подписок
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_active_access 
        ON subscriptions(has_access) 
        WHERE has_access = TRUE;
    """)
    
    # Индекс для поиска истекающих подписок
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_expiring 
        ON subscriptions(subscription_ends_at) 
        WHERE subscription_ends_at IS NOT NULL AND has_access = TRUE;
    """)
    
    print("  ✓ Created indexes")
    
    
    # Step 6: Добавить CHECK constraint для валидации
    print("Adding constraints...")
    
    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT check_status_access_consistency
        CHECK (
            (status = 'FREE' AND has_access = TRUE) OR
            (status = 'TRIAL' AND has_access = TRUE) OR
            (status = 'PAID' AND has_access = TRUE) OR
            (status = 'EXPIRED' AND has_access = FALSE) OR
            (has_access = FALSE)
        );
    """)
    
    print("  ✓ Added status-access consistency check")
    
    
    # Step 7: Добавить комментарии для документации
    print("Adding table comments...")
    
    op.execute("""
        COMMENT ON TABLE subscriptions IS 
        'Unified subscription system for telegram bot and admin panel. 
        Controls user access to the service.';
    """)
    
    op.execute("""
        COMMENT ON COLUMN subscriptions.status IS 
        'Subscription status: FREE (legacy/grandfathered), TRIAL (7 days), 
        PAID (active subscription), EXPIRED (payment required)';
    """)
    
    op.execute("""
        COMMENT ON COLUMN subscriptions.has_access IS 
        'Current access status. TRUE = user can use service. 
        Single source of truth for access control.';
    """)
    
    print("  ✓ Added documentation comments")
    
    print("\n" + "="*60)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"\nSummary:")
    print(f"  • Created subscription records for telegram users")
    print(f"  • All telegram users have FREE status with access")
    print(f"  • Added 6 new columns for payment metadata")
    print(f"  • Created 3 indexes for performance")
    print(f"  • Added validation constraints")
    print(f"\nNext steps:")
    print(f"  1. Update telegram bot to use check_user_access() function")
    print(f"  2. Test with payment_enabled=False (free mode)")
    print(f"  3. When ready: set payment_enabled=True to enable payments")
    print("="*60 + "\n")


def downgrade():
    """
    Откат миграции.
    
    ВНИМАНИЕ: Это удалит новые колонки и может потерять данные!
    """
    print("Rolling back subscription unification...")
    
    # Удаляем constraints
    op.execute("""
        ALTER TABLE subscriptions
        DROP CONSTRAINT IF EXISTS check_status_access_consistency;
    """)
    
    # Удаляем индексы
    op.execute("DROP INDEX IF EXISTS idx_subscriptions_status;")
    op.execute("DROP INDEX IF EXISTS idx_subscriptions_active_access;")
    op.execute("DROP INDEX IF EXISTS idx_subscriptions_expiring;")
    
    # Конвертируем status обратно в VARCHAR
    op.execute("""
        ALTER TABLE subscriptions 
        ADD COLUMN IF NOT EXISTS status_temp VARCHAR(20);
    """)
    
    op.execute("""
        UPDATE subscriptions
        SET status_temp = status::text;
    """)
    
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS status;")
    op.execute("ALTER TABLE subscriptions RENAME COLUMN status_temp TO status;")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN status SET DEFAULT 'unpaid';
    """)
    
    # Удаляем новые колонки
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('last_payment_at')
        batch_op.drop_column('payment_external_id')
        batch_op.drop_column('payment_provider')
        batch_op.drop_column('subscription_ends_at')
        batch_op.drop_column('subscription_starts_at')
        batch_op.drop_column('trial_ends_at')
    
    print("✓ Rollback completed")
    print("⚠️  WARNING: Payment metadata was deleted")
