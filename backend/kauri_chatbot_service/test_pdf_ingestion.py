#!/usr/bin/env python
"""
Script de test pour valider l'ingestion de PDFs avec déduplication
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from pathlib import Path
from src.ingestion.document_processor import document_processor
from src.rag.vector_store.chroma_store import get_chroma_store

async def test_pdf_processing():
    """Test du traitement d'un PDF"""
    print("=" * 70)
    print("Test 1: Traitement d'un PDF")
    print("=" * 70)

    # Trouver un PDF de test
    test_pdf = Path("/app/base_connaissances/doctrines")
    pdf_files = list(test_pdf.glob("*.pdf"))

    if not pdf_files:
        print("❌ Aucun PDF trouvé dans base_connaissances/doctrines/")
        return False

    test_file = pdf_files[0]
    print(f"\nFichier de test: {test_file.name}")

    try:
        # Process le PDF
        result = document_processor.process_file(test_file)

        print(f"✅ PDF traité avec succès!")
        print(f"   Hash: {result['hash'][:16]}...")
        print(f"   Contenu extrait: {len(result['content'])} caractères")
        print(f"   Catégorie: {result['metadata'].get('category', 'N/A')}")
        print(f"   Tables détectées: {result.get('has_tables', False)}")

        return True

    except Exception as e:
        print(f"❌ Erreur lors du traitement: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_deduplication():
    """Test de la déduplication"""
    print("\n" + "=" * 70)
    print("Test 2: Déduplication avec ChromaDB")
    print("=" * 70)

    try:
        chroma_store = get_chroma_store()

        # Compte actuel
        current_count = chroma_store.count()
        print(f"\n📊 Documents actuellement dans ChromaDB: {current_count}")

        # Charger les hashes existants
        from ingest_documents import load_existing_hashes
        existing_hashes = load_existing_hashes(chroma_store)

        print(f"🔐 Hashes uniques trouvés: {len(existing_hashes)}")

        if len(existing_hashes) > 0:
            print(f"✅ Le système de déduplication est opérationnel!")
            print(f"   Exemple de hash: {list(existing_hashes)[0][:16]}...")
        else:
            print(f"⚠️  Aucun document dans ChromaDB (base vide)")

        return True

    except Exception as e:
        print(f"❌ Erreur lors du test de déduplication: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_file_finding():
    """Test de la recherche de fichiers"""
    print("\n" + "=" * 70)
    print("Test 3: Recherche de fichiers dans base_connaissances")
    print("=" * 70)

    try:
        from ingest_documents import find_documents

        base_path = Path("/app/base_connaissances")
        files = find_documents(base_path)

        print(f"\n📁 Fichiers trouvés: {len(files)}")

        # Compter par type
        pdf_count = sum(1 for f in files if f.suffix.lower() == '.pdf')
        docx_count = sum(1 for f in files if f.suffix.lower() == '.docx')

        print(f"   • PDFs: {pdf_count}")
        print(f"   • DOCX: {docx_count}")

        # Compter par catégorie
        categories = {}
        for f in files:
            for part in f.parts:
                if part in ['doctrines', 'jurisprudences', 'actes_uniformes', 'plan_comptable', 'presentation_ohada']:
                    categories[part] = categories.get(part, 0) + 1
                    break

        print(f"\n📂 Distribution par catégorie:")
        for cat, count in sorted(categories.items()):
            print(f"   • {cat}: {count} fichiers")

        if len(files) > 0:
            print(f"\n✅ Système de recherche opérationnel!")
            return True
        else:
            print(f"\n⚠️  Aucun fichier trouvé (vérifiez le dossier base_connaissances)")
            return False

    except Exception as e:
        print(f"❌ Erreur lors de la recherche: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    print("\n" + "=" * 70)
    print("🧪 TESTS DU SYSTÈME D'INGESTION PDF")
    print("=" * 70)

    tests_results = []

    # Test 1: Traitement PDF
    result1 = await test_pdf_processing()
    tests_results.append(("Traitement PDF", result1))

    # Test 2: Déduplication
    result2 = await test_deduplication()
    tests_results.append(("Déduplication", result2))

    # Test 3: Recherche de fichiers
    result3 = await test_file_finding()
    tests_results.append(("Recherche fichiers", result3))

    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)

    for test_name, result in tests_results:
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        print(f"   {test_name}: {status}")

    all_passed = all(result for _, result in tests_results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ TOUS LES TESTS SONT PASSÉS!")
        print("\n💡 Vous pouvez maintenant lancer l'ingestion complète:")
        print("   docker exec kauri_chatbot_service python ingest_documents.py")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("\n💡 Vérifiez les erreurs ci-dessus")
    print("=" * 70 + "\n")

    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
