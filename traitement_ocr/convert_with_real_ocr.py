"""
Script pour convertir les PDFs en documents avec VRAI texte sélectionnable
Utilise OCRmyPDF avec Tesseract pour créer une couche OCR
"""
import os
import logging
from pathlib import Path
import time
from datetime import datetime
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_tesseract():
    """Configure le chemin Tesseract pour Windows"""
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe",
    ]

    for path in possible_paths:
        if Path(path).exists():
            os.environ['TESSDATA_PREFIX'] = str(Path(path).parent / 'tessdata')
            logger.info(f"✓ Tesseract trouvé: {path}")
            return True

    logger.error("✗ Tesseract non trouvé!")
    logger.error("Veuillez installer Tesseract depuis:")
    logger.error("https://github.com/UB-Mannheim/tesseract/wiki")
    return False


def convert_pdf_to_searchable(input_pdf: Path, output_pdf: Path) -> dict:
    """
    Applique l'OCR à un PDF pour rendre le texte sélectionnable

    Args:
        input_pdf: PDF d'entrée (image scannée)
        output_pdf: PDF de sortie avec couche OCR

    Returns:
        Résultat de la conversion
    """
    try:
        import ocrmypdf

        start_time = time.time()

        logger.info(f"OCR en cours: {input_pdf.name}")
        logger.info(f"  Langues: Français + Anglais")

        # Configuration OCRmyPDF
        result = ocrmypdf.ocr(
            input_file=str(input_pdf),
            output_file=str(output_pdf),
            language=['fra', 'eng'],  # Français et Anglais
            output_type='pdf',  # PDF standard (pas PDF/A)
            optimize=1,  # Optimisation légère
            deskew=True,  # Correction inclinaison
            clean=True,  # Nettoyage avant OCR
            force_ocr=False,  # Ne pas refaire OCR si déjà présent
            skip_text=True,  # Sauter pages avec texte
            rotate_pages=True,  # Rotation auto
            remove_background=False,  # Garder fond original
            jobs=2,  # Traitement parallèle (2 cœurs)
            progress_bar=False,  # Pas de barre de progression
            verbose=1,  # Mode verbeux
        )

        elapsed_time = time.time() - start_time

        if result == 0 and output_pdf.exists():
            file_size = output_pdf.stat().st_size
            logger.info(f"  ✓ Succès: {file_size / 1024 / 1024:.1f} MB en {elapsed_time:.1f}s")

            return {
                'success': True,
                'input_file': str(input_pdf),
                'output_file': str(output_pdf),
                'file_size': file_size,
                'processing_time': elapsed_time,
                'message': 'OCR appliqué avec succès'
            }
        else:
            raise Exception(f"OCRmyPDF a retourné le code {result}")

    except Exception as e:
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"  ✗ Erreur: {e}")
        return {
            'success': False,
            'input_file': str(input_pdf),
            'error': str(e),
            'processing_time': elapsed_time
        }


def convert_searchable_pdf_to_docx(input_pdf: Path, output_docx: Path) -> dict:
    """
    Convertit un PDF avec OCR en DOCX
    Maintenant le texte sera sélectionnable car le PDF a une couche OCR
    """
    try:
        from pdf2docx import Converter

        start_time = time.time()

        logger.info(f"Conversion DOCX: {input_pdf.name}")

        cv = Converter(str(input_pdf))
        cv.convert(str(output_docx), start=0, end=None)
        cv.close()

        elapsed_time = time.time() - start_time

        if output_docx.exists():
            file_size = output_docx.stat().st_size
            logger.info(f"  ✓ DOCX créé: {file_size / 1024 / 1024:.1f} MB en {elapsed_time:.1f}s")

            return {
                'success': True,
                'input_file': str(input_pdf),
                'output_file': str(output_docx),
                'file_size': file_size,
                'processing_time': elapsed_time,
                'message': 'Conversion DOCX réussie'
            }
        else:
            raise Exception("Fichier DOCX non créé")

    except Exception as e:
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"  ✗ Erreur DOCX: {e}")
        return {
            'success': False,
            'input_file': str(input_pdf),
            'error': str(e),
            'processing_time': elapsed_time
        }


