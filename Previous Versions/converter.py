import subprocess
import argparse
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

REQUIREMENTS_FILE_NAME = "requirements.txt"

def install_requirements():
    try:
        from PIL import Image
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

def converter(image_path):
    """Convert JPEG/JPG to PDF"""
    try:
        # Check if the file exists
        if not os.path.exists(image_path):
            print(f"Error: File '{image_path}' does not exist.")
            return

        # Get the file name without extension
        base_name = os.path.splitext(image_path)[0]
        pdf_path = f"{base_name}_converted.pdf"

        # Open the image
        img = Image.open(image_path)

        # Convert to RGB mode (required for PDF)
        img = img.convert("RGB")

        # Save as PDF
        img.save(pdf_path)

        print(f"✅ File successfully saved as: {pdf_path}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

# Check if an argument was provided
if len(sys.argv) > 1:
    converter(sys.argv[1])
else:
    print("Usage: python jpeg_to_pdf.py image.jpg")
