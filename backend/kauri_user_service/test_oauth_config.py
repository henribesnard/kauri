"""
Script de test pour vérifier la configuration OAuth
Execute: python test_oauth_config.py
"""
import sys
import os

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("🔍 Test de la configuration OAuth...\n")

    # Test 1: Import des modules
    print("1️⃣  Test des imports...")
    from src.config import settings
    from src.auth.oauth_manager import oauth, is_provider_configured, get_oauth_client
    from src.models.user import User
    print("   ✅ Tous les imports sont OK\n")

    # Test 2: Configuration
    print("2️⃣  Test de la configuration...")
    print(f"   Frontend URL: {settings.frontend_url}")
    print(f"   OAuth State Secret défini: {'✅' if settings.oauth_state_secret else '❌'}\n")

    # Test 3: Providers configurés
    print("3️⃣  Providers OAuth configurés:")
    providers = ['google', 'facebook', 'linkedin', 'twitter']
    configured_count = 0

    for provider in providers:
        is_configured = is_provider_configured(provider)
        configured_count += 1 if is_configured else 0
        status = "✅ Configuré" if is_configured else "⚠️  Non configuré"
        print(f"   {provider.capitalize()}: {status}")

    print(f"\n   Total configurés: {configured_count}/4\n")

    # Test 4: OAuth clients
    print("4️⃣  Test des clients OAuth...")
    try:
        for provider in providers:
            client = get_oauth_client(provider)
            print(f"   {provider.capitalize()}: ✅ Client OK")
        print()
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")

    # Test 5: Modèle User
    print("5️⃣  Test du modèle User...")
    user_oauth_fields = ['google_id', 'facebook_id', 'linkedin_id', 'twitter_id', 'oauth_provider', 'avatar_url']
    for field in user_oauth_fields:
        has_field = hasattr(User, field)
        status = "✅" if has_field else "❌"
        print(f"   {field}: {status}")
    print()

    # Test 6: Routes
    print("6️⃣  Test des routes OAuth...")
    try:
        from src.api.routes import oauth as oauth_routes
        print(f"   Router OAuth: ✅ Importé")
        print(f"   Prefix: {oauth_routes.router.prefix}")
        print(f"   Tags: {oauth_routes.router.tags}\n")
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")

    # Résumé
    print("=" * 50)
    if configured_count > 0:
        print("✅ Configuration OAuth prête !")
        print(f"   {configured_count} provider(s) configuré(s)")
        print("\n💡 Pour tester:")
        print("   1. Démarrez le backend: python -m src.api.main")
        print("   2. Visitez: http://localhost:8001/api/v1/oauth/providers")
        print("   3. Testez un login: http://localhost:8001/api/v1/oauth/login/google")
    else:
        print("⚠️  Aucun provider OAuth configuré")
        print("\n💡 Pour configurer:")
        print("   1. Copiez .env.oauth.example vers votre .env")
        print("   2. Remplissez les credentials des providers")
        print("   3. Consultez OAUTH_SETUP.md pour les instructions détaillées")
    print("=" * 50)

except Exception as e:
    print(f"\n❌ Erreur lors du test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
