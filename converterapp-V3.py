import subprocess
import logging
import sys
import os
import traceback
import threading
import queue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from requirements_installer import install_requirements
install_requirements()

from PIL import Image
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog, messagebox
from tkinter import ttk
import fitz

selected_files = []
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}

# ==== Threading / UI messaging ====
ui_queue = queue.Queue()
cancel_event = threading.Event()
worker_thread = None

def log_ui(msg: str):
    ui_queue.put(("log", msg))

def progress_ui(done: int, total: int):
    ui_queue.put(("progress", done, total))

def done_ui(summary_title: str, summary_msg: str, had_errors: bool):
    ui_queue.put(("done", summary_title, summary_msg, had_errors))

def set_buttons_enabled(enabled: bool):
    state = "normal" if enabled else "disabled"
    bg_on = "#121212"
    bg_off = "#555555"

    for btn in (btn_to_png, btn_to_jpeg, btn_to_webp, btn_to_pdf, btn_select_file, btn_clear_file, btn_many_img_to_one_pdf):
        btn.config(state=state, bg=(bg_on if enabled else bg_off))

    btn_cancel.config(state=("disabled" if enabled else "normal"))
    if enabled:
        btn_cancel.config(bg=bg_off)
    else:
        btn_cancel.config(bg="#3a1f1f")  # delikatny "cancel vibe"

def set_selection(files):
    global selected_files

    cleaned = []
    seen = set()
    for f in files:
        if not f:
            continue
        f = os.path.normpath(f)
        ext = os.path.splitext(f)[1].lower()
        if ext in SUPPORTED_EXTS and f not in seen:
            cleaned.append(f)
            seen.add(f)

    selected_files = cleaned
    update_drop_area()
    update_buttons()
    update_progress(0, max(1, len(selected_files)))

def update_drop_area():
    if not selected_files:
        drop_area.config(text="Drop file(s) here")
        return

    shown = 6
    names = [os.path.basename(f) for f in selected_files[:shown]]
    more = ""
    if len(selected_files) > shown:
        more = f"\n... +{len(selected_files) - shown} more"

    drop_area.config(
        text=f"Selected files: {len(selected_files)}\n" + "\n".join(names) + more
    )

def update_buttons():
    state = "normal" if selected_files else "disabled"
    bg_on = "#121212"
    bg_off = "#555555"

    for btn in (btn_to_png, btn_to_jpeg, btn_to_webp, btn_to_pdf):
        btn.config(state=state, bg=(bg_on if selected_files else bg_off))

def update_progress(done: int, total: int):
    total = max(1, total)
    progress_bar["maximum"] = total
    progress_bar["value"] = done
    progress_label.config(text=f"Progress: {done}/{total}")

def append_log(text: str):
    log_text.configure(state="normal")
    log_text.insert("end", text + "\n")
    log_text.see("end")
    log_text.configure(state="disabled")

def clear_log():
    log_text.configure(state="normal")
    log_text.delete("1.0", "end")
    log_text.configure(state="disabled")

def pump_ui_queue():
    try:
        while True:
            item = ui_queue.get_nowait()
            if not item:
                continue

            kind = item[0]

            if kind == "log":
                append_log(item[1])

            elif kind == "progress":
                _, done, total = item
                update_progress(done, total)

            elif kind == "done":
                _, title, msg, had_errors = item
                set_buttons_enabled(True)
                cancel_event.clear()

                # końcowy popup
                if had_errors:
                    messagebox.showwarning(title, msg)
                else:
                    messagebox.showinfo(title, msg)

    except queue.Empty:
        pass

    root.after(80, pump_ui_queue)

def convert_one_file(input_path, output_format):
    file_extension = os.path.splitext(input_path)[1].lower()
    outputs = []

    base_output_path = os.path.splitext(input_path)[0] + f".{output_format}"

    # obraz -> pdf
    if file_extension in [".jpg", ".jpeg", ".png", ".webp"] and output_format == "pdf":
        img = Image.open(input_path).convert("RGB")
        img.save(base_output_path)
        outputs.append(base_output_path)
        return outputs

    # pdf -> obrazy (po stronach)
    if file_extension == ".pdf" and output_format in ["jpg", "png", "webp"]:
        pdf_document = fitz.open(input_path)
        for page_num in range(len(pdf_document)):
            # pozwól przerwać w trakcie (cancel)
            if cancel_event.is_set():
                raise RuntimeError("Cancelled by user.")

            page = pdf_document[page_num]
            zoom = 3.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            out = os.path.splitext(input_path)[0] + f"_page{page_num + 1}.{output_format}"
            img.save(out)
            outputs.append(out)
        return outputs

    # jpg/jpeg -> png/webp
    if file_extension in [".jpg", ".jpeg"] and output_format in ["png", "webp"]:
        img = Image.open(input_path).convert("RGBA")
        img.save(base_output_path)
        outputs.append(base_output_path)
        return outputs

    # png -> jpg/webp
    if file_extension == ".png" and output_format in ["jpg", "webp"]:
        img = Image.open(input_path).convert("RGB")
        img.save(base_output_path, "JPEG" if output_format == "jpg" else "WEBP")
        outputs.append(base_output_path)
        return outputs

    # webp -> jpg/png
    if file_extension == ".webp" and output_format in ["jpg", "png"]:
        img = Image.open(input_path).convert("RGB")
        img.save(base_output_path, "JPEG" if output_format == "jpg" else "PNG")
        outputs.append(base_output_path)
        return outputs

    raise ValueError(f"Unsupported conversion: {file_extension} -> {output_format}")

