import PyPDF2
import os

def split_pdf(input_pdf, output_dir):
    """
    Découpe le PDF AUPSRVE-2023_fr selon les spécifications
    """
    sections = [
        ("Preambule", 0, 17),
        ("Livre_1", 18, 25),
        ("Livre_2_titre_1", 25, 33),
        ("Livre_2_titre_2", 33, 45),
        ("Livre_2_titre_3", 45, 62),
        ("Livre_2_titre_4", 62, 69),
        ("Livre_2_titre_5", 69, 78),
        ("Livre_2_titre_6", 78, 81),
        ("Livre_2_titre_7", 81, 94),
        ("Livre_2_titre_8", 94, 113),
        ("Livre_2_titre_9", 113, 117)
    ]

    # Ouvrir le PDF source
    with open(input_pdf, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        total_pages = len(pdf_reader.pages)
        print(f"PDF source: {total_pages} pages")

        # Créer le dossier de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)

        # Créer chaque section
        for section_name, start_page, end_page in sections:
            pdf_writer = PyPDF2.PdfWriter()

            # Les numéros de pages sont 0-indexés dans PyPDF2
            # start_page est la première page (incluse)
            # end_page est la dernière page (incluse)
            for page_num in range(start_page, end_page + 1):
                if page_num < total_pages:
                    pdf_writer.add_page(pdf_reader.pages[page_num])

            # Sauvegarder le PDF de section
            output_filename = os.path.join(output_dir, f"{section_name}.pdf")
            with open(output_filename, 'wb') as output_file:
                pdf_writer.write(output_file)

            pages_count = end_page - start_page + 1
            print(f"Créé: {section_name}.pdf (pages {start_page}-{end_page}, {pages_count} pages)")

if __name__ == "__main__":
    input_pdf = "AUPSRVE-2023_fr.pdf"
    output_dir = "sections"

    print(f"Découpage du PDF: {input_pdf}")
    split_pdf(input_pdf, output_dir)
    print("\nDécoupage terminé!")
