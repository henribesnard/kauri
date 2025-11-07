"""
Script de test pour convertir les PDFs découpés en documents Word avec texte sélectionnable
Utilise OCRmyPDF pour créer des PDFs avec couche OCR, puis les convertit en DOCX
"""
import os
import logging
from pathlib import Path
import time
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_pdf_to_searchable(input_pdf: Path, output_pdf: Path) -> dict:
    """
    Convertit un PDF en PDF avec couche OCR (texte sélectionnable)

    Args:
        input_pdf: Chemin du PDF d'entrée
        output_pdf: Chemin du PDF de sortie avec OCR

    Returns:
        Dictionnaire avec les résultats de la conversion
    """
    try:
        import ocrmypdf

        start_time = time.time()

        logger.info(f"Traitement OCR de: {input_pdf.name}")

        # Configuration OCRmyPDF
        result = ocrmypdf.ocr(
            input_file=str(input_pdf),
            output_file=str(output_pdf),
            language=['fra', 'eng'],  # Français et Anglais
            output_type='pdfa',  # Format PDF/A pour archivage
            optimize=1,  # Optimisation légère
            deskew=True,  # Correction inclinaison
            clean=True,  # Nettoyage avant OCR
            skip_text=True,  # Sauter pages avec texte
            force_ocr=False,  # Ne pas refaire OCR existant
            rotate_pages=True,  # Rotation automatique
            jobs=2,  # Traitement parallèle
            progress_bar=False,
        )

        elapsed_time = time.time() - start_time
        file_size = output_pdf.stat().st_size if output_pdf.exists() else 0

        if result == 0:
            logger.info(f"✓ Succès: {output_pdf.name} ({file_size / 1024:.1f} KB) en {elapsed_time:.1f}s")
            return {
                'success': True,
                'input_file': str(input_pdf),
                'output_file': str(output_pdf),
                'file_size': file_size,
                'processing_time': elapsed_time,
                'message': 'Conversion réussie'
            }
        else:
            logger.error(f"✗ Échec: Code retour {result}")
            return {
                'success': False,
                'input_file': str(input_pdf),
                'error': f'OCRmyPDF retourné code {result}',
                'processing_time': elapsed_time
            }

    except Exception as e:
        logger.error(f"✗ Erreur lors de la conversion de {input_pdf.name}: {e}")
        return {
            'success': False,
            'input_file': str(input_pdf),
            'error': str(e),
            'processing_time': time.time() - start_time if 'start_time' in locals() else 0
        }


def convert_pdf_to_docx(input_pdf: Path, output_docx: Path) -> dict:
    """
    Convertit un PDF en document Word (DOCX)

    Args:
        input_pdf: Chemin du PDF d'entrée
        output_docx: Chemin du DOCX de sortie

    Returns:
        Dictionnaire avec les résultats de la conversion
    """
    try:
        from pdf2docx import Converter

        start_time = time.time()

        logger.info(f"Conversion PDF -> DOCX: {input_pdf.name}")

        cv = Converter(str(input_pdf))
        cv.convert(str(output_docx), start=0, end=None)
        cv.close()

        elapsed_time = time.time() - start_time
        file_size = output_docx.stat().st_size if output_docx.exists() else 0

        logger.info(f"✓ Succès: {output_docx.name} ({file_size / 1024:.1f} KB) en {elapsed_time:.1f}s")

        return {
            'success': True,
            'input_file': str(input_pdf),
            'output_file': str(output_docx),
            'file_size': file_size,
            'processing_time': elapsed_time,
            'message': 'Conversion DOCX réussie'
        }

    except Exception as e:
        logger.error(f"✗ Erreur lors de la conversion DOCX de {input_pdf.name}: {e}")
        return {
            'success': False,
            'input_file': str(input_pdf),
            'error': str(e),
            'processing_time': time.time() - start_time if 'start_time' in locals() else 0
        }


