"""
Certificate Authentication System — Flask Application
Smart Certificate Authentication Using Blockchain and AI Validation
"""
import logging
import os

from flask import Flask, jsonify, render_template, request, send_file, abort
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import tempfile
# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

import sys
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# --- Startup Validation ---
if not os.environ.get("GEMINI_API_KEY"):
    logger.critical("FATAL: GEMINI_API_KEY environment variable is missing. Cannot start application.")
    sys.exit(1)

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Rate Limiting ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"]       = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"]  = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "docx"}

# --- Security Headers ---
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Strict-Transport-Security can be managed by reverse proxy (e.g. Nginx/Render), but adding defensively:
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# ---------------------------------------------------------------------------
# Service bootstrap
# ---------------------------------------------------------------------------

def _load_services():
    from services.extractor     import extract_details
    from backend.utils.hashing      import generate_hash_from_details
    from backend.utils.verification import classify_status, issue_certificate
    from backend.utils.blockchain   import Blockchain
    from backend.utils.qr_generator import generate_qr_base64
    from backend.utils.report_generator import generate_report
    from backend.database.db        import init_db, upsert_certificate, get_all_certificates, log_verification, get_certificate_by_token

    blockchain = Blockchain(os.path.join(BASE_DIR, "blockchain.json"))
    init_db()

    return (extract_details, generate_hash_from_details,
            classify_status, issue_certificate, blockchain,
            upsert_certificate, get_all_certificates,
            generate_qr_base64, generate_report, log_verification, get_certificate_by_token)


try:
    (extract_details, generate_hash_from_details,
     classify_status, issue_certificate, blockchain,
     upsert_certificate, get_all_certificates,
     generate_qr_base64, generate_report, log_verification, get_certificate_by_token) = _load_services()
    SERVICES_OK = True
except Exception as exc:
    logger.error("Failed to load backend services: %s", exc)
    SERVICES_OK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _process_upload(file) -> tuple[dict, str, str]:
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    details = extract_details(filepath)
    
    # Use new hash service for certificate hashing
    from services.hash_service import generate_certificate_hash
    from services.ledger_service import ledger_service
    from services.verification_service import verify_certificate
    
    # Validate extraction before generating hash
    if not details or not details.get("certificate_id"):
        raise ValueError("Extraction failed — cannot generate hash from empty data")
    
    h = generate_certificate_hash(details)
    
    # Extract certificate ID from details (do not generate fake ID)
    certificate_id = details.get("certificate_id")
    
    if ledger_service.certificate_exists(certificate_id):
        # Certificate exists - verify it
        stored_hash = ledger_service.get_stored_hash(certificate_id)
        verification_result = verify_certificate(h, stored_hash, details)
        status = verification_result["status"]  # "VALID", "PARTIALLY_MATCHED", or "FAKE"
        details["verification_result"] = verification_result # Store it to use in the route
        logger.info(f"Verification result for {certificate_id}: {status}")
    else:
        # New certificate - store it
        ledger_service.store_certificate(certificate_id, h)
        status = "NEWLY REGISTERED"
        logger.info(f"New certificate registered: {certificate_id}")
    
    logger.info(f"Processed upload: {filename}, hash: {h[:16]}..., status: {status}")
    return details, h, status