def worker_convert_selected(output_format: str, files: list[str]):
    total = len(files)
    success_count = 0
    skipped_count = 0
    fail_count = 0

    saved_outputs = []
    errors = []

    log_ui(f"Starting batch conversion -> .{output_format}")
    progress_ui(0, total)

    for i, f in enumerate(files, start=1):
        if cancel_event.is_set():
            log_ui("Cancelled by user.")
            break

        name = os.path.basename(f)
        log_ui(f"[{i}/{total}] Converting: {name}")

        try:
            outs = convert_one_file(f, output_format)
            saved_outputs.extend(outs)
            success_count += 1
            if len(outs) == 1:
                log_ui(f"  ✓ Saved: {os.path.basename(outs[0])}")
            else:
                log_ui(f"  ✓ Saved: {len(outs)} files (pages)")
        except ValueError as ve:
            skipped_count += 1
            errors.append(f"{name}: {ve}")
            log_ui(f"  ↷ Skipped: {ve}")
        except Exception as e:
            fail_count += 1
            errors.append(f"{name}: {e}")
            log_ui(f"  ✗ Failed: {e}")

        progress_ui(i, total)

    # raport końcowy
    actually_processed = success_count + skipped_count + fail_count
    cancelled = cancel_event.is_set()

    msg = (
        f"{'Cancelled!' if cancelled else 'Done!'}\n\n"
        f"Selected: {total}\n"
        f"Processed: {actually_processed}\n"
        f"Converted: {success_count}\n"
        f"Skipped (unsupported): {skipped_count}\n"
        f"Failed (error): {fail_count}\n"
    )

    if saved_outputs:
        preview = "\n".join(saved_outputs[:8])
        if len(saved_outputs) > 8:
            preview += f"\n... +{len(saved_outputs) - 8} more"
        msg += f"\nSaved outputs (preview):\n{preview}\n"

    if errors:
        err_preview = "\n".join(errors[:10])
        if len(errors) > 10:
            err_preview += f"\n... +{len(errors) - 10} more"
        msg += f"\nNotes:\n{err_preview}"

    had_errors = (fail_count > 0)
    done_ui("Finished with errors" if had_errors else "Success", msg, had_errors)

def convert_selected(output_format: str):
    global worker_thread

    if not selected_files:
        messagebox.showwarning("Warning", "No files selected. Please drag & drop or choose files.")
        return

    # zabezpieczenie przed odpaleniem 2 batchy na raz
    if worker_thread and worker_thread.is_alive():
        messagebox.showwarning("Warning", "Conversion is already running.")
        return

    clear_log()
    cancel_event.clear()
    set_buttons_enabled(False)

    files_snapshot = list(selected_files)  # żeby w trakcie user nie zmienił listy
    update_progress(0, len(files_snapshot))
    append_log(f"Queued {len(files_snapshot)} file(s).")

    worker_thread = threading.Thread(
        target=worker_convert_selected,
        args=(output_format, files_snapshot),
        daemon=True
    )
    worker_thread.start()

def cancel_conversion():
    if worker_thread and worker_thread.is_alive():
        cancel_event.set()
        append_log("Cancelling... (will stop after current file/page)")

def convert_images_to_pdf(selected_images):
    if not selected_images:
        messagebox.showwarning("Warning", "No image files selected.")
        return

    image_files = [f for f in selected_images if os.path.splitext(f)[1].lower() in [".jpg", ".jpeg", ".png", ".webp"]]
    if not image_files:
        messagebox.showerror("Error", "No supported image files (.jpg, .png, .webp) selected.")
        return

    try:
        images = [Image.open(f).convert("RGB") for f in image_files]
        output_path = os.path.splitext(image_files[0])[0] + "_merged.pdf"

        if len(images) == 1:
            images[0].save(output_path, format="PDF")
        else:
            images[0].save(output_path, save_all=True, append_images=images[1:], format="PDF")

        messagebox.showinfo("Success", f"Created PDF with {len(images)} page(s):\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create PDF: {e}")

def on_drop(event):
    files = root.tk.splitlist(event.data)
    if files:
        set_selection(files)