def process_all_pdfs():
    """
    Traite tous les PDFs découpés:
    1. Applique OCR pour rendre le texte sélectionnable
    2. Convertit en DOCX
    """
    # Dossiers
    sections_dir = Path("sections")
    output_searchable_dir = Path("output_searchable_pdfs")
    output_docx_dir = Path("output_docx")

    # Créer les dossiers de sortie
    output_searchable_dir.mkdir(exist_ok=True)
    output_docx_dir.mkdir(exist_ok=True)

    # Liste des PDFs à traiter
    pdf_files = sorted(sections_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error("Aucun fichier PDF trouvé dans le dossier sections/")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"Début du traitement de {len(pdf_files)} fichiers PDF")
    logger.info(f"{'='*80}\n")

    results_ocr = []
    results_docx = []

    # Traitement de chaque PDF
    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n--- [{i}/{len(pdf_files)}] {pdf_file.name} ---")

        # Noms de fichiers de sortie
        searchable_pdf = output_searchable_dir / f"{pdf_file.stem}_searchable.pdf"
        docx_file = output_docx_dir / f"{pdf_file.stem}.docx"

        # Étape 1: OCR
        logger.info("Étape 1/2: Application de l'OCR...")
        ocr_result = convert_pdf_to_searchable(pdf_file, searchable_pdf)
        results_ocr.append(ocr_result)

        # Étape 2: Conversion DOCX (uniquement si OCR réussie)
        if ocr_result['success']:
            logger.info("Étape 2/2: Conversion en DOCX...")
            docx_result = convert_pdf_to_docx(searchable_pdf, docx_file)
            results_docx.append(docx_result)
        else:
            logger.warning("Conversion DOCX ignorée (échec OCR)")
            results_docx.append({
                'success': False,
                'input_file': str(pdf_file),
                'error': 'OCR failed, skipped DOCX conversion'
            })

    # Rapport final
    logger.info(f"\n{'='*80}")
    logger.info(f"RAPPORT FINAL")
    logger.info(f"{'='*80}\n")

    ocr_success = sum(1 for r in results_ocr if r['success'])
    docx_success = sum(1 for r in results_docx if r['success'])

    logger.info(f"OCR:")
    logger.info(f"  - Succès: {ocr_success}/{len(pdf_files)}")
    logger.info(f"  - Échecs: {len(pdf_files) - ocr_success}/{len(pdf_files)}")

    logger.info(f"\nConversion DOCX:")
    logger.info(f"  - Succès: {docx_success}/{len(pdf_files)}")
    logger.info(f"  - Échecs: {len(pdf_files) - docx_success}/{len(pdf_files)}")

    # Temps total
    total_ocr_time = sum(r.get('processing_time', 0) for r in results_ocr)
    total_docx_time = sum(r.get('processing_time', 0) for r in results_docx)

    logger.info(f"\nTemps de traitement:")
    logger.info(f"  - OCR: {total_ocr_time:.1f}s")
    logger.info(f"  - DOCX: {total_docx_time:.1f}s")
    logger.info(f"  - Total: {total_ocr_time + total_docx_time:.1f}s")

    # Liste des échecs
    ocr_failures = [r for r in results_ocr if not r['success']]
    if ocr_failures:
        logger.info(f"\nÉchecs OCR:")
        for failure in ocr_failures:
            logger.info(f"  - {Path(failure['input_file']).name}: {failure.get('error', 'Unknown error')}")

    docx_failures = [r for r in results_docx if not r['success']]
    if docx_failures:
        logger.info(f"\nÉchecs DOCX:")
        for failure in docx_failures:
            input_name = Path(failure['input_file']).name
            logger.info(f"  - {input_name}: {failure.get('error', 'Unknown error')}")

    logger.info(f"\n{'='*80}\n")

    # Sauvegarder le rapport
    save_report(results_ocr, results_docx, output_docx_dir.parent)


def save_report(results_ocr, results_docx, output_dir):
    """Sauvegarde un rapport détaillé en JSON"""
    import json

    report = {
        'timestamp': datetime.now().isoformat(),
        'ocr_results': results_ocr,
        'docx_results': results_docx,
        'summary': {
            'total_files': len(results_ocr),
            'ocr_success': sum(1 for r in results_ocr if r['success']),
            'docx_success': sum(1 for r in results_docx if r['success']),
            'total_ocr_time': sum(r.get('processing_time', 0) for r in results_ocr),
            'total_docx_time': sum(r.get('processing_time', 0) for r in results_docx),
        }
    }

    report_file = output_dir / f"conversion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Rapport sauvegardé: {report_file}")


if __name__ == "__main__":
    try:
        # Vérifier les dépendances
        import ocrmypdf
        from pdf2docx import Converter

        logger.info("Toutes les dépendances sont installées ✓")

        # Lancer le traitement
        process_all_pdfs()

    except ImportError as e:
        logger.error(f"Dépendance manquante: {e}")
        logger.error("\nInstallez les dépendances avec:")
        logger.error("  pip install ocrmypdf pdf2docx")
        logger.error("\nNote: OCRmyPDF nécessite également Tesseract OCR:")
        logger.error("  - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        logger.error("  - Linux: sudo apt-get install tesseract-ocr tesseract-ocr-fra")
        logger.error("  - macOS: brew install tesseract tesseract-lang")
