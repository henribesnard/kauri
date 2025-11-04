"""
Document Processor - Parse and extract content from files
"""
import os
import hashlib
from typing import Dict, Any, List
from pathlib import Path
import structlog
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup

logger = structlog.get_logger()

class DocumentProcessor:
    SUPPORTED_FORMATS = [".txt", ".md", ".pdf", ".docx", ".html"]
    
    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        logger.info("processing_file", path=str(file_path))
        extension = file_path.suffix.lower()
        
        if extension == ".txt" or extension == ".md":
            content = file_path.read_text(encoding="utf-8")
        elif extension == ".pdf":
            reader = PdfReader(str(file_path))
            content = "\n".join(page.extract_text() for page in reader.pages)
        elif extension == ".docx":
            doc = docx.Document(str(file_path))
            content = "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
        else:
            content = file_path.read_text(encoding="utf-8")
        
        return {
            "content": content,
            "hash": self.compute_hash(content),
            "title": file_path.stem,
            "file_path": str(file_path)
        }

document_processor = DocumentProcessor()
