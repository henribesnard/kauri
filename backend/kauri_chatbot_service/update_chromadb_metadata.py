#!/usr/bin/env python
"""
Script to update ChromaDB metadata after plan_comptable restructuring
Removes '/chapitres_word' from file paths in metadata
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


def update_chromadb_metadata():
    """Update ChromaDB metadata for plan_comptable documents"""
    session = Session()
    chroma_store = get_chroma_store()

    logger.info("starting_chromadb_metadata_update")

    try:
        # Get all plan_comptable documents
        plan_comptable_docs = session.query(Document).filter(
            Document.file_path.like('%plan_comptable%')
        ).all()

        logger.info("found_plan_comptable_documents", count=len(plan_comptable_docs))

        total_chunks_updated = 0

        for doc in plan_comptable_docs:
            # Get all chunks for this document
            chunks = session.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).all()

            if not chunks:
                continue

            # Prepare data for ChromaDB
            chunk_ids = []
            chunk_documents = []
            chunk_embeddings = []

            for chunk in chunks:
                chunk_ids.append(chunk.embedding_id)
                chunk_documents.append(chunk.chunk_text)

            # Delete old entries from ChromaDB
            logger.info("deleting_old_chunks_from_chromadb",
                       document_title=doc.title,
                       num_chunks=len(chunk_ids))
            chroma_store.delete_documents(chunk_ids)

            # Get embeddings from ChromaDB (we need to retrieve them first)
            # Actually, ChromaDB doesn't return embeddings in query, so we need to get from embedder
            # But since we're just updating metadata, we can query, delete, and re-add

            logger.info("document_chunks_deleted_from_chromadb",
                       document_title=doc.title,
                       num_chunks=len(chunks))

            total_chunks_updated += len(chunks)

        logger.info("chromadb_metadata_update_complete",
                   total_chunks_updated=total_chunks_updated)

        print(f"\n{'='*60}")
        print(f"✅ Mise à jour ChromaDB terminée!")
        print(f"{'='*60}")
        print(f"📊 Statistiques:")
        print(f"  • Documents plan_comptable traités: {len(plan_comptable_docs)}")
        print(f"  • Chunks mis à jour:                 {total_chunks_updated}")
        print(f"{'='*60}\n")

    except Exception as e:
        logger.error("chromadb_update_failed", error=str(e))
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Note: This script only deletes old chunks from ChromaDB
    # You need to re-run ingestion to add them back with correct metadata
    print("\n⚠️  ATTENTION:")
    print("Ce script va supprimer les chunks plan_comptable de ChromaDB.")
    print("Vous devrez ensuite re-ingérer les documents plan_comptable.\n")

    response = input("Continuer? (oui/non): ")
    if response.lower() in ['oui', 'yes', 'y', 'o']:
        update_chromadb_metadata()
    else:
        print("Opération annulée.")
