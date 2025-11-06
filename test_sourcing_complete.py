"""
Test complet de la fonctionnalite document sourcing
Test en mode stream et non-stream avec differents types de questions
"""
import requests
import json
import time

# Configuration
CHATBOT_API_URL = "http://localhost:3202/api/v1/chat"
USER_SERVICE_URL = "http://localhost:3201/api/v1/auth"

# Credentials
TEST_EMAIL = "henribesnard@example.com"
TEST_PASSWORD = "Harena123456"


def get_auth_token():
    """Get JWT token"""
    print("=" * 80)
    print("[AUTH] Connexion...")
    print("=" * 80)

    response = requests.post(
        f"{USER_SERVICE_URL}/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"[OK] Token obtenu pour {TEST_EMAIL}")
        return token
    else:
        print(f"[ERREUR] Authentification echouee: {response.text}")
        return None


def test_query_non_stream(token, query, test_name):
    """Test une query en mode non-stream"""
    print("\n" + "=" * 80)
    print(f"[TEST NON-STREAM] {test_name}")
    print(f"[QUERY] {query}")
    print("=" * 80)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {"query": query}

    start = time.time()
    try:
        response = requests.post(
            f"{CHATBOT_API_URL}/query",
            headers=headers,
            json=data,
            timeout=60
        )
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            result = response.json()

            print(f"\n[OK] Reponse recue en {latency:.0f}ms")
            print(f"[INFO] Intent: {result.get('metadata', {}).get('intent_type', 'unknown')}")
            print(f"[INFO] Sourcing mode: {result.get('metadata', {}).get('sourcing_mode', False)}")
            print(f"[INFO] Nombre de sources: {len(result.get('sources', []))}")

            if result.get('metadata', {}).get('sourcing_mode'):
                print(f"[INFO] Categories trouvees: {result.get('metadata', {}).get('categories_found', [])}")
                print(f"[INFO] Keywords utilises: {result.get('metadata', {}).get('keywords_used', [])}")

            # Afficher reponse (sans emojis)
            answer = result['answer']
            # Supprimer les emojis pour Windows
            answer_clean = answer.encode('ascii', 'ignore').decode('ascii')
            print(f"\n[REPONSE]\n{answer_clean}\n")

            # Afficher quelques sources
            sources = result.get('sources', [])
            if sources:
                print(f"[SOURCES] Affichage de {min(3, len(sources))} sources:")
                for i, source in enumerate(sources[:3], 1):
                    print(f"  {i}. {source['title']}")
                    print(f"     Score: {source['score']:.3f}")
                    if source.get('category'):
                        print(f"     Categorie: {source['category']}")

            return True
        else:
            print(f"[ERREUR] Code {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"[ERREUR] Exception: {str(e)}")
        return False


def test_query_stream(token, query, test_name):
    """Test une query en mode stream"""
    print("\n" + "=" * 80)
    print(f"[TEST STREAM] {test_name}")
    print(f"[QUERY] {query}")
    print("=" * 80)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {"query": query}

    try:
        response = requests.post(
            f"{CHATBOT_API_URL}/stream",
            headers=headers,
            json=data,
            stream=True,
            timeout=60
        )

        if response.status_code == 200:
            print("\n[OK] Stream demarre\n")

            sources_count = 0
            sourcing_mode = False
            intent_type = None
            answer_parts = []

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)

                            if chunk['type'] == 'sources':
                                sources = chunk.get('sources', [])
                                sources_count = len(sources)
                                sourcing_mode = chunk.get('metadata', {}).get('sourcing_mode', False)
                                print(f"[SOURCES] Recu {sources_count} sources")
                                if sourcing_mode:
                                    print(f"[INFO] Mode sourcing active")
                                    categories = chunk.get('metadata', {}).get('categories_found', [])
                                    if categories:
                                        print(f"[INFO] Categories: {categories}")

                            elif chunk['type'] == 'token':
                                content = chunk['content']
                                # Filtrer les emojis pour Windows
                                content_clean = content.encode('ascii', 'ignore').decode('ascii')
                                print(content_clean, end='', flush=True)
                                answer_parts.append(content)

                            elif chunk['type'] == 'done':
                                print("\n")
                                metadata = chunk.get('metadata', {})
                                intent_type = metadata.get('intent_type')
                                print(f"\n[OK] Stream termine")
                                print(f"[INFO] Intent: {intent_type}")
                                print(f"[INFO] Latence: {metadata.get('latency_ms', 0)}ms")
                                if metadata.get('sourcing_mode'):
                                    print(f"[INFO] Documents trouves: {metadata.get('num_documents_found', 0)}")
                                    print(f"[INFO] Keywords: {metadata.get('keywords_used', [])}")

                            elif chunk['type'] == 'error':
                                print(f"\n[ERREUR] {chunk.get('content', 'Unknown error')}")

                        except json.JSONDecodeError:
                            pass

            return True
        else:
            print(f"[ERREUR] Code {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"[ERREUR] Exception: {str(e)}")
        return False


def main():
    print("\n" + "=" * 80)
    print("TEST COMPLET - DOCUMENT SOURCING")
    print("=" * 80)

    # Get auth token
    token = get_auth_token()
    if not token:
        print("[ERREUR] Impossible de continuer sans authentification")
        return

    # Tests de document sourcing
    sourcing_queries = [
        ("Dans quels documents parle-t-on des amortissements ?", "Sourcing: amortissements"),
        ("Existe-t-il une jurisprudence sur la comptabilite des stocks ?", "Sourcing: jurisprudence stocks"),
        ("Quels documents traitent des provisions ?", "Sourcing: provisions"),
        ("Liste-moi les actes uniformes sur le droit commercial", "Sourcing: actes uniformes"),
    ]

    # Tests de controle (ne devraient PAS etre document_sourcing)
    control_queries = [
        ("C'est quoi un amortissement ?", "RAG Query: definition"),
        ("Comment comptabiliser une provision ?", "RAG Query: procedure"),
        ("Bonjour", "General conversation"),
    ]

    print("\n" + "=" * 80)
    print("PARTIE 1: TESTS NON-STREAM - Questions de Document Sourcing")
    print("=" * 80)

    for query, test_name in sourcing_queries[:2]:  # Test 2 premieres
        success = test_query_non_stream(token, query, test_name)
        if not success:
            print("[ATTENTION] Test echoue")
        time.sleep(1)

    print("\n" + "=" * 80)
    print("PARTIE 2: TESTS NON-STREAM - Questions de Controle")
    print("=" * 80)

    for query, test_name in control_queries[:2]:  # Test 2 premieres
        success = test_query_non_stream(token, query, test_name)
        if not success:
            print("[ATTENTION] Test echoue")
        time.sleep(1)

    print("\n" + "=" * 80)
    print("PARTIE 3: TESTS STREAM - Questions de Document Sourcing")
    print("=" * 80)

    for query, test_name in sourcing_queries[2:3]:  # Test 1 en stream
        success = test_query_stream(token, query, test_name)
        if not success:
            print("[ATTENTION] Test echoue")
        time.sleep(1)

    print("\n" + "=" * 80)
    print("PARTIE 4: TESTS STREAM - Questions de Controle")
    print("=" * 80)

    for query, test_name in control_queries[2:3]:  # Test 1 en stream
        success = test_query_stream(token, query, test_name)
        if not success:
            print("[ATTENTION] Test echoue")
        time.sleep(1)

    print("\n" + "=" * 80)
    print("TESTS TERMINES")
    print("=" * 80)


if __name__ == "__main__":
    main()
