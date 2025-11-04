#!/bin/bash
# ============================================
# KAURI - Script de Démarrage
# ============================================
# Lance tous les services Docker

set -e

echo "=========================================="
echo "  KAURI - Démarrage de l'architecture"
echo "=========================================="

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Erreur: Docker n'est pas installé"
    exit 1
fi

# Vérifier que docker-compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Erreur: docker-compose n'est pas installé"
    exit 1
fi

# Vérifier que le fichier .env existe
if [ ! -f .env ]; then
    echo "❌ Erreur: Fichier .env manquant"
    echo "📋 Copiez .env.example vers .env et configurez les variables"
    exit 1
fi

echo "📦 Construction des images Docker..."
docker-compose build

echo ""
echo "🚀 Démarrage des services..."
docker-compose up -d

echo ""
echo "⏳ Attente du démarrage des services (30s)..."
sleep 30

echo ""
echo "✅ Services démarrés !"
echo ""
echo "📊 Status des services:"
docker-compose ps

echo ""
echo "=========================================="
echo "  Services disponibles:"
echo "=========================================="
echo "🔹 PostgreSQL:       localhost:5432"
echo "🔹 Redis:             localhost:6379"
echo "🔹 ChromaDB:          localhost:8000"
echo "🔹 User Service:      http://localhost:8001"
echo "🔹 Chatbot Service:   http://localhost:8002"
echo ""
echo "📖 Documentation:"
echo "🔹 User Service:      http://localhost:8001/api/v1/docs"
echo "🔹 Chatbot Service:   http://localhost:8002/api/v1/docs"
echo ""
echo "=========================================="
echo "Pour voir les logs: docker-compose logs -f"
echo "Pour arrêter:       docker-compose down"
echo "=========================================="
