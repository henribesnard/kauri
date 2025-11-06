#!/usr/bin/env python
"""
KAURI Document Ingestion CLI
Ingest documents from base_connaissances/ into ChromaDB
NO PostgreSQL - documents are read on-the-fly from source files
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from pathlib import Path
import structlog
from typing import List, Dict, Any
import uuid

from src.config import settings
from src.ingestion.document_processor import document_processor
from src.rag.embedder.bge_embedder import get_embedder
from src.rag.vector_store.chroma_store import get_chroma_store
from src.rag.retriever.bm25_retriever import get_bm25_retriever

logger = structlog.get_logger()


def find_documents(base_path: Path) -> List[Path]:
    """Find all .docx and .pdf documents in base_connaissances/"""
    docx_files = list(base_path.glob("**/*.docx"))
    pdf_files = list(base_path.glob("**/*.pdf"))
    files = docx_files + pdf_files
    logger.info("documents_found_by_type",
               docx=len(docx_files),
               pdf=len(pdf_files),
               total=len(files))
    return files


def chunk_text(text: str, chunk_size: int = 3500, chunk_overlap: int = 300) -> List[str]:
    """
    Split text into overlapping chunks

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters (default: 3500 - universal size)
        chunk_overlap: Overlap between chunks (default: 300 - secures transitions)

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start += chunk_size - chunk_overlap

    return chunks


async def ingest_file(
    file_path: Path,
    embedder,
    chroma_store,
    processed_hashes: set
) -> str:
    """
    Ingest a single file into ChromaDB

    Args:
        file_path: Path to document
        embedder: Embedder instance
        chroma_store: ChromaDB store
        processed_hashes: Set of already processed content hashes

    Returns:
        Status: "created", "skipped", or "failed"
    """
    try:
        # Process file (extracts content with tables as markdown)
        result = document_processor.process_file(file_path)

        # Check if already ingested (by content hash)
        if result['hash'] in processed_hashes:
            logger.info("document_exists_skipping",
                       path=str(file_path),
                       hash=result['hash'][:8])
            return "skipped"

        # Chunk the content
        chunks = chunk_text(result['content'])
        logger.info("document_chunked",
                   file=file_path.name,
                   num_chunks=len(chunks))

        if not chunks:
            logger.warning("no_chunks_generated", path=str(file_path))
            return "failed"

        # Generate embeddings for chunks
        embeddings = embedder.embed_batch(chunks)

        # Prepare data for ChromaDB
        chunk_ids = []
        chunk_documents = []
        chunk_embeddings = []
        chunk_metadatas = []

        doc_id = str(uuid.uuid4())  # Unique doc ID

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_{i}"
            chunk_ids.append(chunk_id)
            chunk_documents.append(chunk)
            chunk_embeddings.append(embedding)

            # Store essential metadata - especially file_path for reading later
            chunk_metadatas.append({
                "document_id": doc_id,
                "chunk_index": i,
                "file_path": str(file_path),  # ← KEY: for reading original doc
                "file_name": file_path.name,
                "title": result.get('title', file_path.stem),
                "category": result['metadata'].get('category', ''),
                "section": result['metadata'].get('section', ''),
                "has_tables": result.get('has_tables', False),
                "content_hash": result['hash']
            })

        # Add to ChromaDB
        chroma_store.add_documents(
            ids=chunk_ids,
            documents=chunk_documents,
            embeddings=chunk_embeddings,
            metadatas=chunk_metadatas
        )

        # Mark as processed
        processed_hashes.add(result['hash'])

        logger.info("document_ingested",
                   file=file_path.name,
                   id=doc_id,
                   num_chunks=len(chunks))
        return "created"

    except Exception as e:
        error_msg = str(e)
        # Distinguish corrupted files from other errors
        if "Package not found" in error_msg or "BadZipFile" in error_msg or "not a zip file" in error_msg:
            logger.warning("corrupted_file_skipped",
                          path=str(file_path),
                          file_name=file_path.name,
                          error=error_msg)
        else:
            logger.error("ingestion_failed",
                        path=str(file_path),
                        file_name=file_path.name,
                        error=error_msg,
                        exc_info=True)
        return "failed"


