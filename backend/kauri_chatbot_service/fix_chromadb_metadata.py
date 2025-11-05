#!/usr/bin/env python
"""
Quick fix: Update ChromaDB metadata for plan_comptable documents
Fetches all chunks, updates metadata, and re-adds them
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import chromadb
from chromadb.config import Settings as ChromaSettings
from src.config import settings
import structlog

logger = structlog.get_logger()


def fix_chromadb_metadata():
    """Update ChromaDB metadata by fetching, updating, and replacing"""
    # Connect to ChromaDB
    client = chromadb.HttpClient(
        host=settings.vector_db_host,
        port=settings.vector_db_port,
        settings=ChromaSettings(anonymized_telemetry=False)
    )

    collection = client.get_collection(name="kauri_ohada_knowledge")

    logger.info("connected_to_chromadb", count=collection.count())

    # Get all documents
    all_data = collection.get(include=["metadatas", "documents", "embeddings"])

    ids = all_data["ids"]
    metadatas = all_data["metadatas"]
    documents = all_data["documents"]
    embeddings = all_data["embeddings"]

    logger.info("fetched_all_documents", count=len(ids))

    # Find and update plan_comptable metadata
    updated_count = 0
    ids_to_update = []
    metadatas_to_update = []
    documents_to_update = []
    embeddings_to_update = []

    for i, (id, metadata, doc, embedding) in enumerate(zip(ids, metadatas, documents, embeddings)):
        source = metadata.get("source", "")

        if "/chapitres_word/" in source:
            # Update metadata
            new_source = source.replace("/chapitres_word/", "/")
            metadata["source"] = new_source

            # Collect for batch update
            ids_to_update.append(id)
            metadatas_to_update.append(metadata)
            documents_to_update.append(doc)
            embeddings_to_update.append(embedding)

            updated_count += 1

            if updated_count % 10 == 0:
                logger.info("processing_updates", count=updated_count)

    logger.info("found_documents_to_update", count=updated_count)

    if updated_count > 0:
        # Delete old entries
        logger.info("deleting_old_entries", count=len(ids_to_update))
        collection.delete(ids=ids_to_update)

        # Add back with updated metadata
        logger.info("adding_updated_entries", count=len(ids_to_update))
        collection.add(
            ids=ids_to_update,
            documents=documents_to_update,
            embeddings=embeddings_to_update,
            metadatas=metadatas_to_update
        )

        logger.info("chromadb_metadata_updated", count=updated_count)

        print(f"\n{'='*60}")
        print(f"✅ ChromaDB metadata mis à jour!")
        print(f"{'='*60}")
        print(f"📊 Statistiques:")
        print(f"  • Chunks mis à jour: {updated_count}")
        print(f"{'='*60}\n")
    else:
        print("\n✅ Aucune mise à jour nécessaire.\n")


if __name__ == "__main__":
    fix_chromadb_metadata()
