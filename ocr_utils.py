import pytesseract
from PIL import Image

# Make sure tesseract path is correct for your system
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(image_path: str) -> str:
    """Extract text from an image using OCR"""
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text
