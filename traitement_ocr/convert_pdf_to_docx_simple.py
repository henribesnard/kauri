"""
Script simplifié pour convertir les PDFs découpés en documents Word
Utilise pdf2docx uniquement (pas besoin de Tesseract)
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


def convert_pdf_to_docx(input_pdf: Path, output_docx: Path) -> dict:
    """
    Convertit un PDF en document Word (DOCX)
    Le texte sera sélectionnable si le PDF contient du texte extractible

    Args:
        input_pdf: Chemin du PDF d'entrée
        output_docx: Chemin du DOCX de sortie

    Returns:
        Dictionnaire avec les résultats de la conversion
    """
    try:
        from pdf2docx import Converter

        start_time = time.time()

        logger.info(f"Conversion: {input_pdf.name} -> {output_docx.name}")

        # Créer le convertisseur
        cv = Converter(str(input_pdf))

        # Convertir (start=0, end=None = toutes les pages)
        cv.convert(str(output_docx), start=0, end=None)

        # Fermer le convertisseur
        cv.close()

        elapsed_time = time.time() - start_time

        # Vérifier que le fichier a bien été créé
        if output_docx.exists():
            file_size = output_docx.stat().st_size
            logger.info(f"  ✓ Succès: {file_size / 1024:.1f} KB en {elapsed_time:.1f}s")

            return {
                'success': True,
                'input_file': str(input_pdf),
                'output_file': str(output_docx),
                'file_size': file_size,
                'processing_time': elapsed_time,
                'message': 'Conversion réussie'
            }
        else:
            raise Exception("Le fichier de sortie n'a pas été créé")

    except Exception as e:
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"  ✗ Erreur: {e}")
        return {
            'success': False,
            'input_file': str(input_pdf),
            'error': str(e),
            'processing_time': elapsed_time
        }


def process_all_pdfs():
    """
    Traite tous les PDFs découpés et les convertit en DOCX
    """
    # Dossiers
    sections_dir = Path("sections")
    output_docx_dir = Path("output_docx")

    # Créer le dossier de sortie
    output_docx_dir.mkdir(exist_ok=True)

    # Liste des PDFs à traiter
    pdf_files = sorted(sections_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error("Aucun fichier PDF trouvé dans le dossier sections/")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"Début de la conversion de {len(pdf_files)} fichiers PDF vers DOCX")
    logger.info(f"{'='*80}\n")

    results = []

    # Traitement de chaque PDF
    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"[{i}/{len(pdf_files)}] {pdf_file.name}")

        # Nom du fichier de sortie
        docx_file = output_docx_dir / f"{pdf_file.stem}.docx"

        # Conversion
        result = convert_pdf_to_docx(pdf_file, docx_file)
        results.append(result)

        logger.info("")  # Ligne vide pour lisibilité

    # Rapport final
    print_summary(results, pdf_files)

    # Sauvegarder le rapport
    save_report(results, output_docx_dir.parent)


def print_summary(results, pdf_files):
    """Affiche un résumé des conversions"""
    logger.info(f"\n{'='*80}")
    logger.info(f"RAPPORT FINAL")
    logger.info(f"{'='*80}\n")

    success_count = sum(1 for r in results if r['success'])
    failure_count = len(results) - success_count

    logger.info(f"Conversions:")
    logger.info(f"  ✓ Succès: {success_count}/{len(pdf_files)}")
    logger.info(f"  ✗ Échecs: {failure_count}/{len(pdf_files)}")

    # Temps total
    total_time = sum(r.get('processing_time', 0) for r in results)
    logger.info(f"\nTemps de traitement:")
    logger.info(f"  - Total: {total_time:.1f}s")
    logger.info(f"  - Moyen: {total_time / len(results):.1f}s par fichier")

    # Taille totale
    total_size = sum(r.get('file_size', 0) for r in results if r['success'])
    logger.info(f"\nTaille totale des fichiers DOCX: {total_size / 1024 / 1024:.2f} MB")

    # Liste des échecs
    failures = [r for r in results if not r['success']]
    if failures:
        logger.info(f"\nÉchecs détaillés:")
        for failure in failures:
            filename = Path(failure['input_file']).name
            error = failure.get('error', 'Erreur inconnue')
            logger.info(f"  - {filename}: {error}")

    # Liste des succès
    successes = [r for r in results if r['success']]
    if successes:
        logger.info(f"\nFichiers convertis avec succès:")
        for success in successes:
            filename = Path(success['output_file']).name
            size = success['file_size'] / 1024
            time_taken = success['processing_time']
            logger.info(f"  - {filename} ({size:.1f} KB, {time_taken:.1f}s)")

    logger.info(f"\n{'='*80}\n")


def save_report(results, output_dir):
    """Sauvegarde un rapport détaillé en JSON"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'conversion_results': results,
        'summary': {
            'total_files': len(results),
            'success_count': sum(1 for r in results if r['success']),
            'failure_count': sum(1 for r in results if not r['success']),
            'total_processing_time': sum(r.get('processing_time', 0) for r in results),
            'total_output_size': sum(r.get('file_size', 0) for r in results if r['success']),
        }
    }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = output_dir / f"conversion_report_{timestamp}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Rapport détaillé sauvegardé: {report_file}")


def test_single_file():
    """Teste la conversion sur un seul fichier pour debug"""
    sections_dir = Path("sections")
    output_docx_dir = Path("output_docx")
    output_docx_dir.mkdir(exist_ok=True)

    # Prendre le premier PDF trouvé
    pdf_files = list(sections_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("Aucun fichier PDF trouvé")
        return

    test_pdf = pdf_files[0]
    test_docx = output_docx_dir / f"test_{test_pdf.stem}.docx"

    logger.info(f"Test de conversion sur: {test_pdf.name}")
    result = convert_pdf_to_docx(test_pdf, test_docx)

    if result['success']:
        logger.info("✓ Test réussi!")
        logger.info(f"Fichier créé: {result['output_file']}")
    else:
        logger.error("✗ Test échoué!")
        logger.error(f"Erreur: {result.get('error', 'Unknown')}")


if __name__ == "__main__":
    try:
        # Vérifier que pdf2docx est installé
        from pdf2docx import Converter
        logger.info("pdf2docx est installé ✓\n")

        # Demander à l'utilisateur s'il veut un test ou conversion complète
        import sys

        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            logger.info("Mode TEST - Conversion d'un seul fichier\n")
            test_single_file()
        else:
            logger.info("Mode COMPLET - Conversion de tous les fichiers\n")
            process_all_pdfs()

    except ImportError as e:
        logger.error(f"Dépendance manquante: {e}")
        logger.error("\nInstallez pdf2docx avec:")
        logger.error("  pip install pdf2docx")
