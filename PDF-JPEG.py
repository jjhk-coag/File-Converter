import subprocess
import argparse
import logging
import sys
import os

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

# REQUIREMENTS_FILE_NAME = "apprequirements.txt"

# def install_requirements():
#     try:
#         from PIL import Image
#         import tkinter as tk
#         from tkinterdnd2 import DND_FILES, TkinterDnD
#         from tkinter import filedialog, messagebox
#         import fitz
#         logging.info("All required libraries are already installed.")
#     except ImportError:
#         logging.info("Missing Libraries. Installing...")
#         if not os.path.exists(REQUIREMENTS_FILE_NAME):
#             logging.error(f"File {REQUIREMENTS_FILE_NAME} not found.")
#             sys.exit(1)
#         try:
#             subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE_NAME])
#             logging.info("All required libraries installed.")
#         except subprocess.CalledProcessError:
#             logging.error("Failed to install required libraries.")
#             sys.exit(1)
            
# install_requirements()

from PIL import Image
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog, messagebox
import fitz


def convert_jpeg_to_pdf(files):
    for file in files:
        try:
            img = Image.open(file)
            img = img.convert("RGB")
            output_path = os.path.splitext(file)[0] + ".pdf"
            img.save(output_path)
            messagebox.showinfo("Success", f"Saved: {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert {file}: {e}")

def convert_pdf_to_jpeg(files):
    for file in files:
        try:
            pdf_document = fitz.open(file)
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                output_path = os.path.splitext(file)[0] + f"_page{page_num + 1}.jpg"
                img.save(output_path)
            messagebox.showinfo("Success", f"Converted PDF to JPG: {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert {file}: {e}")

def open_file_dialog(conversion_type):
    file_types = [("Image Files", "*.jpg;*.jpeg")] if conversion_type == "jpeg_to_pdf" else [("PDF Files", "*.pdf")]
    files = filedialog.askopenfilenames(title="Select Files", filetypes=file_types)
    if files:
        if conversion_type == "jpeg_to_pdf":
            convert_jpeg_to_pdf(files)
        else:
            convert_pdf_to_jpeg(files)

def on_drop(event, conversion_type=None):
    files = root.tk.splitlist(event.data)
    if conversion_type == "jpeg_to_pdf" and all(file.lower().endswith(".jpg") or file.lower().endswith(".jpeg") for file in files):
        convert_jpeg_to_pdf(files)
    elif conversion_type == "pdf_to_jpeg" and all(file.lower().endswith(".pdf") for file in files):
        convert_pdf_to_jpeg(files)
    else:
        messagebox.showwarning("Warning", "Invalid file type for this section.")

        
def on_enter(event):
    event.widget.config(bg="#1DB954", fg="#121212", cursor="hand2")

def on_leave(event):
    event.widget.config(bg="#121212", fg="#1DB954", cursor="arrow")
    event.widget.config(highlightbackground="#1DB954", highlightthickness=2, cursor="hand2")
    event.widget.config(highlightthickness=0, cursor="", bd=2, relief="flat")

root = TkinterDnD.Tk()
root.title("JPEG <-> PDF Converter")
root.geometry("400x400")
root.configure(bg="#212121")

label = tk.Label(root, text="Drag & Drop files or use buttons to open file explorer", fg="#1DB954", bg="#212121", padx=10, pady=10)
label.pack()

# JPEG -> PDF
drop_area_jpeg_to_pdf = tk.Label(root, text="Drag JPEG files here to convert to PDF", fg="#1DB954", bg="#121212", width=50, height=6)
drop_area_jpeg_to_pdf.pack(pady=5)
drop_area_jpeg_to_pdf.drop_target_register(DND_FILES)
drop_area_jpeg_to_pdf.dnd_bind("<<Drop>>", lambda event, ct="jpeg_to_pdf": on_drop(event, ct))

btn_jpeg_to_pdf = tk.Button(root, text="Convert JPEG to PDF", command=lambda: open_file_dialog("jpeg_to_pdf"), bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5, highlightthickness=0, highlightbackground="#1DB954", borderwidth=2, bd=2)
btn_jpeg_to_pdf.pack(pady=5)
btn_jpeg_to_pdf.bind("<Enter>", on_enter)
btn_jpeg_to_pdf.bind("<Leave>", on_leave)

# PDF -> JPEG
drop_area_pdf_to_jpeg = tk.Label(root, text="Drag PDF files here to convert to JPEG", fg="#1DB954", bg="#121212", width=50, height=6)
drop_area_pdf_to_jpeg.pack(pady=5)
drop_area_pdf_to_jpeg.drop_target_register(DND_FILES)
drop_area_pdf_to_jpeg.dnd_bind("<<Drop>>", lambda event, ct="pdf_to_jpeg": on_drop(event, ct))

btn_pdf_to_jpeg = tk.Button(root, text="Convert PDF to JPEG", command=lambda: open_file_dialog("pdf_to_jpeg"), bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5, highlightthickness=0, highlightbackground="#1DB954", borderwidth=2, bd=2)
btn_pdf_to_jpeg.pack(pady=5)
btn_pdf_to_jpeg.bind("<Enter>", on_enter)
btn_pdf_to_jpeg.bind("<Leave>", on_leave)

root.mainloop()