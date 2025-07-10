import subprocess
import logging
import sys
import os

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