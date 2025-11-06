"""
PDF Generator Service - Creates searchable PDFs with OCR layer
Uses OCRmyPDF to add text layer to image-based PDFs
"""
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import ocrmypdf
from PIL import Image
import img2pdf

from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFGeneratorService:
    """Service for generating searchable PDFs with OCR text layer"""

    def __init__(self):
        self.output_dir = Path("/app/processed_pdfs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF Generator initialized. Output directory: {self.output_dir}")

    async def generate_searchable_pdf(
        self,
        input_pdf_path: str,
        output_filename: Optional[str] = None,
        ocr_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a searchable PDF from an image-based PDF

        Args:
            input_pdf_path: Path to input PDF file
            output_filename: Custom output filename (optional)
            ocr_data: OCR results data from PaddleOCR (optional, for metadata)
            **kwargs: Additional OCRmyPDF options

        Returns:
            Dict with generation results including output path
        """
        try:
            input_path = Path(input_pdf_path)

            if not input_path.exists():
                raise FileNotFoundError(f"Input PDF not found: {input_pdf_path}")

            # Generate output filename
            if output_filename is None:
                output_filename = f"{input_path.stem}_searchable.pdf"

            output_path = self.output_dir / output_filename

            logger.info(f"Generating searchable PDF: {input_path.name} -> {output_filename}")

            # OCRmyPDF configuration
            ocrmypdf_options = {
                "language": self._get_language_codes(),
                "output_type": "pdfa",  # PDF/A format for archival
                "optimize": 1,  # Light optimization
                "deskew": True,  # Deskew pages
                "clean": True,  # Clean pages before OCR
                "skip_text": True,  # Skip pages that already have text
                "force_ocr": False,  # Don't re-OCR pages with text
                "redo_ocr": False,  # Don't redo existing OCR
                "rotate_pages": True,  # Auto-rotate pages
                "remove_background": False,  # Keep original background
                "sidecar": None,  # Don't generate sidecar text file
                "jobs": settings.WORKER_CONCURRENCY,  # Parallel processing
                "progress_bar": False,  # No progress bar in logs
            }

            # Override with custom options
            ocrmypdf_options.update(kwargs)

            # Run OCRmyPDF
            logger.info(f"Running OCRmyPDF with options: {ocrmypdf_options}")

            result_code = ocrmypdf.ocr(
                input_file=str(input_path),
                output_file=str(output_path),
                **ocrmypdf_options
            )

            # Check result
            if result_code == 0:
                file_size = output_path.stat().st_size
                logger.info(f"Searchable PDF generated successfully: {output_filename} ({file_size} bytes)")

                return {
                    "success": True,
                    "output_path": str(output_path),
                    "output_filename": output_filename,
                    "file_size": file_size,
                    "input_file": str(input_path),
                    "message": "Searchable PDF generated successfully"
                }
            else:
                raise Exception(f"OCRmyPDF returned error code: {result_code}")

        except ocrmypdf.exceptions.PriorOcrFoundError:
            # PDF already has OCR layer - just copy it
            logger.info(f"PDF already has OCR layer: {input_pdf_path}")

            if str(input_path) != str(output_path):
                import shutil
                shutil.copy2(input_path, output_path)

            return {
                "success": True,
                "output_path": str(output_path),
                "output_filename": output_filename,
                "file_size": output_path.stat().st_size,
                "input_file": str(input_path),
                "message": "PDF already has OCR layer (copied)"
            }

        except Exception as e:
            logger.error(f"Error generating searchable PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "input_file": str(input_pdf_path),
                "message": "Failed to generate searchable PDF"
            }

    async def generate_pdf_from_images(
        self,
        image_paths: list,
        output_filename: str,
        apply_ocr: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a PDF from a list of images and optionally apply OCR

        Args:
            image_paths: List of image file paths
            output_filename: Output PDF filename
            apply_ocr: Whether to apply OCR to make it searchable

        Returns:
            Dict with generation results
        """
        try:
            if not image_paths:
                raise ValueError("No images provided")

            logger.info(f"Creating PDF from {len(image_paths)} images")

            # Create temporary non-searchable PDF first
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                tmp_pdf_path = tmp_pdf.name

            # Convert images to PDF
            with open(tmp_pdf_path, 'wb') as f:
                f.write(img2pdf.convert(image_paths))

            logger.info(f"Temporary PDF created: {tmp_pdf_path}")

            # If OCR requested, apply it
            if apply_ocr:
                result = await self.generate_searchable_pdf(
                    input_pdf_path=tmp_pdf_path,
                    output_filename=output_filename
                )

                # Clean up temporary file
                try:
                    os.unlink(tmp_pdf_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary PDF: {e}")

                return result
            else:
                # Just move the PDF to output directory
                output_path = self.output_dir / output_filename
                import shutil
                shutil.move(tmp_pdf_path, output_path)

                return {
                    "success": True,
                    "output_path": str(output_path),
                    "output_filename": output_filename,
                    "file_size": output_path.stat().st_size,
                    "message": "PDF created from images (no OCR)"
                }

        except Exception as e:
            logger.error(f"Error generating PDF from images: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate PDF from images"
            }

    async def optimize_pdf(
        self,
        input_pdf_path: str,
        output_filename: Optional[str] = None,
        optimization_level: int = 2
    ) -> Dict[str, Any]:
        """
        Optimize an existing PDF (reduce size)

        Args:
            input_pdf_path: Path to input PDF
            output_filename: Output filename (optional)
            optimization_level: 0=none, 1=safe, 2=lossy, 3=aggressive

        Returns:
            Dict with optimization results
        """
        try:
            input_path = Path(input_pdf_path)

            if output_filename is None:
                output_filename = f"{input_path.stem}_optimized.pdf"

            output_path = self.output_dir / output_filename

            logger.info(f"Optimizing PDF: {input_path.name} (level={optimization_level})")

            # Run OCRmyPDF in optimize-only mode
            ocrmypdf.ocr(
                input_file=str(input_path),
                output_file=str(output_path),
                skip_text=True,
                redo_ocr=False,
                optimize=optimization_level,
                jobs=settings.WORKER_CONCURRENCY
            )

            original_size = input_path.stat().st_size
            optimized_size = output_path.stat().st_size
            reduction_percent = ((original_size - optimized_size) / original_size) * 100

            logger.info(
                f"PDF optimized: {original_size} -> {optimized_size} bytes "
                f"({reduction_percent:.1f}% reduction)"
            )

            return {
                "success": True,
                "output_path": str(output_path),
                "output_filename": output_filename,
                "original_size": original_size,
                "optimized_size": optimized_size,
                "reduction_percent": reduction_percent,
                "message": "PDF optimized successfully"
            }

        except Exception as e:
            logger.error(f"Error optimizing PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to optimize PDF"
            }

    def _get_language_codes(self) -> str:
        """
        Convert language codes from settings to Tesseract format

        Returns:
            Language codes string (e.g., "fra+eng")
        """
        # Map common language codes to Tesseract codes
        lang_map = {
            "fr": "fra",
            "en": "eng",
            "es": "spa",
            "de": "deu",
            "it": "ita",
            "pt": "por",
            "ar": "ara"
        }

        languages = []
        for lang in settings.ocr_languages:
            tesseract_lang = lang_map.get(lang.lower(), lang)
            languages.append(tesseract_lang)

        return "+".join(languages)

    def get_output_path(self, filename: str) -> Path:
        """Get the full path for an output file"""
        return self.output_dir / filename

    def file_exists(self, filename: str) -> bool:
        """Check if a generated PDF exists"""
        return (self.output_dir / filename).exists()

    def delete_file(self, filename: str) -> bool:
        """Delete a generated PDF file"""
        try:
            file_path = self.output_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False


# Global PDF generator service instance
pdf_generator_service = PDFGeneratorService()
