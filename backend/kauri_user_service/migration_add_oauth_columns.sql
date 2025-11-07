-- Migration: Add all OAuth columns to users table
-- Date: 2025-11-07
-- Description: Add all missing OAuth provider columns (facebook_id, linkedin_id, twitter_id, oauth_provider)

-- Add OAuth provider ID columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS twitter_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50);

-- Add unique constraints
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_facebook_id ON users(facebook_id) WHERE facebook_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_linkedin_id ON users(linkedin_id) WHERE linkedin_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_twitter_id ON users(twitter_id) WHERE twitter_id IS NOT NULL;

-- Comments
COMMENT ON COLUMN users.facebook_id IS 'Facebook OAuth user ID';
COMMENT ON COLUMN users.linkedin_id IS 'LinkedIn OAuth user ID';
COMMENT ON COLUMN users.twitter_id IS 'Twitter OAuth user ID';
COMMENT ON COLUMN users.oauth_provider IS 'OAuth provider name (google, facebook, linkedin, twitter)';