def load_existing_hashes(chroma_store) -> set:
    """
    Load content hashes of already ingested documents from ChromaDB

    Args:
        chroma_store: ChromaDB store instance

    Returns:
        Set of content hashes already in the database
    """
    try:
        logger.info("loading_existing_hashes_from_chromadb")

        # Get all documents with their metadata
        collection = chroma_store.collection
        all_data = collection.get()

        if not all_data or not all_data['metadatas']:
            logger.info("no_existing_documents_in_chromadb")
            return set()

        # Extract content_hash from metadata
        existing_hashes = set()
        for metadata in all_data['metadatas']:
            if metadata and 'content_hash' in metadata:
                existing_hashes.add(metadata['content_hash'])

        logger.info("existing_hashes_loaded",
                   count=len(existing_hashes),
                   total_chunks=len(all_data['metadatas']))

        return existing_hashes

    except Exception as e:
        logger.error("failed_to_load_existing_hashes", error=str(e))
        # Return empty set on error, will process all documents
        return set()


def build_bm25_index(chroma_store, bm25_retriever):
    """
    Build BM25 index from all documents in ChromaDB

    Args:
        chroma_store: ChromaDB store instance
        bm25_retriever: BM25 retriever instance
    """
    logger.info("building_bm25_index")

    try:
        # Get all documents from ChromaDB
        collection = chroma_store.collection
        all_data = collection.get()

        if not all_data or not all_data['documents']:
            logger.warning("no_documents_found_for_bm25")
            return

        # Build documents list for BM25
        documents = []
        for doc_id, content, metadata in zip(
            all_data['ids'],
            all_data['documents'],
            all_data['metadatas']
        ):
            documents.append({
                "id": doc_id,
                "content": content,
                "metadata": metadata
            })

        # Build index
        bm25_retriever.build_index(documents)
        logger.info("bm25_index_built", num_documents=len(documents))

    except Exception as e:
        logger.error("bm25_build_failed", error=str(e), exc_info=True)


async def main_async():
    """Async main ingestion process"""
    logger.info("starting_ingestion")

    # Initialize RAG components
    embedder = get_embedder()
    chroma_store = get_chroma_store()
    bm25_retriever = get_bm25_retriever()

    # Find documents
    base_path = Path("/app/base_connaissances")
    if not base_path.exists():
        logger.error("base_connaissances_not_found", path=str(base_path.absolute()))
        print(f"\n❌ Erreur: Le dossier {base_path} n'existe pas!")
        return

    files = find_documents(base_path)
    logger.info("documents_found", count=len(files))

    if len(files) == 0:
        print(f"\n⚠️  Aucun fichier .docx ou .pdf trouvé dans {base_path}")
        return

    # Load existing hashes from ChromaDB for deduplication
    processed_hashes = load_existing_hashes(chroma_store)
    logger.info("deduplication_ready",
               existing_documents=len(processed_hashes),
               files_to_process=len(files))

    # Ingest
    stats = {"created": 0, "skipped": 0, "failed": 0}

    for file_path in files:
        result = await ingest_file(file_path, embedder, chroma_store, processed_hashes)
        stats[result] += 1

    # Build BM25 index from all chunks in ChromaDB
    build_bm25_index(chroma_store, bm25_retriever)

    logger.info("ingestion_complete", **stats)

    # Display summary
    total = stats['created'] + stats['skipped'] + stats['failed']
    success_rate = (stats['created'] / total * 100) if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"✅ Ingestion terminée!")
    print(f"{'='*60}")
    print(f"📊 Statistiques:")
    print(f"  • Fichiers trouvés:      {total}")
    print(f"  • Documents créés:       {stats['created']}")
    print(f"  • Documents ignorés:     {stats['skipped']} (déjà existants)")
    print(f"  • Échecs:                {stats['failed']} (fichiers corrompus)")
    print(f"  • Taux de succès:        {success_rate:.1f}%")
    print(f"{'='*60}\n")

    if stats['failed'] > 0:
        print(f"⚠️  {stats['failed']} fichier(s) corrompu(s) n'ont pas pu être ingérés.")
        print(f"   Consultez les logs ci-dessus pour voir les fichiers concernés.\n")

    # Show ChromaDB stats
    total_chunks = chroma_store.count()
    print(f"📦 ChromaDB: {total_chunks} chunks indexés\n")


def main():
    """Main entry point"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
