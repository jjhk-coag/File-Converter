import os
import queue
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttkb
from tkinterdnd2 import DND_FILES, TkinterDnD

from backend.exceptions import ConversionCancelledError
from backend.converter import FileConverter
from backend.formats import (
    FILE_DIALOG_TYPES,
    IMAGE_DIALOG_TYPES,
    PDF_SAVE_DIALOG_TYPES,
    SUPPORTED_EXTENSIONS,
)
from backend.pdf_service import PdfService
from services.conversion_worker import ConversionResult, ConversionWorker


class ConverterApp:
    def __init__(self):
        # =========================
        # Stan aplikacji
        # =========================

        self.selected_files: list[str] = []

        self.ui_queue: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()

        self.worker_thread: threading.Thread | None = None

        self.converter = FileConverter()
        self.pdf_service = PdfService()

        # =========================
        # Główne okno
        # =========================

        self.root = TkinterDnD.Tk()
        self.root.title("File Converter")
        self.root.geometry("560x470")
        self.root.minsize(560, 470)

        self.style = ttkb.Style(theme="darkly")

        self._create_widgets()

        self.update_buttons()
        self.update_progress(0, 1)

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close,
        )

    # =====================================================
    # Tworzenie interfejsu
    # =====================================================

    def _create_widgets(self):
        title_label = ttkb.Label(
            self.root,
            text="Drag & Drop file(s) or use the button below",
            font=("Segoe UI", 11, "bold"),
            bootstyle="info",
        )
        title_label.pack(pady=(15, 5))

        self.drop_area = ttkb.Label(
            self.root,
            text="Drop file(s) here",
            width=60,
            font=("Segoe UI", 10),
            justify="center",
            anchor="center",
            bootstyle="info-inverse",
        )
        self.drop_area.pack(
            pady=10,
            padx=15,
            fill="x",
            ipady=30,
        )

        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind(
            "<<Drop>>",
            self.on_drop,
        )

        # =========================
        # Przyciski wyboru plików
        # =========================

        top_button_frame = ttkb.Frame(self.root)
        top_button_frame.pack(pady=5)

        self.btn_clear_file = ttkb.Button(
            top_button_frame,
            text="Clear Selection",
            command=self.clear_selection,
            bootstyle="warning-outline",
            takefocus=False,
        )
        self.btn_clear_file.grid(
            row=0,
            column=0,
            padx=5,
        )

        self.btn_select_file = ttkb.Button(
            top_button_frame,
            text="Open File Explorer",
            command=self.open_file_dialog,
            bootstyle="info-outline",
            takefocus=False,
        )
        self.btn_select_file.grid(
            row=0,
            column=1,
            padx=5,
        )

        self.btn_cancel = ttkb.Button(
            top_button_frame,
            text="Cancel",
            command=self.cancel_conversion,
            bootstyle="secondary-outline",
            state=tk.DISABLED,
            takefocus=False,
        )
        self.btn_cancel.grid(
            row=0,
            column=2,
            padx=5,
        )

        # =========================
        # Przyciski konwersji
        # =========================

        conversion_label = ttkb.Label(
            self.root,
            text="Convert selected file(s) to:",
            font=("Segoe UI", 11, "bold"),
            bootstyle="info",
        )
        conversion_label.pack(pady=(10, 5))

        conversion_button_frame = ttkb.Frame(self.root)
        conversion_button_frame.pack(pady=5)

        self.btn_to_png = ttkb.Button(
            conversion_button_frame,
            text=".png",
            command=lambda: self.convert_selected("png"),
            bootstyle="info",
            takefocus=False,
        )
        self.btn_to_png.grid(
            row=0,
            column=0,
            padx=5,
        )

        self.btn_to_jpeg = ttkb.Button(
            conversion_button_frame,
            text=".jpg",
            command=lambda: self.convert_selected("jpg"),
            bootstyle="info",
            takefocus=False,
        )
        self.btn_to_jpeg.grid(
            row=0,
            column=1,
            padx=5,
        )

        self.btn_to_webp = ttkb.Button(
            conversion_button_frame,
            text=".webp",
            command=lambda: self.convert_selected("webp"),
            bootstyle="info",
            takefocus=False,
        )
        self.btn_to_webp.grid(
            row=0,
            column=2,
            padx=5,
        )

        self.btn_to_pdf = ttkb.Button(
            conversion_button_frame,
            text=".pdf",
            command=lambda: self.convert_selected("pdf"),
            bootstyle="info",
            takefocus=False,
        )
        self.btn_to_pdf.grid(
            row=0,
            column=3,
            padx=5,
        )

        self.btn_to_heic = ttkb.Button(
            conversion_button_frame,
            text=".heic",
            command=lambda: self.convert_selected("heic"),
            bootstyle="info",
            takefocus=False,
        )
        self.btn_to_heic.grid(
            row=0,
            column=4,
            padx=5,
        )

        # =========================
        # Łączenie obrazów w PDF
        # =========================

        merge_label = ttkb.Label(
            self.root,
            text="Merge many images into one PDF:",
            font=("Segoe UI", 11, "bold"),
            bootstyle="info",
        )
        merge_label.pack(pady=(15, 0))

        self.btn_many_img_to_one_pdf = ttkb.Button(
            self.root,
            text="Open file explorer",
            command=self.choose_and_merge_images,
            bootstyle="info-outline",
            takefocus=False,
        )
        self.btn_many_img_to_one_pdf.pack(pady=10)

        # =========================
        # Pasek postępu
        # =========================

        progress_frame = ttkb.Frame(self.root)
        progress_frame.pack(
            pady=(10, 0),
            fill="x",
            padx=15,
        )

        self.progress_label = ttkb.Label(
            progress_frame,
            text="Status: 0/0",
            font=("Segoe UI", 10, "bold"),
            bootstyle="info",
        )
        self.progress_label.pack(anchor="center")

        self.progress_bar = ttkb.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            bootstyle="info-striped",
        )
        self.progress_bar.pack(
            fill="x",
            pady=6,
        )

        # =========================
        # Rozwijany log
        # =========================

        log_container = ttkb.Frame(self.root)
        log_container.pack(
            pady=6,
            fill="both",
            expand=True,
            padx=15,
        )

        self.btn_toggle_log = ttkb.Button(
            log_container,
            text="Show Log ▼",
            command=self.toggle_log,
            bootstyle="info-link",
            takefocus=False,
        )
        self.btn_toggle_log.pack(anchor="w")

        self.log_content_frame = ttkb.Frame(log_container)

        log_scroll = ttkb.Scrollbar(
            self.log_content_frame,
            bootstyle="round",
        )
        log_scroll.pack(
            side="right",
            fill="y",
        )

        self.log_text = tk.Text(
            self.log_content_frame,
            height=6,
            bg="#222222",
            fg="#0F7E0F",
            insertbackground="#0F7E0F",
            selectbackground="#0F7E0F",
            selectforeground="white",
            yscrollcommand=log_scroll.set,
            relief="flat",
            padx=8,
            pady=6,
        )
        self.log_text.pack(
            side="left",
            fill="both",
            expand=True,
        )

        self.log_text.configure(state=tk.DISABLED)
        log_scroll.config(command=self.log_text.yview)

    # =====================================================
    # Uruchomienie aplikacji
    # =====================================================

    def run(self):
        self.pump_ui_queue()

        try:
            self.root.mainloop()
        except Exception:
            error_message = traceback.format_exc()

            try:
                messagebox.showerror(
                    "Fatal Error",
                    f"Application crashed:\n\n{error_message}",
                )
            except Exception:
                pass

    # =====================================================
    # Obsługa zaznaczenia plików
    # =====================================================

    def set_selection(self, files):
        cleaned_files = []
        seen_files = set()

        for file_path in files:
            if not file_path:
                continue

            normalized_path = os.path.normpath(file_path)
            extension = os.path.splitext(normalized_path)[1].lower()

            if extension not in SUPPORTED_EXTENSIONS:
                continue

            if normalized_path in seen_files:
                continue

            if not os.path.isfile(normalized_path):
                continue

            cleaned_files.append(normalized_path)
            seen_files.add(normalized_path)

        self.selected_files = cleaned_files

        self.update_drop_area()
        self.update_buttons()
        self.update_progress(
            0,
            max(1, len(self.selected_files)),
        )

    def clear_selection(self):
        if self.is_worker_running():
            return

        self.set_selection([])

    def update_drop_area(self):
        if not self.selected_files:
            self.drop_area.config(
                text="Drop file(s) here",
                justify="center",
                anchor="center",
            )
            return

        visible_count = 6

        visible_names = [
            os.path.basename(file_path)
            for file_path in self.selected_files[:visible_count]
        ]

        additional_text = ""

        if len(self.selected_files) > visible_count:
            additional_count = (
                len(self.selected_files) - visible_count
            )

            additional_text = (
                f"\n... +{additional_count} more"
            )

        self.drop_area.config(
            text=(
                f"Selected files: {len(self.selected_files)}\n"
                + "\n".join(visible_names)
                + additional_text
            )
        )

    # =====================================================
    # Drag & Drop oraz File Explorer
    # =====================================================

    def on_drop(self, event):
        if self.is_worker_running():
            return

        files = self.root.tk.splitlist(event.data)

        if files:
            self.set_selection(files)

    def open_file_dialog(self):
        if self.is_worker_running():
            return

        files = filedialog.askopenfilenames(
            title="Select file(s)",
            filetypes=FILE_DIALOG_TYPES,
        )

        if files:
            self.set_selection(files)

    # =====================================================
    # Przyciski i stan interfejsu
    # =====================================================

    def update_buttons(self):
        conversion_state = (
            tk.NORMAL
            if self.selected_files
            else tk.DISABLED
        )

        for button in self.conversion_buttons:
            button.config(state=conversion_state)

    @property
    def conversion_buttons(self):
        return (
            self.btn_to_png,
            self.btn_to_jpeg,
            self.btn_to_webp,
            self.btn_to_pdf,
            self.btn_to_heic,
        )

    @property
    def all_action_buttons(self):
        return (
            self.btn_to_png,
            self.btn_to_jpeg,
            self.btn_to_webp,
            self.btn_to_pdf,
            self.btn_to_heic,
            self.btn_select_file,
            self.btn_clear_file,
            self.btn_many_img_to_one_pdf,
        )

    def set_processing_state(self, processing: bool):
        if processing:
            for button in self.all_action_buttons:
                button.config(state=tk.DISABLED)

            self.btn_cancel.config(state=tk.NORMAL)

        else:
            self.btn_select_file.config(state=tk.NORMAL)
            self.btn_clear_file.config(state=tk.NORMAL)
            self.btn_many_img_to_one_pdf.config(
                state=tk.NORMAL
            )

            self.btn_cancel.config(state=tk.DISABLED)

            self.update_buttons()

    def is_worker_running(self):
        return bool(
            self.worker_thread
            and self.worker_thread.is_alive()
        )

    # =====================================================
    # Pasek postępu
    # =====================================================

    def update_progress(self, done: int, total: int):
        safe_total = max(1, total)
        safe_done = min(done, safe_total)

        self.progress_bar["maximum"] = safe_total
        self.progress_bar["value"] = safe_done

        self.progress_label.config(
            text=f"Status: {done}/{total}"
        )

    # =====================================================
    # Log
    # =====================================================

    def append_log(self, text: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(
            tk.END,
            text + "\n",
        )
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(
            "1.0",
            tk.END,
        )
        self.log_text.configure(state=tk.DISABLED)

    def toggle_log(self):
        if self.log_content_frame.winfo_ismapped():
            self.log_content_frame.pack_forget()
            self.btn_toggle_log.config(
                text="Show Log ▼"
            )
        else:
            self.log_content_frame.pack(
                side="top",
                fill="both",
                expand=True,
                pady=(5, 0),
            )

            self.btn_toggle_log.config(
                text="Hide Log ▲"
            )

    # =====================================================
    # Komunikacja worker → GUI
    # =====================================================

    def log_ui(self, message: str):
        self.ui_queue.put(
            ("log", message)
        )

    def progress_ui(self, done: int, total: int):
        self.ui_queue.put(
            ("progress", done, total)
        )

    def conversion_done_ui(
        self,
        result: ConversionResult,
    ):
        self.ui_queue.put(
            ("conversion_done", result)
        )

    def merge_done_ui(
        self,
        output_path: str,
        image_count: int,
    ):
        self.ui_queue.put(
            (
                "merge_done",
                output_path,
                image_count,
            )
        )

    def error_ui(
        self,
        title: str,
        message: str,
    ):
        self.ui_queue.put(
            (
                "error",
                title,
                message,
            )
        )

    def pump_ui_queue(self):
        try:
            while True:
                item = self.ui_queue.get_nowait()

                if not item:
                    continue

                message_type = item[0]

                if message_type == "log":
                    self.append_log(item[1])

                elif message_type == "progress":
                    _, done, total = item
                    self.update_progress(done, total)

                elif message_type == "conversion_done":
                    _, result = item
                    self.handle_conversion_finished(result)

                elif message_type == "merge_done":
                    _, output_path, image_count = item

                    self.handle_merge_finished(
                        output_path,
                        image_count,
                    )

                elif message_type == "merge_cancelled":
                    self.set_processing_state(False)
                    self.cancel_event.clear()

                    self.progress_label.config(
                        text="Status: Cancelled"
                    )

                    self.append_log(
                        "Image merging cancelled."
                    )

                    messagebox.showwarning(
                        "Cancelled",
                        "Image merging was cancelled.",
                    )

                elif message_type == "error":
                    _, title, message = item

                    self.set_processing_state(False)

                    messagebox.showerror(
                        title,
                        message,
                    )

        except queue.Empty:
            pass

        if self.root.winfo_exists():
            self.root.after(
                80,
                self.pump_ui_queue,
            )

    # =====================================================
    # Konwersja wybranych plików
    # =====================================================

    def convert_selected(self, output_format: str):
        if not self.selected_files:
            messagebox.showwarning(
                "Warning",
                (
                    "No files selected. "
                    "Please drag & drop or choose files."
                ),
            )
            return

        if self.is_worker_running():
            messagebox.showwarning(
                "Warning",
                "Conversion is already running.",
            )
            return

        self.clear_log()
        self.cancel_event.clear()
        self.set_processing_state(True)

        files_snapshot = list(self.selected_files)

        self.update_progress(
            0,
            len(files_snapshot),
        )

        self.append_log(
            f"Queued {len(files_snapshot)} file(s)."
        )

        self.worker_thread = threading.Thread(
            target=self._conversion_thread_target,
            args=(
                output_format,
                files_snapshot,
            ),
            daemon=True,
        )

        self.worker_thread.start()

    def _conversion_thread_target(
        self,
        output_format: str,
        files: list[str],
    ):
        try:
            worker = ConversionWorker(
                converter=self.converter,
                cancel_event=self.cancel_event,
            )

            self.log_ui(
                f"Starting batch conversion -> .{output_format}"
            )

            result = worker.run(
                files=files,
                output_format=output_format,
                on_log=self.log_ui,
                on_progress=self.progress_ui,
            )

            self.conversion_done_ui(result)

        except Exception as error:
            self.error_ui(
                "Conversion Error",
                str(error),
            )

    def cancel_conversion(self):
        if self.is_worker_running():
            self.cancel_event.set()

            self.append_log(
                "Cancelling... "
                "(will stop after current file/page)"
            )

            self.btn_cancel.config(
                state=tk.DISABLED
            )

    def handle_conversion_finished(
        self,
        result: ConversionResult,
    ):
        self.set_processing_state(False)
        self.cancel_event.clear()

        processed_count = (
            result.converted_count
            + result.skipped_count
            + result.failed_count
        )

        if result.cancelled:
            self.progress_label.config(
                text="Status: Cancelled"
            )
        else:
            self.progress_label.config(
                text="Status: Completed"
            )

        message = (
            f"{'Cancelled!' if result.cancelled else 'Done!'}\n\n"
            f"Selected: {result.selected_count}\n"
            f"Processed: {processed_count}\n"
            f"Converted: {result.converted_count}\n"
            f"Skipped: {result.skipped_count}\n"
            f"Failed: {result.failed_count}\n"
        )

        if result.output_files:
            output_preview = "\n".join(
                result.output_files[:8]
            )

            if len(result.output_files) > 8:
                output_preview += (
                    f"\n... +"
                    f"{len(result.output_files) - 8} more"
                )

            message += (
                "\nSaved outputs:\n"
                f"{output_preview}\n"
            )

        if result.errors:
            error_preview = "\n".join(
                result.errors[:10]
            )

            if len(result.errors) > 10:
                error_preview += (
                    f"\n... +"
                    f"{len(result.errors) - 10} more"
                )

            message += (
                "\nNotes:\n"
                f"{error_preview}"
            )

        if result.failed_count > 0:
            messagebox.showwarning(
                "Finished with errors",
                message,
            )

        elif result.cancelled:
            messagebox.showwarning(
                "Conversion cancelled",
                message,
            )

        else:
            messagebox.showinfo(
                "Success",
                message,
            )

    # =====================================================
    # Łączenie obrazów w jeden PDF
    # =====================================================

    def choose_and_merge_images(self):
        if self.is_worker_running():
            messagebox.showwarning(
                "Warning",
                "Another operation is already running.",
            )
            return

        files = filedialog.askopenfilenames(
            title="Select image files to merge into one PDF",
            filetypes=IMAGE_DIALOG_TYPES,
        )

        if not files:
            return

        output_path = filedialog.asksaveasfilename(
            title="Save merged PDF",
            defaultextension=".pdf",
            filetypes=PDF_SAVE_DIALOG_TYPES,
            initialfile="merged.pdf",
        )

        if not output_path:
            return

        self.clear_log()
        self.cancel_event.clear()
        self.set_processing_state(True)
        self.update_progress(0, len(files))

        files_snapshot = list(files)

        self.append_log(
            f"Queued {len(files_snapshot)} image(s) for merging."
        )

        self.worker_thread = threading.Thread(
            target=self._merge_thread_target,
            args=(
                files_snapshot,
                output_path,
            ),
            daemon=True,
        )

        self.worker_thread.start()

    def _merge_thread_target(
        self,
        image_paths: list[str],
        output_path: str,
    ):
        try:
            self.log_ui(
                "Starting image merge..."
            )

            created_path = self.pdf_service.merge_images(
                image_paths=image_paths,
                output_path=output_path,
                cancel_callback=self.cancel_event.is_set,
                progress_callback=self.progress_ui,
                log_callback=self.log_ui,
            )

            self.merge_done_ui(
                created_path,
                len(image_paths),
            )

        except ConversionCancelledError:
            self.ui_queue.put(
                ("merge_cancelled",)
            )

        except Exception as error:
            self.error_ui(
                "PDF Merge Error",
                str(error),
            )

    def handle_merge_finished(
        self,
        output_path: str,
        image_count: int,
    ):
        self.set_processing_state(False)
        self.cancel_event.clear()

        self.progress_label.config(
            text="Status: Completed"
        )

        self.append_log(
            f"Created PDF: {output_path}"
        )

        messagebox.showinfo(
            "Success",
            (
                f"Created PDF with {image_count} page(s):\n\n"
                f"{output_path}"
            ),
        )

    # =====================================================
    # Zamykanie programu
    # =====================================================

    def on_close(self):
        if self.is_worker_running():
            should_close = messagebox.askyesno(
                "Operation in progress",
                (
                    "A conversion is currently running.\n\n"
                    "Do you want to cancel it and close the application?"
                ),
            )

            if not should_close:
                return

            self.cancel_event.set()

        self.root.destroy()