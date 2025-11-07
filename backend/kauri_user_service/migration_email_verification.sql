-- Migration: Add email verification fields to users table
-- Date: 2025-11-07
-- Description: Adds email verification token, expiration, and verification timestamp

-- Add email verification columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token_expires TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP;

-- Create index on verification token for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email_verification_token ON users(email_verification_token);

-- For OAuth users, mark their email as already verified
UPDATE users
SET is_verified = TRUE,
    email_verified_at = created_at
WHERE oauth_provider IS NOT NULL
  AND is_verified = FALSE;

-- Add comments
COMMENT ON COLUMN users.email_verification_token IS 'Token sent to user email for verification';
COMMENT ON COLUMN users.email_verification_token_expires IS 'Expiration timestamp for verification token';
COMMENT ON COLUMN users.email_verified_at IS 'Timestamp when email was verified';
