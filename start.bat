@echo off
REM ============================================
REM KAURI - Script de Démarrage Windows
REM ============================================

echo ==========================================
echo   KAURI - Démarrage de l'architecture
echo ==========================================

REM Vérifier que le fichier .env existe
if not exist .env (
    echo ❌ Erreur: Fichier .env manquant
    echo 📋 Copiez .env.example vers .env et configurez les variables
    exit /b 1
)

echo 📦 Construction des images Docker...
docker-compose build

echo.
echo 🚀 Démarrage des services...
docker-compose up -d

echo.
echo ⏳ Attente du démarrage des services (30s)...
timeout /t 30 /nobreak

echo.
echo ✅ Services démarrés !
echo.
echo 📊 Status des services:
docker-compose ps

echo.
echo ==========================================
echo   Services disponibles:
echo ==========================================
echo 🔹 PostgreSQL:       localhost:5432
echo 🔹 Redis:             localhost:6379
echo 🔹 ChromaDB:          localhost:8000
echo 🔹 User Service:      http://localhost:8001
echo 🔹 Chatbot Service:   http://localhost:8002
echo.
echo 📖 Documentation:
echo 🔹 User Service:      http://localhost:8001/api/v1/docs
echo 🔹 Chatbot Service:   http://localhost:8002/api/v1/docs
echo.
echo ==========================================
echo Pour voir les logs: docker-compose logs -f
echo Pour arrêter:       docker-compose down
echo ==========================================

pause
