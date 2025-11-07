"""
Test de connexion a PostgreSQL
"""
import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv('../../.env')

database_url = os.getenv('DATABASE_URL')
print(f"DATABASE_URL from env: {database_url}")

try:
    import psycopg2
    print("\n[OK] psycopg2 is installed")

    # Essayer de se connecter
    print(f"\n[TEST] Tentative de connexion a: {database_url}")
    conn = psycopg2.connect(database_url)
    print("[OK] Connexion reussie!")

    # Tester une requete simple
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"[OK] PostgreSQL version: {version[0]}")

    # Lister les tables
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    print(f"\n[INFO] Tables dans la base kauri_users:")
    if tables:
        for table in tables:
            print(f"   - {table[0]}")
    else:
        print("   (aucune table)")

    cur.close()
    conn.close()

except ImportError:
    print("[ERROR] psycopg2 n'est pas installe")
    sys.exit(1)

except Exception as e:
    print(f"[ERROR] Erreur de connexion: {type(e).__name__}")
    print(f"   Message: {e}")
    sys.exit(1)
