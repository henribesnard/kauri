# ============================================
# KAURI - Makefile
# ============================================
# Commandes simplifiées pour gérer l'infrastructure

.PHONY: help build up down restart logs ps clean test

# Aide par défaut
help:
	@echo "=========================================="
	@echo "  KAURI - Commandes Disponibles"
	@echo "=========================================="
	@echo ""
	@echo "  make build       - Construire les images Docker"
	@echo "  make up          - Démarrer tous les services"
	@echo "  make down        - Arrêter tous les services"
	@echo "  make restart     - Redémarrer tous les services"
	@echo "  make logs        - Voir les logs (temps réel)"
	@echo "  make logs-user   - Logs User Service uniquement"
	@echo "  make logs-chat   - Logs Chatbot Service uniquement"
	@echo "  make ps          - Status des services"
	@echo "  make clean       - Arrêter et supprimer volumes"
	@echo "  make shell-user  - Shell User Service"
	@echo "  make shell-chat  - Shell Chatbot Service"
	@echo "  make health      - Vérifier santé services"
	@echo "  make test        - Lancer les tests"
	@echo ""
	@echo "=========================================="

# Construire les images
build:
	@echo "📦 Construction des images Docker..."
	docker-compose build

# Démarrer les services
up:
	@echo "🚀 Démarrage des services..."
	docker-compose up -d
	@echo ""
	@echo "⏳ Attente du démarrage (30s)..."
	@sleep 30 || timeout /t 30
	@echo ""
	@echo "✅ Services démarrés !"
	@make ps
	@echo ""
	@make health

# Arrêter les services
down:
	@echo "🛑 Arrêt des services..."
	docker-compose down

# Redémarrer les services
restart:
	@echo "🔄 Redémarrage des services..."
	docker-compose restart
	@sleep 10 || timeout /t 10
	@make ps

# Logs de tous les services
logs:
	docker-compose logs -f

# Logs User Service
logs-user:
	docker-compose logs -f kauri_user_service

# Logs Chatbot Service
logs-chat:
	docker-compose logs -f kauri_chatbot_service

# Status des services
ps:
	@echo "📊 Status des services:"
	@docker-compose ps

# Nettoyer tout (supprime volumes)
clean:
	@echo "⚠️  Attention: Cette commande supprime TOUS les volumes (données)"
	@echo "Appuyez sur Ctrl+C pour annuler..."
	@sleep 5 || timeout /t 5
	docker-compose down -v
	@echo "✅ Nettoyage complet effectué"

# Shell User Service
shell-user:
	docker exec -it kauri_user_service bash

# Shell Chatbot Service
shell-chat:
	docker exec -it kauri_chatbot_service bash

# Shell PostgreSQL
shell-db:
	docker exec -it kauri_postgres psql -U kauri_user

# Shell Redis
shell-redis:
	docker exec -it kauri_redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d'=' -f2)

# Vérifier santé des services
health:
	@echo "🏥 Vérification de la santé des services..."
	@echo ""
	@echo "User Service:"
	@curl -s http://localhost:8001/api/v1/health | python -m json.tool || echo "❌ User Service non disponible"
	@echo ""
	@echo "Chatbot Service:"
	@curl -s http://localhost:8002/api/v1/health | python -m json.tool || echo "❌ Chatbot Service non disponible"
	@echo ""

# Lancer les tests
test:
	@echo "🧪 Lancement des tests..."
	@echo "User Service:"
	docker exec -it kauri_user_service pytest tests/ -v || true
	@echo ""
	@echo "Chatbot Service:"
	docker exec -it kauri_chatbot_service pytest tests/ -v || true

# Rebuild complet
rebuild:
	@echo "🔧 Rebuild complet..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@make health

# Voir les URLs des services
urls:
	@echo "=========================================="
	@echo "  Services Disponibles"
	@echo "=========================================="
	@echo ""
	@echo "🔹 PostgreSQL:       localhost:5432"
	@echo "🔹 Redis:             localhost:6379"
	@echo "🔹 ChromaDB:          http://localhost:8000"
	@echo "🔹 User Service:      http://localhost:8001"
	@echo "🔹 Chatbot Service:   http://localhost:8002"
	@echo ""
	@echo "📖 Documentation API:"
	@echo "🔹 User Service:      http://localhost:8001/api/v1/docs"
	@echo "🔹 Chatbot Service:   http://localhost:8002/api/v1/docs"
	@echo ""
	@echo "=========================================="

# Stats ressources
stats:
	@echo "📊 Statistiques ressources Docker:"
	docker stats --no-stream
