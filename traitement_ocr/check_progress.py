"""
Script pour vérifier la progression de la conversion
"""
from pathlib import Path
import json

def check_progress():
    sections_dir = Path("sections")
    output_dir = Path("output_docx")

    # Compter les fichiers
    total_pdfs = len(list(sections_dir.glob("*.pdf")))
    converted_docx = len([f for f in output_dir.glob("*.docx") if not f.name.startswith("test_")])

    print(f"Progression de la conversion :")
    print(f"  Total à convertir : {total_pdfs} fichiers")
    print(f"  Déjà convertis    : {converted_docx} fichiers")
    print(f"  Restants          : {total_pdfs - converted_docx} fichiers")
    print(f"  Pourcentage       : {(converted_docx / total_pdfs * 100):.1f}%")

    print(f"\nFichiers convertis :")
    for docx in sorted(output_dir.glob("*.docx")):
        if not docx.name.startswith("test_"):
            size_mb = docx.stat().st_size / 1024 / 1024
            print(f"  ✓ {docx.name} ({size_mb:.1f} MB)")

    print(f"\nFichiers en attente :")
    converted_names = {f.stem for f in output_dir.glob("*.docx")}
    for pdf in sorted(sections_dir.glob("*.pdf")):
        if pdf.stem not in converted_names:
            print(f"  ○ {pdf.name}")

if __name__ == "__main__":
    check_progress()
