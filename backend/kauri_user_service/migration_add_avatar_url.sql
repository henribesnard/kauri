-- Migration: Add avatar_url column to users table
-- Date: 2025-11-07
-- Description: Add avatar_url column for OAuth user profile pictures

-- Add avatar_url column
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);

-- Comment
COMMENT ON COLUMN users.avatar_url IS 'URL of user profile picture from OAuth provider';
