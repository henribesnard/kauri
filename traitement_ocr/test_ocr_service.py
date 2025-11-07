"""
Script client pour tester le service kauri_ocr_service
Envoie les PDFs découpés au service et récupère les résultats
"""
import requests
import time
import json
from pathlib import Path
from datetime import datetime
import logging
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OCR_SERVICE_URL = "http://localhost:8003/api/v1"
TENANT_ID = str(uuid.uuid4())  # ID unique pour ce test
USER_ID = str(uuid.uuid4())


def check_service_health():
    """Vérifie que le service OCR est actif"""
    try:
        response = requests.get(f"{OCR_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info("✓ Service OCR actif")
            return True
        else:
            logger.error(f"✗ Service répond avec status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("✗ Service OCR non accessible (connexion refusée)")
        return False
    except Exception as e:
        logger.error(f"✗ Erreur lors du health check: {e}")
        return False


def submit_pdf_for_ocr(pdf_path: Path):
    """
    Soumet un PDF au service OCR

    Returns:
        dict avec document_id et job_id si succès
    """
    try:
        logger.info(f"Envoi de {pdf_path.name} au service OCR...")

        # Préparer les données
        data = {
            "tenant_id": TENANT_ID,
            "user_id": USER_ID,
            "source_document_id": str(uuid.uuid4()),
            "filename": pdf_path.name,
            "file_path": f"/app/traitement_ocr/sections/{pdf_path.name}",
            "mime_type": "application/pdf",
            "priority": 5,
            "metadata": {
                "source": "test_ocr_service",
                "original_file": str(pdf_path)
            }
        }

        # Envoyer la requête
        response = requests.post(
            f"{OCR_SERVICE_URL}/ocr/process",
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"  ✓ Document soumis: {result['document_id']}")
            logger.info(f"    Status: {result['status']}")
            logger.info(f"    Message: {result['message']}")
            return result
        else:
            logger.error(f"  ✗ Erreur HTTP {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"  ✗ Erreur lors de la soumission: {e}")
        return None


def get_document_status(document_id: str):
    """Récupère le status d'un document"""
    try:
        response = requests.get(
            f"{OCR_SERVICE_URL}/ocr/document/{document_id}/status",
            params={"tenant_id": TENANT_ID},
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Impossible de récupérer le status: {response.status_code}")
            return None

    except Exception as e:
        logger.warning(f"Erreur lors de la récupération du status: {e}")
        return None


def get_document_results(document_id: str):
    """Récupère les résultats complets d'un document"""
    try:
        response = requests.get(
            f"{OCR_SERVICE_URL}/ocr/document/{document_id}",
            params={"tenant_id": TENANT_ID},
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Impossible de récupérer les résultats: {response.status_code}")
            return None

    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des résultats: {e}")
        return None


def download_searchable_pdf(document_id: str, output_path: Path):
    """Télécharge le PDF avec couche OCR"""
    try:
        response = requests.get(
            f"{OCR_SERVICE_URL}/ocr/document/{document_id}/searchable-pdf",
            params={"tenant_id": TENANT_ID},
            timeout=30,
            stream=True
        )

        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"  ✓ PDF téléchargé: {output_path}")
            return True
        else:
            logger.warning(f"  ✗ Impossible de télécharger le PDF: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"  ✗ Erreur téléchargement: {e}")
        return False


def wait_for_processing(document_id: str, max_wait_seconds=300, check_interval=5):
    """
    Attend que le document soit traité

    Returns:
        True si succès, False si échec ou timeout
    """
    logger.info(f"  Attente du traitement (max {max_wait_seconds}s)...")
    start_time = time.time()

    while (time.time() - start_time) < max_wait_seconds:
        status = get_document_status(document_id)

        if status:
            current_status = status['status']

            if current_status == 'COMPLETED':
                logger.info(f"  ✓ Traitement terminé!")
                logger.info(f"    Temps: {status.get('processing_time_ms', 0) / 1000:.1f}s")
                logger.info(f"    Confiance: {status.get('confidence_score', 0):.2f}")
                logger.info(f"    Qualité: {status.get('quality_score', 0):.2f}")
                return True

            elif current_status == 'FAILED':
                logger.error(f"  ✗ Traitement échoué: {status.get('error_message', 'Unknown error')}")
                return False

            elif current_status in ['QUEUED', 'PROCESSING']:
                elapsed = time.time() - start_time
                logger.info(f"    Status: {current_status} ({elapsed:.0f}s écoulées)")

        time.sleep(check_interval)

    logger.error(f"  ✗ Timeout après {max_wait_seconds}s")
    return False


def test_single_file():
    """Test avec un seul fichier"""
    logger.info("\n" + "="*80)
    logger.info("TEST SUR UN SEUL FICHIER")
    logger.info("="*80 + "\n")

    # Vérifier le service
    if not check_service_health():
        logger.error("Service OCR non disponible!")
        return

    # Trouver un PDF
    sections_dir = Path("sections")
    pdf_files = list(sections_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error("Aucun PDF trouvé dans sections/")
        return

    test_pdf = pdf_files[0]
    logger.info(f"Test avec: {test_pdf.name}\n")

    # Soumettre au service
    result = submit_pdf_for_ocr(test_pdf)

    if not result:
        logger.error("Échec de la soumission")
        return

    document_id = result['document_id']

    # Attendre le traitement
    if wait_for_processing(document_id, max_wait_seconds=300):
        # Récupérer les résultats
        logger.info("\nRécupération des résultats...")
        doc_results = get_document_results(document_id)

        if doc_results:
            logger.info(f"\nRésultats:")
            logger.info(f"  Pages: {doc_results.get('page_count', 0)}")
            logger.info(f"  Mots: {doc_results.get('word_count', 0)}")
            logger.info(f"  Type: {doc_results.get('document_type', 'unknown')}")

            # Télécharger le PDF avec OCR
            output_dir = Path("output_from_service")
            output_dir.mkdir(exist_ok=True)

            output_pdf = output_dir / f"test_{test_pdf.stem}_searchable.pdf"

            logger.info(f"\nTéléchargement du PDF avec OCR...")
            if download_searchable_pdf(document_id, output_pdf):
                logger.info(f"\n✓ Test réussi!")
                logger.info(f"  Fichier: {output_pdf}")
                logger.info(f"\n⚠️  Ouvrez le PDF et vérifiez que le texte est sélectionnable!")
            else:
                logger.warning("PDF searchable non disponible")
    else:
        logger.error("Échec du traitement")


def process_all_pdfs():
    """Traite tous les PDFs découpés"""
    logger.info("\n" + "="*80)
    logger.info("TRAITEMENT DE TOUS LES FICHIERS")
    logger.info("="*80 + "\n")

    # Vérifier le service
    if not check_service_health():
        logger.error("Service OCR non disponible!")
        logger.error("\nDémarrez le service avec:")
        logger.error("  cd backend/kauri_ocr_service")
        logger.error("  docker-compose up -d")
        return

    # Lister les PDFs
    sections_dir = Path("sections")
    pdf_files = sorted(sections_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error("Aucun PDF dans sections/")
        return

    logger.info(f"Nombre de fichiers à traiter: {len(pdf_files)}\n")

    # Soumettre tous les fichiers
    submissions = []

    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
        result = submit_pdf_for_ocr(pdf_file)

        if result:
            submissions.append({
                'filename': pdf_file.name,
                'document_id': result['document_id'],
                'submitted_at': datetime.now()
            })
        else:
            submissions.append({
                'filename': pdf_file.name,
                'document_id': None,
                'submitted_at': datetime.now(),
                'error': 'Submission failed'
            })

        logger.info("")

    # Attendre que tous soient traités
    logger.info("\n" + "="*80)
    logger.info("ATTENTE DES RÉSULTATS")
    logger.info("="*80 + "\n")

    output_dir = Path("output_from_service")
    output_dir.mkdir(exist_ok=True)

    results = []

    for i, submission in enumerate(submissions, 1):
        filename = submission['filename']
        document_id = submission.get('document_id')

        logger.info(f"[{i}/{len(submissions)}] {filename}")

        if not document_id:
            logger.error("  ✗ Pas de document_id (soumission échouée)")
            results.append({**submission, 'success': False})
            continue

        # Attendre le traitement
        if wait_for_processing(document_id, max_wait_seconds=600):
            # Télécharger le PDF
            output_pdf = output_dir / f"{Path(filename).stem}_searchable.pdf"

            if download_searchable_pdf(document_id, output_pdf):
                results.append({
                    **submission,
                    'success': True,
                    'output_file': str(output_pdf)
                })
            else:
                results.append({
                    **submission,
                    'success': False,
                    'error': 'Download failed'
                })
        else:
            results.append({
                **submission,
                'success': False,
                'error': 'Processing failed or timeout'
            })

        logger.info("")

    # Rapport final
    print_final_report(results)
    save_results_report(results, output_dir.parent)


def print_final_report(results):
    """Affiche le rapport final"""
    logger.info("\n" + "="*80)
    logger.info("RAPPORT FINAL")
    logger.info("="*80 + "\n")

    total = len(results)
    success = sum(1 for r in results if r.get('success', False))
    failed = total - success

    logger.info(f"Total: {total} fichiers")
    logger.info(f"  ✓ Succès: {success}")
    logger.info(f"  ✗ Échecs: {failed}")

    if failed > 0:
        logger.info(f"\nÉchecs:")
        for r in results:
            if not r.get('success', False):
                logger.info(f"  - {r['filename']}: {r.get('error', 'Unknown error')}")

    logger.info("\n" + "="*80 + "\n")


def save_results_report(results, output_dir):
    """Sauvegarde le rapport en JSON"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'tenant_id': TENANT_ID,
        'service_url': OCR_SERVICE_URL,
        'results': results,
        'summary': {
            'total': len(results),
            'success': sum(1 for r in results if r.get('success', False)),
            'failed': sum(1 for r in results if not r.get('success', False))
        }
    }

    report_file = output_dir / f"service_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Rapport sauvegardé: {report_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_single_file()
    else:
        process_all_pdfs()