def process_all_pdfs():
    """
    Traite tous les PDFs:
    1. Applique OCR pour créer une couche de texte (PDF searchable)
    2. Convertit en DOCX avec texte sélectionnable
    """
    # Vérifier Tesseract
    if not setup_tesseract():
        logger.error("\n⚠️  Installation de Tesseract requise!")
        logger.error("   Téléchargez depuis: https://github.com/UB-Mannheim/tesseract/wiki")
        logger.error("   Installez avec les langues French (fra) et English (eng)")
        return

    # Dossiers
    sections_dir = Path("sections")
    output_searchable_dir = Path("output_searchable_pdfs")
    output_docx_dir = Path("output_docx_with_ocr")

    # Créer dossiers
    output_searchable_dir.mkdir(exist_ok=True)
    output_docx_dir.mkdir(exist_ok=True)

    # Liste des PDFs
    pdf_files = sorted(sections_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error("Aucun fichier PDF dans sections/")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"Conversion avec OCR de {len(pdf_files)} fichiers")
    logger.info(f"{'='*80}\n")

    results_ocr = []
    results_docx = []

    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
        logger.info(f"{'='*80}")

        searchable_pdf = output_searchable_dir / f"{pdf_file.stem}_searchable.pdf"
        docx_file = output_docx_dir / f"{pdf_file.stem}.docx"

        # Étape 1: Appliquer OCR
        logger.info("\nÉtape 1/2: Application OCR (Tesseract)...")
        ocr_result = convert_pdf_to_searchable(pdf_file, searchable_pdf)
        results_ocr.append(ocr_result)

        # Étape 2: Conversion DOCX
        if ocr_result['success']:
            logger.info("\nÉtape 2/2: Conversion en DOCX...")
            docx_result = convert_searchable_pdf_to_docx(searchable_pdf, docx_file)
            results_docx.append(docx_result)
        else:
            logger.warning("\n⚠️  Conversion DOCX ignorée (échec OCR)")
            results_docx.append({
                'success': False,
                'input_file': str(pdf_file),
                'error': 'OCR failed'
            })

    # Rapport final
    print_summary(results_ocr, results_docx, len(pdf_files))
    save_report(results_ocr, results_docx, output_docx_dir.parent)


def print_summary(results_ocr, results_docx, total):
    """Affiche le résumé"""
    logger.info(f"\n{'='*80}")
    logger.info(f"RAPPORT FINAL")
    logger.info(f"{'='*80}\n")

    ocr_success = sum(1 for r in results_ocr if r['success'])
    docx_success = sum(1 for r in results_docx if r['success'])

    logger.info(f"OCR (Tesseract):")
    logger.info(f"  ✓ Succès: {ocr_success}/{total}")
    logger.info(f"  ✗ Échecs: {total - ocr_success}/{total}")

    logger.info(f"\nConversion DOCX:")
    logger.info(f"  ✓ Succès: {docx_success}/{total}")
    logger.info(f"  ✗ Échecs: {total - docx_success}/{total}")

    # Temps
    total_ocr_time = sum(r.get('processing_time', 0) for r in results_ocr)
    total_docx_time = sum(r.get('processing_time', 0) for r in results_docx)

    logger.info(f"\nTemps de traitement:")
    logger.info(f"  OCR:   {total_ocr_time / 60:.1f} minutes")
    logger.info(f"  DOCX:  {total_docx_time / 60:.1f} minutes")
    logger.info(f"  Total: {(total_ocr_time + total_docx_time) / 60:.1f} minutes")

    # Échecs
    failures = [r for r in results_ocr if not r['success']]
    if failures:
        logger.info(f"\nÉchecs OCR:")
        for f in failures:
            logger.info(f"  - {Path(f['input_file']).name}: {f.get('error', 'Unknown')}")

    logger.info(f"\n{'='*80}\n")


def save_report(results_ocr, results_docx, output_dir):
    """Sauvegarde le rapport"""
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

    report_file = output_dir / f"ocr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Rapport sauvegardé: {report_file}")


def test_single_file():
    """Test sur un seul fichier"""
    if not setup_tesseract():
        return

    sections_dir = Path("sections")
    output_searchable_dir = Path("output_searchable_pdfs")
    output_docx_dir = Path("output_docx_with_ocr")

    output_searchable_dir.mkdir(exist_ok=True)
    output_docx_dir.mkdir(exist_ok=True)

    pdf_files = list(sections_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("Aucun PDF trouvé")
        return

    test_pdf = pdf_files[0]
    searchable_pdf = output_searchable_dir / f"test_{test_pdf.stem}_searchable.pdf"
    docx_file = output_docx_dir / f"test_{test_pdf.stem}.docx"

    logger.info(f"Test OCR sur: {test_pdf.name}\n")

    # OCR
    logger.info("Étape 1: Application OCR...")
    ocr_result = convert_pdf_to_searchable(test_pdf, searchable_pdf)

    if ocr_result['success']:
        logger.info("\n✓ OCR réussi!")

        # DOCX
        logger.info("\nÉtape 2: Conversion DOCX...")
        docx_result = convert_searchable_pdf_to_docx(searchable_pdf, docx_file)

        if docx_result['success']:
            logger.info("\n✓ Test complet réussi!")
            logger.info(f"PDF avec OCR: {searchable_pdf}")
            logger.info(f"DOCX: {docx_file}")
            logger.info("\n⚠️  Ouvrez le fichier DOCX et vérifiez que le texte est sélectionnable!")
        else:
            logger.error("\n✗ Échec conversion DOCX")
    else:
        logger.error("\n✗ Échec OCR")


if __name__ == "__main__":
    import sys

    try:
        # Vérifier les dépendances
        import ocrmypdf
        from pdf2docx import Converter

        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            logger.info("Mode TEST - Un seul fichier\n")
            test_single_file()
        else:
            logger.info("Mode COMPLET - Tous les fichiers\n")
            process_all_pdfs()

    except ImportError as e:
        logger.error(f"Dépendance manquante: {e}")
        logger.error("\nInstallez avec: pip install ocrmypdf pdf2docx")
