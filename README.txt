# Multilingual OCR Tool — Windows

This app processes a folder containing JPG/JPEG/PNG/BMP/TIFF/WEBP images and extracts text in:
- English
- Bengali
- Hindi
- Any combination of the three, including mixed-language images.

## 1. Install Python
Install Python 3.10+ for Windows from python.org.
During installation, tick "Add Python to PATH".

## 2. Install Tesseract OCR
Install Tesseract OCR for Windows. During setup, make sure the language data for:
- English (eng)
- Bengali (ben)
- Hindi (hin)
is installed.

If Tesseract is installed but not in PATH, edit ocr_tool.py and add:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

## 3. Install Python packages
Open Command Prompt in this folder and run:
pip install -r requirements.txt

## 4. Run
python ocr_tool.py

Select the folder containing your 50+ images, select an output folder, choose:
English + Bengali + Hindi

Then click START OCR.

The output folder will contain:
- OCR_Output.xlsx
- OCR_Output.txt

The Excel file has:
File Name | Extracted Text | Status

## Important
OCR accuracy depends heavily on image quality. The app automatically rotates based on EXIF, upscales smaller images, improves contrast/sharpness, and uses a document-friendly OCR mode.

The sample screenshot you provided contains Bengali and English mixed together and is suitable for this workflow.
