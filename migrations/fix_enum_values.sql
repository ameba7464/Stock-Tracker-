-- Fix payment_status enum values to uppercase
UPDATE users SET payment_status = 'PAID' WHERE payment_status = 'paid';
UPDATE users SET payment_status = 'FREE' WHERE payment_status = 'free';
UPDATE users SET payment_status = 'TRIAL' WHERE payment_status = 'trial';
UPDATE users SET payment_status = 'EXPIRED' WHERE payment_status = 'expired';

-- Verify changes
SELECT email, payment_status FROM users;