def _build_result(details, cert_hash, verification, action) -> dict:
    def _get(keys, default="Not Extracted"):
        for k in keys:
            val = details.get(k)
            if val and str(val).strip() and str(val).strip().lower() not in ["not extracted", "none", "null"]:
                return str(val).strip()
        return default

    date_val = _get(["date", "issue_date", "year", "completion_date", "issued_on"], "Not Mentioned")
    cert_id  = _get(["certificate_id", "cert_id", "id", "credential_id"], f"CERT-{cert_hash[:9].upper()}")
    course_value = _get(["course", "certificate_title", "course_title", "title", "course_name", "certification", "program"], "Not Extracted")
    name_value = _get(["name", "candidate_name", "student_name", "recipient"], "Not Extracted")
    issuer_value = _get(["issuing_authority", "issuer", "organization", "institution", "issued_by"], "Not Extracted")
    
    return {
        "action":           action,
        "status":           verification.get("status", "UNKNOWN"),
        "label":            verification.get("label", "UNKNOWN"),
        "color":            verification.get("color", "grey"),
        "message":          verification.get("message", ""),
        "explanation":      verification.get("explanation", ""),
        "confidence_score": verification.get("confidence_score", details.get("confidence_score", 0)),
        "name":             name_value,
        "course":           course_value,
        "issuing_authority": issuer_value,
        "date":             date_val,
        "cert_id":          cert_id,
        "hash":             cert_hash,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/issue", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def issue():
    if request.method == "GET":
        return render_template("upload.html", action="issue")

    if not SERVICES_OK:
        return render_template("upload.html", action="issue",
                               error="Backend services unavailable.")

    file = request.files.get("certificate")
    if not file or not file.filename or not allowed_file(file.filename):
        return render_template("upload.html", action="issue",
                               error="Please upload a valid file (PNG, JPG, PDF, DOCX).")
    try:
        details, cert_hash, verification_status = _process_upload(file)
        
        # Prevent duplicate issuance
        if verification_status != "NEWLY REGISTERED":
            vr = details.get("verification_result", {})
            return render_template("upload.html", action="issue",
                                   error="This certificate has already been issued and recorded on the blockchain.", 
                                   error_type="duplicate",
                                   duplicate_details=details,
                                   duplicate_vr=vr)

        status = issue_certificate(cert_hash, details, blockchain)
        token = upsert_certificate(cert_hash, details, action="ISSUE")

        # Proxy-aware URL generation
        forwarded_proto = request.headers.get("X-Forwarded-Proto", request.scheme)
        forwarded_host = request.headers.get("X-Forwarded-Host", request.host)
        base_url = f"{forwarded_proto}://{forwarded_host}".rstrip("/")
        
        qr_data = generate_qr_base64(token, base_url, is_token=True)

        already = status == "ALREADY REGISTERED"
        
        # Build verification object based on our new verification system
        vr = details.get("verification_result", {})
        
        if verification_status == "NEWLY REGISTERED":
            verification = {
                "status":           "NEWLY_REGISTERED",
                "label":            "✓ Newly Registered",
                "color":            "blue",
                "message":          "Certificate successfully registered and verified.",
                "explanation":      "Extracted successfully and added to the blockchain ledger.",
                "confidence_score": details.get("confidence_score", 0),
            }
        elif verification_status == "VALID":
            verification = {
                "status":           "VALID",
                "label":            "✓ Valid Certificate",
                "color":            "green",
                "message":          vr.get("message", "Certificate is authentic and valid."),
                "explanation":      vr.get("explanation", "Exact Blockchain Match"),
                "confidence_score": vr.get("confidence_score", details.get("confidence_score", 0)),
            }
        elif verification_status == "PARTIALLY_MATCHED":
            verification = {
                "status":           "PARTIALLY_MATCHED",
                "label":            "⚠ Partial Match",
                "color":            "orange",
                "message":          vr.get("message", "Partial Metadata Match"),
                "explanation":      vr.get("explanation", "Fuzzy metadata matched, but hash differs."),
                "confidence_score": vr.get("confidence_score", details.get("confidence_score", 0)),
            }
        else:  # FAKE
            verification = {
                "status":           "FAKE",
                "label":            "✗ Fake Certificate",
                "color":            "red",
                "message":          vr.get("message", "Certificate appears to be fake or altered."),
                "explanation":      vr.get("explanation", "Hash failed and metadata did not match."),
                "confidence_score": vr.get("confidence_score", min(details.get("confidence_score", 0), 55.0)),
            }
        
        result = _build_result(details, cert_hash, verification, "ISSUE")
        result["qr_data"] = qr_data
        result["token"] = token
        
        # Log outcome
        log_verification("ISSUE", cert_hash, verification["status"], request.remote_addr, request.user_agent.string, "Certificate issued")
        
        return render_template("result.html", **result)
    except Exception as e:
        logger.error("Issue route: %s", e)
        return render_template("upload.html", action="issue",
                               error=f"Processing failed: {e}")

@app.route("/verify", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def verify():
    if request.method == "GET":
        return render_template("upload.html", action="verify")

    if not SERVICES_OK:
        return render_template("upload.html", action="verify",
                               error="Backend services unavailable.")

    file = request.files.get("certificate")
    if not file or not file.filename or not allowed_file(file.filename):
        return render_template("upload.html", action="verify",
                               error="Please upload a valid file (PNG, JPG, PDF, DOCX).")
    try:
        details, cert_hash, verification_status = _process_upload(file)
        
        # Build verification object based on our new verification system
        vr = details.get("verification_result", {})
        
        if verification_status == "NEWLY REGISTERED":
            verification = {
                "status":           "NEWLY_REGISTERED",
                "label":            "✓ Newly Registered",
                "color":            "blue",
                "message":          "Certificate successfully registered and verified.",
                "explanation":      "Extracted successfully and added to the blockchain ledger.",
                "confidence_score": details.get("confidence_score", 0),
            }
        elif verification_status == "VALID":
            verification = {
                "status":           "VALID",
                "label":            "✓ Valid Certificate",
                "color":            "green",
                "message":          vr.get("message", "Certificate is authentic and valid."),
                "explanation":      vr.get("explanation", "Exact Blockchain Match"),
                "confidence_score": vr.get("confidence_score", details.get("confidence_score", 0)),
            }
        elif verification_status == "PARTIALLY_MATCHED":
            verification = {
                "status":           "PARTIALLY_MATCHED",
                "label":            "⚠ Partial Match",
                "color":            "orange",
                "message":          vr.get("message", "Partial Metadata Match"),
                "explanation":      vr.get("explanation", "Fuzzy metadata matched, but hash differs."),
                "confidence_score": vr.get("confidence_score", details.get("confidence_score", 0)),
            }
        else:  # FAKE
            verification = {
                "status":           "FAKE",
                "label":            "✗ Fake Certificate",
                "color":            "red",
                "message":          vr.get("message", "Certificate appears to be fake or altered."),
                "explanation":      vr.get("explanation", "Hash failed and metadata did not match."),
                "confidence_score": vr.get("confidence_score", min(details.get("confidence_score", 0), 55.0)),
            }
        
        token = upsert_certificate(cert_hash, details, action="VERIFY")
        result = _build_result(details, cert_hash, verification, "VERIFY")
        result["token"] = token
        
        # Log outcome
        log_verification("VERIFY", cert_hash, verification["status"], request.remote_addr, request.user_agent.string, "Certificate verified manually")
        
        return render_template("result.html", **result)
    except Exception as e:
        logger.error("Verify route: %s", e)
        return render_template("upload.html", action="verify",
                               error=f"Processing failed: {e}")
@app.route("/certificate/<cert_hash>")
def certificate_view(cert_hash: str):
    if not SERVICES_OK:
        abort(503)
    from backend.database.db import get_certificate_by_hash
    record = get_certificate_by_hash(cert_hash)
    if not record:
        log_verification("VIEW", cert_hash, "MISSING", request.remote_addr, request.user_agent.string, "Record missing from DB")
        return render_template("upload.html", action="verify", error="Certificate not found in database or ledger. It may be invalid or not issued yet.")
        
    # Dynamically verify against blockchain
    block = blockchain.find_by_hash(cert_hash)
    if block:
        verification = {
            "status":           "VALID",
            "label":            "✓ Valid Historical Record",
            "color":            "green",
            "message":          "Certificate is authentic and valid.",
            "explanation":      "Retrieved from immutable ledger and dynamically verified.",
            "confidence_score": record.get("confidence_score", 100.0),
        }
    else:
        # DB record exists but blockchain doesn't have it -> TAMPERED!
        verification = {
            "status":           "FAKE",
            "label":            "✗ Tampered Record",
            "color":            "red",
            "message":          "Blockchain integrity check failed.",
            "explanation":      "This record exists in the database but may have been tampered with or corrupted.",
            "confidence_score": 0.0,
        }
    
    log_verification("VIEW", cert_hash, verification["status"], request.remote_addr, request.user_agent.string, "Viewed via hash")
    result = _build_result(record, cert_hash, verification, "VERIFY")
    return render_template("result.html", **result)


@app.route("/verify_token/<token>")
def verify_token_view(token: str):
    if not SERVICES_OK:
        abort(503)
        
    record = get_certificate_by_token(token)
    if not record:
        log_verification("TOKEN_VIEW", "unknown", "MISSING", request.remote_addr, request.user_agent.string, f"Token not found: {token}")
        return render_template("upload.html", action="verify", error="Invalid verification token. The certificate cannot be found.")
        
    cert_hash = record["cert_hash"]
    
    # Dynamically verify against blockchain
    block = blockchain.find_by_hash(cert_hash)
    if block:
        verification = {
            "status":           "VALID",
            "label":            "✓ Valid Certificate",
            "color":            "green",
            "message":          "Certificate is authentic and valid.",
            "explanation":      "Retrieved securely via token and verified against the immutable ledger.",
            "confidence_score": record.get("confidence_score", 100.0),
        }
    else:
        # DB record exists but blockchain doesn't have it -> TAMPERED!
        verification = {
            "status":           "FAKE",
            "label":            "✗ Tampered / Corrupted Record",
            "color":            "red",
            "message":          "Blockchain integrity check failed.",
            "explanation":      "This record exists in the database but is missing from the blockchain. It may have been tampered with or revoked.",
            "confidence_score": 0.0,
        }
        
    log_verification("TOKEN_VIEW", cert_hash, verification["status"], request.remote_addr, request.user_agent.string, "Viewed via secure token")
    result = _build_result(record, cert_hash, verification, "VERIFY")
    return render_template("result.html", **result)

@app.route("/report/<cert_hash>")
def download_report(cert_hash: str):
    if not SERVICES_OK:
        abort(503)
    from backend.database.db import get_certificate_by_hash
    record = get_certificate_by_hash(cert_hash)
    if not record:
        abort(404)

    # Check blockchain for original details to ensure we didn't lose fields in DB columns
    block = blockchain.find_by_hash(cert_hash)
    if block and "data" in block:
        # Merge blockchain data with DB record for maximum field coverage
        for k, v in block["data"].items():
            if k not in record or not record[k]:
                record[k] = v

    verification = {
        "status":       "VALID" if record.get("action") else "UNKNOWN",
        "label":        "✓ Valid Certificate" if record.get("action") else "UNKNOWN",
        "color":        "green" if record.get("action") else "grey",
        "message":      "Valid Historical Record",
        "explanation":  "Retrieved from immutable ledger.",
        "confidence_score": record.get("confidence_score", 95.0),
    }
    
    result = _build_result(record, cert_hash, verification, record.get("action", "VERIFY"))
    result["token"] = record.get("verification_token")
    
    path = generate_report(result, base_url=request.host_url.rstrip("/"))
    if not path or not os.path.exists(path):
        logger.error(f"Failed to generate report for {cert_hash}. path={path}")
        return render_template("upload.html", action="verify", error="Failed to generate the PDF report due to a server error. Please check dependencies or logs.")
    return send_file(path, as_attachment=True, download_name=f"report_{cert_hash[:12]}.pdf")


@app.route("/ledger")
def ledger():
    if not SERVICES_OK:
        return render_template("ledger.html", records=[], chain_valid=False)
    records     = get_all_certificates()
    chain_valid = blockchain.is_valid()
    return render_template("ledger.html", records=records, chain_valid=chain_valid)


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.route("/api/issue", methods=["POST"])
@limiter.limit("10 per minute")
def api_issue():
    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or missing file"}), 400
    try:
        details, cert_hash, verification_status = _process_upload(file)
        
        # Prevent duplicate issuance
        if verification_status != "NEWLY REGISTERED":
            return jsonify({"error": "This certificate has already been issued and recorded on the blockchain.", "code": "DUPLICATE_CERTIFICATE"}), 409

        status = issue_certificate(cert_hash, details, blockchain)
        upsert_certificate(cert_hash, details, action="ISSUE")
        
        # Build verification object based on our new verification system
        if verification_status == "NEWLY REGISTERED":
            verification = {
                "status": "NEWLY_REGISTERED", 
                "label": "✓ Newly Registered",
                "color": "blue", 
                "message": "Certificate successfully registered and verified.",
                "confidence_score": details.get("confidence_score", 0),
            }
        elif verification_status == "VALID":
            verification = {
                "status": "VALID", 
                "label": "✓ Valid Certificate",
                "color": "green", 
                "message": "Certificate is authentic and valid.",
                "confidence_score": details.get("confidence_score", 0),
            }
        else:  # FAKE
            verification = {
                "status": "FAKE", 
                "label": "✗ Fake Certificate",
                "color": "red", 
                "message": "Certificate appears to be fake or altered.",
                "confidence_score": details.get("confidence_score", 0),
            }
        
        result = _build_result(details, cert_hash, verification, "ISSUE")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/verify", methods=["POST"])
@limiter.limit("20 per minute")
def api_verify():
    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or missing file"}), 400
    try:
        details, cert_hash, verification_status = _process_upload(file)
        
        # Build verification object based on our new verification system
        if verification_status == "NEWLY REGISTERED":
            verification = {
                "status": "NEWLY_REGISTERED", 
                "label": "✓ Newly Registered",
                "color": "blue", 
                "message": "Certificate successfully registered and verified.",
                "confidence_score": details.get("confidence_score", 0),
            }
        elif verification_status == "VALID":
            verification = {
                "status": "VALID", 
                "label": "✓ Valid Certificate",
                "color": "green", 
                "message": "Certificate is authentic and valid.",
                "confidence_score": details.get("confidence_score", 0),
            }
        else:  # FAKE
            verification = {
                "status": "FAKE", 
                "label": "✗ Fake Certificate",
                "color": "red", 
                "message": "Certificate appears to be fake or altered.",
                "confidence_score": details.get("confidence_score", 0),
            }
        
        upsert_certificate(cert_hash, details, action="VERIFY")
        result = _build_result(details, cert_hash, verification, "VERIFY")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export", methods=["GET"])
@limiter.limit("5 per day")
def api_export():
    # Admin-only / disabled in production
    # To enable, set ENABLE_ADMIN_EXPORT=true in the environment.
    if os.environ.get("ENABLE_ADMIN_EXPORT", "false").lower() != "true":
        abort(403, description="Export route is disabled in production for security.")
        
    try:
        from backend.database.db import get_all_certificates
        import json
        
        records = get_all_certificates()
        bc_data = blockchain.chain
        
        export_data = {
            "database_records": records,
            "blockchain_blocks": bc_data
        }
        
        return jsonify(export_data)
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/blockchain")
def api_blockchain():
    return jsonify({
        "blocks": len(blockchain.chain),
        "valid":  blockchain.is_valid(),
        "chain":  blockchain.chain,
    })


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV", "development").lower() == "development"
    app.run(debug=debug_mode, use_reloader=False, host="0.0.0.0", port=5000)
