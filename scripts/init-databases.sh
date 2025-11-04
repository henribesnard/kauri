#!/bin/bash
# ============================================
# KAURI - PostgreSQL Database Initialization
# ============================================
# Ce script crée automatiquement les bases de données
# pour chaque service au démarrage de PostgreSQL

set -e
set -u

function create_database() {
    local database=$1
    echo "Creating database: $database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $database;
        GRANT ALL PRIVILEGES ON DATABASE $database TO $POSTGRES_USER;
EOSQL
}

# Parse POSTGRES_MULTIPLE_DATABASES environment variable
if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
    IFS=',' read -ra DATABASES <<< "$POSTGRES_MULTIPLE_DATABASES"
    for db in "${DATABASES[@]}"; do
        create_database $db
    done
    echo "Multiple databases created successfully"
else
    echo "POSTGRES_MULTIPLE_DATABASES not set, skipping additional database creation"
fi
