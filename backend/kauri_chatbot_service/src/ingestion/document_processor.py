"""
Document Processor - Parse and extract content from files
Supports both .docx and .pdf files
"""
import hashlib
from typing import Dict, Any
from pathlib import Path
import structlog
import pdfplumber
from .document_reader import get_document_reader

logger = structlog.get_logger()


class DocumentProcessor:
    """
    Process documents from base_connaissances
    Supports .docx (with tables) and .pdf files
    """
    SUPPORTED_FORMATS = [".docx", ".pdf"]  # Support both formats

    def __init__(self):
        self.document_reader = get_document_reader()

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def read_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract text from PDF file using pdfplumber

        Args:
            file_path: Path to PDF file

        Returns:
            Dict with content and metadata
        """
        try:
            text_parts = []
            has_tables = False

            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    # Check for tables
                    tables = page.extract_tables()
                    if tables:
                        has_tables = True
                        for table in tables:
                            # Convert table to markdown-like format
                            table_text = self._table_to_text(table)
                            text_parts.append(f"\n\n[TABLE]\n{table_text}\n[/TABLE]\n\n")

            content = "\n\n".join(text_parts)

            # Extract metadata
            metadata = {
                "category": self._infer_category_from_path(file_path),
                "section": "",
                "title": file_path.stem
            }

            logger.info("pdf_processed",
                       path=str(file_path),
                       length=len(content),
                       has_tables=has_tables)

            return {
                "content": content,
                "metadata": metadata,
                "has_tables": has_tables
            }

        except Exception as e:
            logger.error("pdf_read_error", path=str(file_path), error=str(e))
            raise

    def _table_to_text(self, table: list) -> str:
        """Convert table data to text format"""
        if not table:
            return ""

        lines = []
        for row in table:
            # Filter out None values and join with | separator
            row_text = " | ".join(str(cell) if cell else "" for cell in row)
            lines.append(row_text)

        return "\n".join(lines)

    def _infer_category_from_path(self, file_path: Path) -> str:
        """Infer document category from file path"""
        path_parts = file_path.parts

        if "doctrines" in path_parts:
            return "doctrine"
        elif "jurisprudences" in path_parts:
            return "jurisprudence"
        elif "actes_uniformes" in path_parts:
            return "acte_uniforme"
        elif "plan_comptable" in path_parts:
            return "plan_comptable"
        else:
            return "general"

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

        # Use pdfplumber for .pdf
        elif extension == ".pdf":
            pdf_data = self.read_pdf(file_path)

            return {
                "content": pdf_data["content"],
                "hash": self.compute_hash(pdf_data["content"]),
                "metadata": pdf_data["metadata"],
                "has_tables": pdf_data.get("has_tables", False),
                "file_path": str(file_path),
                "file_name": file_path.name,
                "title": pdf_data["metadata"].get("title", file_path.stem)
            }

        else:
            raise ValueError(f"Format not yet implemented: {extension}")


# Singleton instance
document_processor = DocumentProcessor()