def open_file_dialog():
    file_types = [("All Supported Files", "*.jpg;*.jpeg;*.png;*.webp;*.pdf")]
    files = filedialog.askopenfilenames(title="Select file(s)", filetypes=file_types)
    if files:
        set_selection(files)

def choose_and_convert_images():
    files = filedialog.askopenfilenames(
        title="Select image files to merge into one PDF",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp")]
    )
    if files:
        convert_images_to_pdf(files)

def clear_selection():
    set_selection([])

# ===== UI =====

root = TkinterDnD.Tk()
root.title("File Converter")
root.geometry("560x560")
root.configure(bg="#212121")

label = tk.Label(root, text="Drag & Drop file(s) or use the button below", fg="#1DB954", bg="#212121", padx=10, pady=10)
label.pack()

drop_area = tk.Label(
    root, text="Drop file(s) here", fg="#1DB954", bg="#121212",
    width=68, height=6, relief="ridge", justify="left", anchor="w"
)
drop_area.pack(pady=10)
drop_area.drop_target_register(DND_FILES)
drop_area.dnd_bind("<<Drop>>", on_drop)

btn_frame_top = tk.Frame(root, bg="#212121")
btn_frame_top.pack(pady=5)

btn_clear_file = tk.Button(btn_frame_top, text="Clear Selection", command=clear_selection,
                           bg="#121212", fg="#FF4500", relief="flat", padx=10, pady=5)
btn_clear_file.grid(row=0, column=0, padx=5)

btn_select_file = tk.Button(btn_frame_top, text="Open File Explorer (multi)", command=open_file_dialog,
                            bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_select_file.grid(row=0, column=1, padx=5)

btn_cancel = tk.Button(btn_frame_top, text="Cancel", command=cancel_conversion,
                       bg="#555555", fg="#FFB3B3", relief="flat", padx=10, pady=5, state="disabled")
btn_cancel.grid(row=0, column=2, padx=5)

label_convert = tk.Label(root, text="Convert selected file(s) to:", fg="#1DB954", bg="#212121", pady=10)
label_convert.pack()

btn_frame = tk.Frame(root, bg="#212121")
btn_frame.pack(pady=5)

btn_to_png = tk.Button(btn_frame, text=".png", command=lambda: convert_selected("png"),
                       bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_png.grid(row=0, column=0, padx=5)

btn_to_jpeg = tk.Button(btn_frame, text=".jpg", command=lambda: convert_selected("jpg"),
                        bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_jpeg.grid(row=0, column=1, padx=5)

btn_to_webp = tk.Button(btn_frame, text=".webp", command=lambda: convert_selected("webp"),
                        bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_webp.grid(row=0, column=2, padx=5)

btn_to_pdf = tk.Button(btn_frame, text=".pdf", command=lambda: convert_selected("pdf"),
                       bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_to_pdf.grid(row=0, column=3, padx=5)

# ==== Progress area ====
progress_frame = tk.Frame(root, bg="#212121")
progress_frame.pack(pady=10, fill="x", padx=12)

progress_label = tk.Label(progress_frame, text="Progress: 0/0", fg="#1DB954", bg="#212121")
progress_label.pack(anchor="w")

progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
progress_bar.pack(fill="x", pady=6)

# ==== Log area ====
log_frame = tk.Frame(root, bg="#212121")
log_frame.pack(pady=6, fill="both", expand=True, padx=12)

log_label = tk.Label(log_frame, text="Log:", fg="#1DB954", bg="#212121")
log_label.pack(anchor="w")

log_scroll = tk.Scrollbar(log_frame)
log_scroll.pack(side="right", fill="y")

log_text = tk.Text(log_frame, height=10, bg="#121212", fg="#D8FFD8", insertbackground="#D8FFD8",
                   yscrollcommand=log_scroll.set, relief="flat", padx=8, pady=6)
log_text.pack(side="left", fill="both", expand=True)
log_text.configure(state="disabled")
log_scroll.config(command=log_text.yview)

# ==== Separate feature: merge images into one PDF ====
label_convert2 = tk.Label(root, text="Merge many images into one PDF:", fg="#1DB954", bg="#212121", pady=6)
label_convert2.pack()

btn_many_img_to_one_pdf = tk.Button(root, text="Open file explorer", command=choose_and_convert_images,
                                    bg="#121212", fg="#1DB954", relief="flat", padx=10, pady=5)
btn_many_img_to_one_pdf.pack(pady=5)

try:
    update_buttons()
    pump_ui_queue()  # start UI queue loop
    root.mainloop()
except Exception:
    error_root = tk.Tk()
    error_root.withdraw()
    error_msg = traceback.format_exc()
    messagebox.showerror("Fatal Error", f"Application crashed:\n\n{error_msg}")
    error_root.destroy()
