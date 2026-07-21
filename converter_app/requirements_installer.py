import subprocess
import logging
import sys
import os
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import traceback

REQUIREMENTS_FILE_NAME = "apprequirements.txt"

def install_requirements():
    root = tk.Tk()
    root.title("Loading...")
    # Hide the standard window borders to make it look like a splash screen
    root.overrideredirect(True)
    root.geometry("350x150")
    root.configure(bg="#212121")
    # Center window
    root.update_idletasks()
    width = 350
    height = 150
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    label = tk.Label(root, text="Checking required libraries...", fg="#16B5FE", bg="#212121", font=("Arial", 12))
    label.pack(pady=25)

    progress = ttk.Progressbar(root, orient="horizontal", length=250, mode="indeterminate")
    progress.pack(pady=10)
    progress.start(15)

    def check_and_install():
        try:
            from PIL import Image
            import tkinter as tk_temp
            from tkinterdnd2 import DND_FILES, TkinterDnD
            from tkinter import filedialog, messagebox
            import fitz
            import pillow_heif
            logging.info("All required libraries are already installed.")
            # Done, close the splash screen
            root.after(100, root.destroy)
        except ImportError:
            logging.info("Missing Libraries. Installing...")
            root.after(0, lambda: label.config(text="Installing missing libraries (this may take a while)..."))
            
            # Make sure we're looking in the correct path where apprequirements.txt is located relative to execution path
            req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), REQUIREMENTS_FILE_NAME)
            
            if not os.path.exists(req_path):
                logging.error(f"File {REQUIREMENTS_FILE_NAME} not found.")
                root.after(0, lambda: show_error_and_exit(f"Required file {REQUIREMENTS_FILE_NAME} is missing."))
                return
            try:
                # Install without hiding the window
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logging.info("All required libraries installed.")
                root.after(100, root.destroy)
            except subprocess.CalledProcessError as e:
                logging.error("Failed to install required libraries.")
                root.after(0, lambda: show_error_and_exit(f"Failed to install required libraries.\nMake sure you have internet connection.\nError: {e}"))
            except Exception as e:
                root.after(0, lambda: show_error_and_exit(f"An unexpected error occurred:\n{e}"))

    def show_error_and_exit(err_msg):
        # Stop the progress bar
        progress.stop()
        
        # We can just show a messagebox on top of our hidden root
        root.withdraw()
        messagebox.showerror("Startup Error", err_msg)
        sys.exit(1)

    # Start checking in a background thread so the GUI doesn't freeze
    threading.Thread(target=check_and_install, daemon=True).start()

    root.mainloop()