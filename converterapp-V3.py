import subprocess
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

REQUIREMENTS_FILE_NAME = "apprequirements.txt"

def install_requirements():
    try:
        from PIL import Image
        import tkinter as tk
        from tkinterdnd2 import DND_FILES, TkinterDnD
        from tkinter import filedialog, messagebox
        import fitz
        logging.info("All required libraries are already installed.")
    except ImportError:
        logging.info("Missing Libraries. Installing...")
        if not os.path.exists(REQUIREMENTS_FILE_NAME):
            logging.error(f"File {REQUIREMENTS_FILE_NAME} not found.")
            sys.exit(1)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE_NAME])
            logging.info("All required libraries installed.")
        except subprocess.CalledProcessError:
            logging.error("Failed to install required libraries.")
            sys.exit(1)
            
install_requirements()
from PIL import Image
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog, messagebox
import fitz

selected_file = None

def update_buttons():
    global selected_file
    btn_to_png.config(state="disabled", bg="#555555")
    btn_to_jpeg.config(state="disabled", bg="#555555")
    btn_to_webp.config(state="disabled", bg="#555555")
    btn_to_pdf.config(state="disabled", bg="#555555")
    
    if selected_file:
        file_extension = os.path.splitext(selected_file)[1].lower()
        
        if file_extension in [".jpg", ".jpeg"]:
            btn_to_jpeg.config(state="disabled", bg="#555555")
            btn_to_png.config(state="normal", bg="#121212")
            btn_to_webp.config(state="normal", bg="#121212")
            btn_to_pdf.config(state="normal", bg="#121212")
        elif file_extension == ".png":
            btn_to_jpeg.config(state="normal", bg="#121212")
            btn_to_png.config(state="disabled", bg="#555555")
            btn_to_webp.config(state="normal", bg="#121212")
            btn_to_pdf.config(state="normal", bg="#121212")
        elif file_extension == ".webp":
            btn_to_jpeg.config(state="normal", bg="#121212")
            btn_to_png.config(state="normal", bg="#121212")
            btn_to_webp.config(state="disabled", bg="#555555")
            btn_to_pdf.config(state="normal", bg="#121212")
        elif file_extension == ".pdf":
            btn_to_jpeg.config(state="normal", bg="#121212")
            btn_to_png.config(state="normal", bg="#121212")
            btn_to_webp.config(state="normal", bg="#121212")
            btn_to_pdf.config(state="disabled", bg="#555555")
            
def convert_file(output_format):
    global selected_file
    if not selected_file:
        messagebox.showwarning("Warning", "No file selected. Please drag and drop a file.")
        return
    
    try:
        file_extension = os.path.splitext(selected_file)[1].lower()
        output_path = os.path.splitext(selected_file)[0] + f".{output_format}"
        
        if file_extension in [".jpg", ".jpeg", ".png", ".webp"] and output_format == "pdf":
            img = Image.open(selected_file).convert("RGB")
            img.save(output_path)
            
        elif file_extension == ".pdf" and output_format in ["jpg", "png", "webp"]:
            pdf_document = fitz.open(selected_file)
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                zoom = 3.0  # 3x = ~300 DPI
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                output_path = os.path.splitext(selected_file)[0] + f"_page{page_num + 1}.{output_format}"
                img.save(output_path)
                
        elif file_extension in [".jpg", ".jpeg"] and output_format in ["png", "webp"]:
            img = Image.open(selected_file).convert("RGBA")
            img.save(output_path)
            
        elif file_extension == ".png" and output_format in ["jpg", "webp"]:
            img = Image.open(selected_file).convert("RGB")
            img.save(output_path, "JPEG" if output_format == "jpg" else "WEBP")
            
        elif file_extension == ".webp" and output_format in ["jpg", "png"]:
            img = Image.open(selected_file).convert("RGB")
            img.save(output_path, "JPEG" if output_format == "jpg" else "PNG")
            
        else:
            messagebox.showerror("Error", "Unsupported conversion.")
            return
        
        messagebox.showinfo("Success", f"Converted file saved: {output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Conversion failed: {e}")

