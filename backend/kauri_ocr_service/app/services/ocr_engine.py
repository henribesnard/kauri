"""
OCR Engine Service - PaddleOCR implementation
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
import time
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class OCREngine:
    """Base OCR Engine interface"""

    def __init__(self):
        self.engine_name = "base"

    async def process_image(self, image_path: str, **kwargs) -> Dict[str, Any]:
        """Process an image and return OCR results"""
        raise NotImplementedError

    async def process_pdf(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """Process a PDF document and return OCR results"""
        raise NotImplementedError


class PaddleOCREngine(OCREngine):
    """PaddleOCR implementation"""

    def __init__(self):
        super().__init__()
        self.engine_name = "paddleocr"
        self._ocr = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of PaddleOCR"""
        if self._initialized:
            return

        try:
            from paddleocr import PaddleOCR

            logger.info("Initializing PaddleOCR...")

            # Initialize PaddleOCR
            lang = settings.ocr_languages[0] if settings.ocr_languages else "fr"

            self._ocr = PaddleOCR(
                use_angle_cls=settings.OCR_USE_ANGLE_CLS,
                lang=lang,
                use_gpu=settings.OCR_USE_GPU,
                show_log=False,
                det_model_dir=settings.OCR_DET_MODEL_DIR,
                rec_model_dir=settings.OCR_REC_MODEL_DIR,
                cls_model_dir=settings.OCR_CLS_MODEL_DIR,
            )

            self._initialized = True
            logger.info(f"PaddleOCR initialized successfully (lang={lang}, gpu={settings.OCR_USE_GPU})")

        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    async def process_image(self, image_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process a single image with PaddleOCR

        Args:
            image_path: Path to image file
            **kwargs: Additional options

        Returns:
            Dict with OCR results
        """
        self._initialize()

        start_time = time.time()

        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Failed to load image: {image_path}")

            # Run OCR
            result = self._ocr.ocr(image_path, cls=settings.OCR_USE_ANGLE_CLS)

            processing_time = int((time.time() - start_time) * 1000)

            # Parse results
            parsed_results = self._parse_paddleocr_results(result)

            return {
                "success": True,
                "engine": self.engine_name,
                "processing_time_ms": processing_time,
                **parsed_results
            }

        except Exception as e:
            logger.error(f"Error processing image with PaddleOCR: {e}")
            return {
                "success": False,
                "engine": self.engine_name,
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    async def process_pdf(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process a PDF document with PaddleOCR

        Args:
            pdf_path: Path to PDF file
            **kwargs: Additional options

        Returns:
            Dict with OCR results for all pages
        """
        from pdf2image import convert_from_path
        import tempfile
        import os

        self._initialize()

        start_time = time.time()

        try:
            # Convert PDF to images
            logger.info(f"Converting PDF to images: {pdf_path}")
            images = convert_from_path(pdf_path, dpi=300)

            pages_results = []
            total_text = []

            # Process each page
            for page_num, image in enumerate(images, start=1):
                logger.info(f"Processing page {page_num}/{len(images)}")

                # Save image temporarily
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    image.save(tmp_path, 'PNG')

                try:
                    # Process page
                    page_result = await self.process_image(tmp_path)
                    page_result['page_number'] = page_num
                    pages_results.append(page_result)

                    if page_result.get('success') and page_result.get('text'):
                        total_text.append(page_result['text'])

                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            processing_time = int((time.time() - start_time) * 1000)

            # Combine results
            all_words = []
            all_lines = []
            total_confidence = 0
            confidence_count = 0

            for page in pages_results:
                if page.get('success'):
                    all_words.extend(page.get('words', []))
                    all_lines.extend(page.get('lines', []))

                    if page.get('confidence_score'):
                        total_confidence += page['confidence_score']
                        confidence_count += 1

            avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0

            return {
                "success": True,
                "engine": self.engine_name,
                "processing_time_ms": processing_time,
                "page_count": len(images),
                "text": "\n\n".join(total_text),
                "pages": pages_results,
                "words": all_words,
                "lines": all_lines,
                "word_count": len(all_words),
                "confidence_score": avg_confidence
            }

        except Exception as e:
            logger.error(f"Error processing PDF with PaddleOCR: {e}")
            return {
                "success": False,
                "engine": self.engine_name,
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    def _parse_paddleocr_results(self, result: List) -> Dict[str, Any]:
        """
        Parse PaddleOCR raw results into structured format

        Args:
            result: Raw PaddleOCR result

        Returns:
            Parsed results dict
        """
        if not result or not result[0]:
            return {
                "text": "",
                "words": [],
                "lines": [],
                "word_count": 0,
                "confidence_score": 0.0
            }

        words = []
        lines = []
        text_parts = []
        total_confidence = 0
        confidence_count = 0

        # Parse each line
        for line in result[0]:
            if not line:
                continue

            bbox, (text, confidence) = line

            # Extract bounding box coordinates
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]

            line_data = {
                "text": text,
                "confidence": float(confidence),
                "bbox": {
                    "x": int(min(x_coords)),
                    "y": int(min(y_coords)),
                    "width": int(max(x_coords) - min(x_coords)),
                    "height": int(max(y_coords) - min(y_coords))
                }
            }

            lines.append(line_data)
            text_parts.append(text)

            # Split into words
            for word in text.split():
                words.append({
                    "text": word,
                    "confidence": float(confidence)
                })

            total_confidence += confidence
            confidence_count += 1

        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0

        return {
            "text": " ".join(text_parts),
            "words": words,
            "lines": lines,
            "word_count": len(words),
            "confidence_score": float(avg_confidence)
        }


class OCRService:
    """OCR Service manager - coordinates different OCR engines"""

    def __init__(self):
        self.engines = {}
        self._initialize_engines()

    def _initialize_engines(self):
        """Initialize available OCR engines"""
        # PaddleOCR (default)
        self.engines["paddleocr"] = PaddleOCREngine()
        logger.info("OCR engines initialized")

    async def process_document(
        self,
        file_path: str,
        engine: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a document with the specified OCR engine

        Args:
            file_path: Path to document
            engine: OCR engine to use (default: from settings)
            **kwargs: Additional processing options

        Returns:
            OCR results dict
        """
        # Select engine
        engine_name = engine or settings.OCR_DEFAULT_ENGINE
        ocr_engine = self.engines.get(engine_name)

        if not ocr_engine:
            raise ValueError(f"Unknown OCR engine: {engine_name}")

        # Determine file type
        file_path_obj = Path(file_path)
        extension = file_path_obj.suffix.lower()

        logger.info(f"Processing document: {file_path} with {engine_name}")

        # Process based on file type
        if extension == '.pdf':
            return await ocr_engine.process_pdf(file_path, **kwargs)
        elif extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return await ocr_engine.process_image(file_path, **kwargs)
        else:
            raise ValueError(f"Unsupported file type: {extension}")


# Global OCR service instance
ocr_service = OCRService()
