-- First, alter the enum type to add uppercase values
ALTER TYPE payment_status_enum ADD VALUE IF NOT EXISTS 'FREE';
ALTER TYPE payment_status_enum ADD VALUE IF NOT EXISTS 'TRIAL';
ALTER TYPE payment_status_enum ADD VALUE IF NOT EXISTS 'PAID';
ALTER TYPE payment_status_enum ADD VALUE IF NOT EXISTS 'EXPIRED';

-- Update existing data to use uppercase
UPDATE users SET payment_status = 'PAID' WHERE payment_status = 'paid';
UPDATE users SET payment_status = 'FREE' WHERE payment_status = 'free';
UPDATE users SET payment_status = 'TRIAL' WHERE payment_status = 'trial';
UPDATE users SET payment_status = 'EXPIRED' WHERE payment_status = 'expired';

-- Verify
SELECT email, payment_status FROM users;
