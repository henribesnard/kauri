"""
Test de la détection de questions générales
"""

# Liste des patterns (copié depuis rag_pipeline.py)
general_patterns = [
    "qui es-tu", "qui es tu", "c'est quoi kauri", "présente-toi", "présente toi",
    "bonjour", "salut", "hello", "bonsoir", "bonne journée",
    "merci", "merci beaucoup", "d'accord", "ok", "très bien",
    "au revoir", "à bientôt", "à plus", "bye",
    "comment ça va", "ça va", "comment vas-tu",
    "quel est ton rôle", "que fais-tu", "que peux-tu faire",
    "aide", "help", "comment utiliser"
]

def is_general_question(query: str) -> bool:
    """Check if query is a general question that doesn't need RAG retrieval"""
    query_lower = query.lower().strip()

    # Check if query matches any general pattern
    # Use word count limit only for very short phrases to avoid false positives
    for pattern in general_patterns:
        if pattern in query_lower:
            # For longer patterns (4+ words), require exact match
            if len(pattern.split()) >= 4:
                if pattern == query_lower or query_lower.startswith(pattern):
                    return True
            # For shorter patterns, allow if query is also short (<=5 words)
            elif len(query_lower.split()) <= 5:
                return True

    return False

# Tests
test_queries = [
    # Questions générales qui devraient être détectées
    ("Qui es-tu ?", True),
    ("Bonjour", True),
    ("Salut !", True),
    ("Merci beaucoup", True),
    ("C'est quoi KAURI ?", True),
    ("Quel est ton rôle ?", True),
    ("Comment ça va ?", True),
    ("Au revoir", True),
    ("Aide", True),

    # Questions OHADA qui nécessitent RAG (plus de 3 mots)
    ("C'est quoi un amortissement ?", False),
    ("Comment comptabiliser une créance douteuse ?", False),
    ("Quelle est la différence entre classe 2 et classe 3 ?", False),
    ("Explique-moi le plan comptable OHADA", False),

    # Questions courtes mais qui ne matchent pas les patterns
    ("Plan comptable", False),
    ("Article 15", False),
]

print("Test de détection de questions générales\n")
print("=" * 60)

all_passed = True
for query, expected in test_queries:
    result = is_general_question(query)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        all_passed = False

    print(f"{status} | Query: '{query}'")
    print(f"       | Expected: {expected}, Got: {result}")
    if result != expected:
        print(f"       | ERROR: Detection incorrecte!")
    print()

print("=" * 60)
if all_passed:
    print("Tous les tests sont passes!")
else:
    print("Certains tests ont echoue")