def convert_images_to_pdf(selected_files):
    if not selected_files:
        messagebox.showwarning("Warning", "No image files selected.")
        return

    # 
    image_files = [f for f in selected_files if os.path.splitext(f)[1].lower() in [".jpg", ".jpeg", ".png", ".webp"]]

    if not image_files:
        messagebox.showerror("Error", "No supported image files (.jpg, .png, .webp) selected.")
        return

    try:
        # 
        images = [Image.open(f).convert("RGB") for f in image_files]

        # 
        output_path = os.path.splitext(image_files[0])[0] + "_merged.pdf"

        if len(images) == 1:
            images[0].save(output_path, format="PDF")
        else:
            images[0].save(output_path, save_all=True, append_images=images[1:], format="PDF")

        messagebox.showinfo("Success", f"Created PDF with {len(images)} page(s):\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create PDF: {e}")

def on_drop(event):
    global selected_file
    files = root.tk.splitlist(event.data)
    if files:
        selected_file = files[0]
        drop_area.config(text=f"Selected File:\n{os.path.basename(selected_file)}")
        update_buttons()

def open_file_dialog():
    global selected_file
    file_types = [("All Supported Files", "*.jpg;*.jpeg;*.png;*.webp;*.pdf")]
    files = filedialog.askopenfilename(title="Select File", filetypes=file_types)
    if files:
        selected_file = files
        drop_area.config(text=f"Selected File:\n{os.path.basename(selected_file)}")
        update_buttons()

def choose_and_convert_images():
    # 
    files = filedialog.askopenfilenames(
        title="Select image files to convert",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp")]
    )
    if files:
        convert_images_to_pdf(files)

def clear_selection():
    global selected_file
    selected_file = None
    drop_area.config(text="Drop a file here")
    update_buttons()

root = TkinterDnD.Tk()
root.title("File Converter")
root.geometry("400x350")
root.configure(bg="#212121")

label = tk.Label(root, text="Drag & Drop a file or use the button below", fg="#1DB954", bg="#212121", padx=10, pady=10)
label.pack()

drop_area = tk.Label(root, text="Drop a file here", fg="#1DB954", bg="#121212", width=50, height=4, relief="ridge")
drop_area.pack(pady=10)
drop_area.drop_target_register(DND_FILES)
drop_area.dnd_bind("<<Drop>>", on_drop)

btn_frame_top = tk.Frame(root, bg="#212121")
btn_frame_top.pack(pady=5)

btn_clear_file = tk.Button(btn_frame_top, text="Clear Selection", command=clear_selection, bg="#121212", fg="#FF4500", relief="flat", padx=10, pady=5)
btn_clear_file.grid(row=0, column=0, padx=5)

btn_select_file = tk.Button(btn_frame_top, text="Open File Explorer", command=open_file_dialog, bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_select_file.grid(row=0, column=1, padx=5)

label_convert = tk.Label(root, text="Convert this file to:", fg="#1DB954", bg="#212121", pady=10)
label_convert.pack()

btn_frame = tk.Frame(root, bg="#212121")
btn_frame.pack(pady=5)

btn_to_png = tk.Button(btn_frame, text=".png", command=lambda: convert_file("png"), bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_png.grid(row=0, column=0, padx=5)

btn_to_jpeg = tk.Button(btn_frame, text=".jpg", command=lambda: convert_file("jpg"), bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_jpeg.grid(row=0, column=1, padx=5)

btn_to_webp = tk.Button(btn_frame, text=".webp", command=lambda: convert_file("webp"), bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_webp.grid(row=0, column=2, padx=5)

btn_to_pdf = tk.Button(btn_frame, text=".pdf", command=lambda: convert_file("pdf"), bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_pdf.grid(row=0, column=3, padx=5)

label_convert = tk.Label(root, text="Convert many images to one PDF:", fg="#1DB954", bg="#212121", pady=5)
label_convert.pack()

btn_many_img_to_one_pdf = tk.Button(root, text="Open file explorer", command=choose_and_convert_images, bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_many_img_to_one_pdf.pack(pady=5)

update_buttons()

root.mainloop()


