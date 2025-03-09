import os
from PIL import Image

def jpeg_to_pdf_pillow(image_path):
    # Pobranie nazwy pliku bez rozszerzenia
    base_name = os.path.splitext(image_path)[0]
    pdf_path = f"{base_name}_converted.pdf"

    # Konwersja obrazu do PDF
    img = Image.open(image_path)
    img.convert("RGB").save(pdf_path)

    print(f"Plik zapisany jako: {pdf_path}")
