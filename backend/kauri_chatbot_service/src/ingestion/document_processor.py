"""
Document Processor - Parse and extract content from files
Simplified version using DocumentReader for .docx files
"""
import hashlib
from typing import Dict, Any
from pathlib import Path
import structlog
from .document_reader import get_document_reader

logger = structlog.get_logger()


class DocumentProcessor:
    """
    Process documents from base_connaissances
    Uses DocumentReader for enhanced .docx support (tables, structure)
    """
    SUPPORTED_FORMATS = [".docx"]  # Focus on .docx for OHADA documents

    def __init__(self):
        self.document_reader = get_document_reader()

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a document file

        Args:
            file_path: Path to document file

        Returns:
            Dict with content, metadata, hash
        """
        logger.info("processing_file", path=str(file_path))
        extension = file_path.suffix.lower()

        if extension not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {extension}. Supported: {self.SUPPORTED_FORMATS}")

        # Use DocumentReader for .docx (with table support)
        if extension == ".docx":
            doc_data = self.document_reader.read_docx(file_path)

            return {
                "content": doc_data["content"],
                "hash": self.compute_hash(doc_data["content"]),
                "metadata": doc_data["metadata"],
                "has_tables": doc_data.get("has_tables", False),
                "file_path": str(file_path),
                "file_name": file_path.name,
                "title": doc_data["metadata"].get("title", file_path.stem)
            }
        else:
            raise ValueError(f"Format not yet implemented: {extension}")


# Singleton instance
document_processor = DocumentProcessor()
