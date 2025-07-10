from PIL import Image
import fitz
import os

def convert_file_logic(selected_file, output_format):
    file_extension = os.path.splitext(selected_file)[1].lower()
    output_path = os.path.splitext(selected_file)[0] + f".{output_format}"

    if file_extension in [".jpg", ".jpeg", ".png", ".webp"] and output_format == "pdf":
        img = Image.open(selected_file).convert("RGB")
        img.save(output_path)
        return output_path

    elif file_extension == ".pdf" and output_format in ["jpg", "png", "webp"]:
        pdf_document = fitz.open(selected_file)
        output_paths = []
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            mat = fitz.Matrix(3.0, 3.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            output_path = os.path.splitext(selected_file)[0] + f"_page{page_num + 1}.{output_format}"
            img.save(output_path)
            output_paths.append(output_path)
        return output_paths

    elif file_extension in [".jpg", ".jpeg"] and output_format in ["png", "webp"]:
        img = Image.open(selected_file).convert("RGBA")
        img.save(output_path)
        return output_path

    elif file_extension == ".png" and output_format in ["jpg", "webp"]:
        img = Image.open(selected_file).convert("RGB")
        img.save(output_path, "JPEG" if output_format == "jpg" else "WEBP")
        return output_path

    elif file_extension == ".webp" and output_format in ["jpg", "png"]:
        img = Image.open(selected_file).convert("RGB")
        img.save(output_path, "JPEG" if output_format == "jpg" else "PNG")
        return output_path

    else:
        raise ValueError("Unsupported conversion.")
