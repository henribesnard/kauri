#!/usr/bin/env python
"""
Migration script for plan_comptable restructuring
Deletes old plan_comptable documents and allows re-ingestion with new paths
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import structlog

from src.config import settings
from src.models.document import DocumentChunk, Document
from src.rag.vector_store.chroma_store import get_chroma_store

logger = structlog.get_logger()

# Database setup
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)


def migrate_plan_comptable():
    """Delete old plan_comptable documents to allow re-ingestion"""
    session = Session()
    chroma_store = get_chroma_store()

    logger.info("starting_plan_comptable_migration")

    try:
        # Get all plan_comptable documents
        plan_comptable_docs = session.query(Document).filter(
            Document.file_path.like('%plan_comptable%')
        ).all()

        logger.info("found_plan_comptable_documents", count=len(plan_comptable_docs))

        total_chunks_deleted = 0
        chunk_ids_to_delete = []

        # Collect all chunk IDs to delete from ChromaDB
        for doc in plan_comptable_docs:
            chunks = session.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).all()

            for chunk in chunks:
                if chunk.embedding_id:
                    chunk_ids_to_delete.append(chunk.embedding_id)

            total_chunks_deleted += len(chunks)

        # Delete from ChromaDB
        if chunk_ids_to_delete:
            logger.info("deleting_chunks_from_chromadb", count=len(chunk_ids_to_delete))
            chroma_store.delete_documents(chunk_ids_to_delete)
            logger.info("chunks_deleted_from_chromadb")

        # Delete from PostgreSQL (cascades to chunks)
        for doc in plan_comptable_docs:
            session.delete(doc)

        session.commit()

        logger.info("plan_comptable_migration_complete",
                   documents_deleted=len(plan_comptable_docs),
                   chunks_deleted=total_chunks_deleted)

        print(f"\n{'='*60}")
        print(f"✅ Migration terminée!")
        print(f"{'='*60}")
        print(f"📊 Statistiques:")
        print(f"  • Documents supprimés:  {len(plan_comptable_docs)}")
        print(f"  • Chunks supprimés:     {total_chunks_deleted}")
        print(f"{'='*60}\n")
        print(f"🔄 Prochaine étape:")
        print(f"   Lancez la ré-ingestion des documents:")
        print(f"   docker exec kauri_chatbot_service python ingest_documents.py\n")

    except Exception as e:
        logger.error("migration_failed", error=str(e))
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("\n⚠️  ATTENTION:")
    print("Ce script va supprimer tous les documents plan_comptable de:")
    print("  - PostgreSQL (table documents et document_chunks)")
    print("  - ChromaDB (embeddings)")
    print("\nVous devrez ensuite ré-ingérer les documents.\n")

    response = input("Continuer? (oui/non): ")
    if response.lower() in ['oui', 'yes', 'y', 'o']:
        migrate_plan_comptable()
    else:
        print("Opération annulée.")
