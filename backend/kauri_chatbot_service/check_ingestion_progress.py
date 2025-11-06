#!/usr/bin/env python
"""
Script de suivi de la progression de l'ingestion
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from src.rag.vector_store.chroma_store import get_chroma_store
from ingest_documents import load_existing_hashes

def main():
    print("\n" + "="*70)
    print("📊 PROGRESSION DE L'INGESTION")
    print("="*70)

    try:
        # Connexion à ChromaDB
        chroma_store = get_chroma_store()

        # Compteurs
        total_chunks = chroma_store.count()

        # Charger les hashes pour compter les documents uniques
        hashes = load_existing_hashes(chroma_store)
        unique_docs = len(hashes)

        # Compter les fichiers totaux à ingérer
        base_path = Path("/app/base_connaissances")
        docx_files = list(base_path.glob("**/*.docx"))
        pdf_files = list(base_path.glob("**/*.pdf"))
        total_files = len(docx_files) + len(pdf_files)

        # Calculs
        progress_pct = (unique_docs / total_files * 100) if total_files > 0 else 0
        remaining = total_files - unique_docs
        avg_chunks_per_doc = total_chunks / unique_docs if unique_docs > 0 else 0

        print(f"\n📁 Fichiers à traiter:")
        print(f"   • Total:        {total_files} fichiers")
        print(f"   • DOCX:         {len(docx_files)}")
        print(f"   • PDF:          {len(pdf_files)}")

        print(f"\n✅ Documents ingérés:")
        print(f"   • Uniques:      {unique_docs} documents")
        print(f"   • Restants:     {remaining} documents")
        print(f"   • Progression:  {progress_pct:.1f}%")

        print(f"\n📦 Chunks dans ChromaDB:")
        print(f"   • Total:        {total_chunks} chunks")
        print(f"   • Moyenne:      {avg_chunks_per_doc:.1f} chunks/doc")

        # Barre de progression
        bar_length = 50
        filled_length = int(bar_length * unique_docs // total_files)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        print(f"\n[{bar}] {progress_pct:.1f}%")

        # Estimation du temps restant (basé sur ~5-8 secondes par document)
        if remaining > 0:
            avg_time_per_doc = 6  # secondes
            remaining_time_sec = remaining * avg_time_per_doc
            remaining_hours = remaining_time_sec / 3600
            remaining_minutes = (remaining_time_sec % 3600) / 60

            print(f"\n⏱️  Temps restant estimé:")
            if remaining_hours >= 1:
                print(f"   • ~{remaining_hours:.1f} heures ({remaining_minutes:.0f} minutes)")
            else:
                print(f"   • ~{remaining_minutes:.0f} minutes")

        print("\n" + "="*70 + "\n")

        # Status de l'ingestion
        if unique_docs == 0:
            print("⚠️  L'ingestion n'a pas encore démarré")
        elif unique_docs < total_files:
            print("🔄 Ingestion en cours...")
            print("\n💡 Pour voir les logs en direct:")
            print("   docker exec kauri_chatbot_service tail -f /app/logs/ingestion.log")
        else:
            print("✅ INGESTION TERMINÉE!")
            print(f"\n📊 Résumé final:")
            print(f"   • {unique_docs} documents ingérés")
            print(f"   • {total_chunks} chunks créés")
            print(f"   • Moyenne: {avg_chunks_per_doc:.1f} chunks/document")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
