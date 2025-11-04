#!/usr/bin/env python
"""
KAURI Document Ingestion CLI
Ingest documents from base_connaissances/ into PostgreSQL + ChromaDB
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from pathlib import Path
import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any
import uuid
from datetime import datetime

from src.config import settings
from src.models.document import Base, Document, DocumentChunk, IngestionLog
from src.ingestion.document_processor import document_processor
from src.rag.embedder.bge_embedder import get_embedder
from src.rag.vector_store.chroma_store import get_chroma_store
from src.rag.retriever.bm25_retriever import get_bm25_retriever

logger = structlog.get_logger()

# Database setup
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)

def init_db():
    """Initialize database tables"""
    logger.info("initializing_database")
    Base.metadata.create_all(engine)
    logger.info("database_initialized")

def find_documents(base_path: Path):
    """Find all documents in base_connaissances/"""
    patterns = ["**/*.txt", "**/*.md", "**/*.pdf", "**/*.docx"]
    files = []
    for pattern in patterns:
        files.extend(base_path.glob(pattern))
    return files

def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - chunk_overlap

    return chunks


async def ingest_file(file_path: Path, session, embedder, chroma_store):
    """Ingest a single file with embeddings"""
    try:
        # Process file
        result = document_processor.process_file(file_path)

        # Check if already exists
        existing = session.query(Document).filter_by(content_hash=result['hash']).first()

        if existing:
            logger.info("document_exists_skipping", path=str(file_path))
            return "skipped"

        # Create document
        doc = Document(
            title=result['title'],
            content_text=result['content'],
            content_hash=result['hash'],
            file_path=result['file_path'],
            file_name=file_path.name,
            document_type="document",
            status="published"
        )

        session.add(doc)
        session.flush()  # Get doc.id without committing

        # Chunk the content
        chunks = chunk_text(result['content'])
        logger.info("document_chunked", title=doc.title, num_chunks=len(chunks))

        # Generate embeddings for chunks
        embeddings = embedder.embed_batch(chunks)

        # Prepare data for ChromaDB
        chunk_ids = []
        chunk_documents = []
        chunk_embeddings = []
        chunk_metadatas = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc.id}_{i}"
            chunk_ids.append(chunk_id)
            chunk_documents.append(chunk)
            chunk_embeddings.append(embedding)
            chunk_metadatas.append({
                "document_id": str(doc.id),
                "chunk_index": i,
                "title": doc.title,
                "file_name": doc.file_name,
                "source": result.get('file_path', '')
            })

            # Create DocumentChunk record
            doc_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_text=chunk,
                chunk_index=i,
                chunk_size=len(chunk),
                embedding_id=chunk_id
            )
            session.add(doc_chunk)

        # Add to ChromaDB
        chroma_store.add_documents(
            ids=chunk_ids,
            documents=chunk_documents,
            embeddings=chunk_embeddings,
            metadatas=chunk_metadatas
        )

        session.commit()

        logger.info("document_ingested",
                   title=doc.title,
                   id=str(doc.id),
                   num_chunks=len(chunks))
        return "created"

    except Exception as e:
        error_msg = str(e)
        # Distinguish corrupted files from other errors
        if "Package not found" in error_msg or "BadZipFile" in error_msg:
            logger.warning("corrupted_file_skipped",
                          path=str(file_path),
                          file_name=file_path.name,
                          error=error_msg)
        else:
            logger.error("ingestion_failed",
                        path=str(file_path),
                        file_name=file_path.name,
                        error=error_msg)
        session.rollback()
        return "failed"

def build_bm25_index(session, bm25_retriever):
    """Build BM25 index from all documents in database"""
    logger.info("building_bm25_index")

    # Get all chunks
    chunks = session.query(DocumentChunk).all()

    if not chunks:
        logger.warning("no_chunks_found_for_bm25")
        return

    # Build documents list
    documents = []
    for chunk in chunks:
        documents.append({
            "id": chunk.embedding_id,
            "content": chunk.chunk_text,
            "metadata": {
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index
            }
        })

    # Build index
    bm25_retriever.build_index(documents)
    logger.info("bm25_index_built", num_documents=len(documents))


async def main_async():
    """Async main ingestion process"""
    logger.info("starting_ingestion")

    # Initialize DB
    init_db()

    # Initialize RAG components
    embedder = get_embedder()
    chroma_store = get_chroma_store()
    bm25_retriever = get_bm25_retriever()

    # Find documents
    base_path = Path("/app/base_connaissances")
    if not base_path.exists():
        logger.error("base_connaissances_not_found", path=str(base_path.absolute()))
        return

    files = find_documents(base_path)
    logger.info("documents_found", count=len(files))

    # Ingest
    session = Session()
    stats = {"created": 0, "skipped": 0, "failed": 0}

    for file_path in files:
        result = await ingest_file(file_path, session, embedder, chroma_store)
        stats[result] += 1

    # Build BM25 index from all chunks
    build_bm25_index(session, bm25_retriever)

    session.close()

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


def main():
    """Main entry point"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
