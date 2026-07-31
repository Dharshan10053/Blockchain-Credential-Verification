from flask import Flask, render_template, request
import os
import hashlib
import pytesseract
from PIL import Image
import re
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
BLOCKCHAIN_FILE = "blockchain.txt"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

# ----------------------------------
# FILE VALIDATION
# ----------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------------------------
# IMAGE PREPROCESSING
# ----------------------------------
def preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.8, beta=20)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    return thresh


# ----------------------------------
# OCR FUNCTION (IMPROVED)
# ----------------------------------
# ----------------------------------
def perform_ocr(filepath):
    import fitz  # PyMuPDF
    text = ""
    custom_config = r'--oem 3 --psm 6'

    try:
        if filepath.lower().endswith(".pdf"):
            # Open PDF using PyMuPDF
            doc = fitz.open(filepath)
            for page in doc:
                page_text = page.get_text().strip()
                if page_text:
                    text += page_text + "\n"
                else:
                    # fallback: convert page to image for scanned PDF
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                   cv2.THRESH_BINARY, 11, 2)
                    text += pytesseract.image_to_string(thresh, config=custom_config) + "\n"
        else:
            # Image files (png/jpg/jpeg)
            processed = preprocess_image(filepath)
            if processed is not None:
                text1 = pytesseract.image_to_string(processed, config=custom_config)
                text2 = pytesseract.image_to_string(processed, config="--oem 3 --psm 11")
                text = text1 + "\n" + text2
            else:
                text = pytesseract.image_to_string(Image.open(filepath), config=custom_config)

        print("\n----- OCR RAW TEXT -----")
        print(text)
        print("------------------------\n")
        return text

    except Exception as e:
        print("OCR Error:", e)
        return ""


# ----------------------------------
# DETAIL EXTRACTION (UNCHANGED)
# ----------------------------------
def extract_details(text):
    name = "Unknown"
    course = "Unknown"
    date = "Unknown"
    cert_id = "Unknown"

    # Normalize text
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    normalized_text = "\n".join(lines)

    # Match structured fields
    name_match = re.search(r"(Student Name|Name)\s*\n\s*(.+)", normalized_text, re.IGNORECASE)
    if name_match:
        name = name_match.group(2).strip()

    course_match = re.search(r"(Course)\s*\n\s*(.+)", normalized_text, re.IGNORECASE)
    if course_match:
        course = course_match.group(2).strip()

    date_match = re.search(r"(Issue Date|Date)\s*\n\s*(.+)", normalized_text, re.IGNORECASE)
    if date_match:
        date = date_match.group(2).strip()

    id_match = re.search(r"(Certificate ID|Cert ID|ID)\s*\n\s*(.+)", normalized_text, re.IGNORECASE)
    if id_match:
        cert_id = id_match.group(2).strip()

    # Fallback heuristics if labels are missing
    if name == "Unknown":
        for i, line in enumerate(lines):
            if "presented to" in line.lower() and i + 1 < len(lines):
                name = lines[i + 1]
                break

    if course == "Unknown":
        keywords = ["python", "machine", "data", "blockchain", "course", "internship"]
        for line in lines:
            if any(k in line.lower() for k in keywords):
                course = line
                break

    if date == "Unknown":
        date_patterns = [
            r"\d{1,2}/\d{1,2}/\d{4}",
            r"\d{4}-\d{2}-\d{2}",
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{4}"
        ]
        for pattern in date_patterns:
            m = re.search(pattern, text)
            if m:
                date = m.group()
                break

    if cert_id == "Unknown":
        id_patterns = [
            r"(Certificate ID|Cert ID|ID)[:\s]*([A-Za-z0-9\-]+)"
        ]
        for pattern in id_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                cert_id = m.group(2)
                break

    print("----- EXTRACTED DETAILS -----")
    print("Name:", name)
    print("Course:", course)
    print("Date:", date)
    print("Certificate ID:", cert_id)
    print("-----------------------------\n")

    return {
        "name": name,
        "course": course,
        "date": date,
        "cert_id": cert_id
    }
# ----------------------------------
# HASH / BLOCKCHAIN (UNCHANGED)
# ----------------------------------
def generate_hash(details):
    data_string = details["name"] + details["course"] + details["date"] + details["cert_id"]
    cert_hash = hashlib.sha256(data_string.encode()).hexdigest()
    print("Generated Hash:", cert_hash)
    return cert_hash

def load_hashes():
    if not os.path.exists(BLOCKCHAIN_FILE):
        return set()
    with open(BLOCKCHAIN_FILE, "r") as f:
        return set(f.read().splitlines())

def add_certificate(cert_hash):
    hashes = load_hashes()
    if cert_hash in hashes:
        return "ALREADY EXISTS"
    with open(BLOCKCHAIN_FILE, "a") as f:
        f.write(cert_hash + "\n")
    return "ISSUED SUCCESSFULLY"

def verify_certificate(cert_hash):
    hashes = load_hashes()
    return "VERIFIED" if cert_hash in hashes else "FAKE"


# ----------------------------------
# ROUTES (UNCHANGED)
# ----------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        # Get uploaded file
        file = request.files.get("certificate")
        if not file or not allowed_file(file.filename):
            return render_template("issue.html", error="Invalid file type.")

        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # OCR to extract text
        text = perform_ocr(filepath)
        details = extract_details(text)

        # Generate hash from file bytes (safer than text-based)
        cert_hash = generate_hash_from_file(filepath)

        # Add to blockchain
        status = add_certificate(cert_hash)

        return render_template(
            "result.html",
            status=status,
            name=details["name"],
            course=details["course"],
            date=details["date"],
            cert_id=details["cert_id"],
            hash=cert_hash
        )

    return render_template("issue.html")
@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        file = request.files.get("certificate")
        if not file or not allowed_file(file.filename):
            return render_template("verify.html")
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        text = perform_ocr(filepath)
        details = extract_details(text)
        cert_hash = generate_hash(details)
        status = verify_certificate(cert_hash)
        return render_template(
            "result.html",
            status=status,
            name=details["name"],
            course=details["course"],
            date=details["date"],
            cert_id=details["cert_id"],
            hash=cert_hash
        )
    return render_template("verify.html")


# ----------------------------------
# RUN APP
# ----------------------------------
if __name__ == "__main__":
    app.run(debug=True)