from flask import Blueprint, render_template, request
from werkzeug.utils import secure_filename
import os

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/', methods=['GET'])
def index():
    return render_template('upload.html')  # Show upload page

@upload_bp.route('/upload', methods=['POST'])
def upload_certificate():
    file = request.files.get('certificate')
    if not file or file.filename == '':
        return "No file selected"

    filename = secure_filename(file.filename)
    upload_folder = 'uploads/certificates'
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Instead of returning a string, render the verification page
    return render_template('verify.html', filepath=filepath)
