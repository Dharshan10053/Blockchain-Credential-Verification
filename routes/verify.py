from flask import Blueprint, render_template, request
from models.ocr import extract_text, extract_details
from models.hash_utils import generate_hash
from models.certificate_store import verify_certificate
import os

verify_bp = Blueprint('verify', __name__)

@verify_bp.route('/', methods=['POST'])
def verify_certificate_route():
    filepath = request.form.get('filepath')
    if not filepath or not os.path.exists(filepath):
        return "Certificate file not found"

    # OCR
    raw_text = extract_text(filepath)

    # Extract structured fields
    name, course, date, cert_id, full_text = extract_details(raw_text)

    # Create structured string
    structured = f"{name}|{course}|{date}|{cert_id}"

    # Hash
    hash_value = generate_hash(structured)

    # Verify
    is_valid = verify_certificate(cert_id, hash_value)

    return render_template(
        'result.html',
        text=structured,
        hash_value=hash_value,
        status="Authentic" if is_valid else "Fake"
    )