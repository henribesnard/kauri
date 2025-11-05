#!/usr/bin/env python
"""
Direct test of intent classification without auth
"""
import asyncio
import sys
import os

# Add backend path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'kauri_chatbot_service'))

from src.rag.agents.intent_classifier import get_intent_classifier


async def test_intent_classification():
    """Test intent classification with various queries"""

    classifier = get_intent_classifier()

    test_cases = [
        ("Qui es-tu ?", "general_conversation"),
        ("Bonjour", "general_conversation"),
        ("Merci beaucoup", "general_conversation"),
        ("C'est quoi un amortissement ?", "rag_query"),
        ("Comment comptabiliser une creance douteuse ?", "rag_query"),
        ("Article 15 du SYSCOHADA", "rag_query"),
        ("Qu'est-ce que c'est ?", "clarification"),
        ("Et apres ?", "clarification"),
    ]

    print("=" * 80)
    print("TEST: Intent Classification System")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for query, expected_intent in test_cases:
        try:
            result = await classifier.classify_intent(query)
            status = "PASS" if result.intent_type == expected_intent else "FAIL"

            if status == "PASS":
                passed += 1
            else:
                failed += 1

            print(f"[{status}] Query: {query}")
            print(f"      Expected: {expected_intent}")
            print(f"      Got: {result.intent_type}")
            print(f"      Confidence: {result.confidence:.2f}")
            print(f"      Reasoning: {result.reasoning}")
            print()

        except Exception as e:
            failed += 1
            print(f"[ERROR] Query: {query}")
            print(f"        Error: {str(e)}")
            print()

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(test_intent_classification())
    sys.exit(0 if failed == 0 else 1)
