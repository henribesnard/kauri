-- Migration SQL pour ajouter les champs OAuth à la table users
-- À exécuter manuellement ou via Alembic

-- Ajouter les champs OAuth
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS twitter_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50);

-- Créer les index pour les nouveaux champs
CREATE INDEX IF NOT EXISTS idx_users_facebook_id ON users(facebook_id);
CREATE INDEX IF NOT EXISTS idx_users_linkedin_id ON users(linkedin_id);
CREATE INDEX IF NOT EXISTS idx_users_twitter_id ON users(twitter_id);

-- Note: google_id devrait déjà exister dans votre schéma
-- Si ce n'est pas le cas, décommentez la ligne suivante:
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;
-- CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
