"""
Certificate Authentication System — Flask Application
Smart Certificate Authentication Using Blockchain and AI Validation
"""
import logging
import os
import re
import secrets

from flask import Flask, jsonify, render_template, request, send_file, abort
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Logging — INFO in production, DEBUG only in development
# ---------------------------------------------------------------------------
_log_level = logging.DEBUG if os.environ.get("FLASK_ENV", "production").lower() == "development" else logging.INFO
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

import sys
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Startup Validation — fail fast with clear messages
# ---------------------------------------------------------------------------
if not os.environ.get("GEMINI_API_KEY"):
    logger.critical("FATAL: GEMINI_API_KEY environment variable is missing. Cannot start application.")
    sys.exit(1)

is_production = os.environ.get("FLASK_ENV", "production").lower() != "development"
if is_production and not os.environ.get("BASE_URL"):
    raise RuntimeError("BASE_URL not configured in production — set BASE_URL env var to your Render URL")

# ---------------------------------------------------------------------------
# Flask App Initialization
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "docx"}

# Regex for validating SHA-256 hashes and UUIDs in URL params
_HASH_RE  = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[0-9a-f-]{36}$")   # UUID v4

# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------
@app.after_request
def add_security_headers(response):
    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # HSTS — let Render/CDN handle for HTTPS but add defensively
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Referrer policy — prevents leaking path/query to third-party sites
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Permissions policy — restrict dangerous browser features
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Content-Security-Policy — restrict script/style sources, prevent XSS
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "   # unsafe-inline needed for inline scripts in templates
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "                # data: needed for base64 QR codes
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response


# ---------------------------------------------------------------------------
# Service bootstrap
# ---------------------------------------------------------------------------

def _load_services():
    from services.extractor          import extract_details
    from backend.utils.hashing       import generate_hash_from_details
    from backend.utils.verification  import classify_status, issue_certificate
    from backend.utils.blockchain    import Blockchain
    from backend.utils.qr_generator  import generate_qr_base64
    from backend.utils.report_generator import generate_report
    from backend.database.db         import init_db, upsert_certificate, get_all_certificates, log_verification, get_certificate_by_token

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


def _validate_hash(cert_hash: str) -> bool:
    """Return True only if cert_hash is a valid 64-char lowercase hex SHA-256."""
    return bool(_HASH_RE.match(cert_hash))


def _validate_token(token: str) -> bool:
    """Return True only if token matches UUID v4 format."""
    return bool(_TOKEN_RE.match(token))


def _process_upload(file, mode: str = "issue") -> tuple[dict, str, str]:
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    try:
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
            details["verification_result"] = verification_result
            logger.info("Verification result for cert_id=%s: status=%s", certificate_id, status)
        else:
            if mode == "issue":
                # New certificate - store it (issuance only)
                ledger_service.store_certificate(certificate_id, h)
                status = "NEWLY REGISTERED"
                logger.info("New certificate registered: cert_id=%s", certificate_id)
            else:
                # Verification mode - do NOT register unknown certificates
                status = "NOT REGISTERED"
                logger.info("Certificate not found in ledger (verify mode): cert_id=%s", certificate_id)

        logger.info("Processed upload: filename=%s, hash_prefix=%s, status=%s", filename, h[:16], status)
        return details, h, status
    finally:
        # Always delete the uploaded file after processing — never retain user documents on disk.
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info("Deleted uploaded file after processing: %s", filename)
        except Exception as _cleanup_err:
            logger.warning("Failed to delete uploaded file %s: %s", filepath, _cleanup_err)


def _build_result(details, cert_hash, verification, action) -> dict:
    def _get(keys, default="Not Extracted"):
        for k in keys:
            val = details.get(k)
            if val and str(val).strip() and str(val).strip().lower() not in ["not extracted", "none", "null"]:
                return str(val).strip()
        return default

    date_val     = _get(["date", "issue_date", "year", "completion_date", "issued_on"], "Not Mentioned")
    cert_id      = _get(["certificate_id", "cert_id", "id", "credential_id"], f"CERT-{cert_hash[:9].upper()}")
    course_value = _get(["course", "certificate_title", "course_title", "title", "course_name", "certification", "program"], "Not Extracted")
    name_value   = _get(["name", "candidate_name", "student_name", "recipient"], "Not Extracted")
    issuer_value = _get(["issuing_authority", "issuer", "organization", "institution", "issued_by"], "Not Extracted")

    return {
        "action":            action,
        "status":            verification.get("status", "UNKNOWN"),
        "label":             verification.get("label", "UNKNOWN"),
        "color":             verification.get("color", "grey"),
        "message":           verification.get("message", ""),
        "explanation":       verification.get("explanation", ""),
        "confidence_score":  verification.get("confidence_score", details.get("confidence_score", 0)),
        "name":              name_value,
        "course":            course_value,
        "issuing_authority": issuer_value,
        "date":              date_val,
        "cert_id":           cert_id,
        "hash":              cert_hash,
    }


def _build_verification_dict(verification_status: str, details: dict) -> dict:
    """Build the verification dict from the processing status string."""
    vr = details.get("verification_result", {})
    if verification_status == "NEWLY REGISTERED":
        return {
            "status":           "NEWLY_REGISTERED",
            "label":            "✓ Newly Registered",
            "color":            "blue",
            "message":          "Certificate successfully registered and verified.",
            "explanation":      "Extracted successfully and added to the blockchain ledger.",
            "confidence_score": details.get("confidence_score", 0),
        }
    elif verification_status == "NOT REGISTERED":
        return {
            "status":           "NOT_REGISTERED",
            "label":            "✗ Not Registered",
            "color":            "red",
            "message":          "Certificate not found in any trusted registry.",
            "explanation":      "This certificate has not been issued through the system. It cannot be verified.",
            "confidence_score": 0.0,
        }
    elif verification_status == "VALID":
        return {
            "status":           "VALID",
            "label":            "✓ Valid Certificate",
            "color":            "green",
            "message":          vr.get("message", "Certificate is authentic and valid."),
            "explanation":      vr.get("explanation", "Exact Blockchain Match"),
            "confidence_score": vr.get("confidence_score", details.get("confidence_score", 0)),
        }
    elif verification_status == "PARTIALLY_MATCHED":
        return {
            "status":           "PARTIALLY_MATCHED",
            "label":            "⚠ Partial Match",
            "color":            "orange",
            "message":          vr.get("message", "Partial Metadata Match"),
            "explanation":      vr.get("explanation", "Fuzzy metadata matched, but hash differs."),
            "confidence_score": vr.get("confidence_score", details.get("confidence_score", 0)),
        }
    else:  # FAKE
        return {
            "status":           "FAKE",
            "label":            "✗ Fake Certificate",
            "color":            "red",
            "message":          vr.get("message", "Certificate appears to be fake or altered."),
            "explanation":      vr.get("explanation", "Hash failed and metadata did not match."),
            "confidence_score": vr.get("confidence_score", min(details.get("confidence_score", 0), 55.0)),
        }


# ---------------------------------------------------------------------------
# Custom Error Handlers
# ---------------------------------------------------------------------------

@app.errorhandler(400)
def bad_request(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Bad request"}), 400
    return render_template("errors/400.html"), 400

@app.errorhandler(403)
def forbidden(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Forbidden"}), 403
    return render_template("errors/403.html"), 403

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("errors/404.html"), 404

@app.errorhandler(413)
def request_too_large(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "File too large — maximum 16 MB"}), 413
    return render_template("upload.html", action="verify",
                           error="The uploaded file exceeds the 16 MB size limit. Please upload a smaller file."), 413

@app.errorhandler(429)
def rate_limited(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Too many requests — slow down"}), 429
    return render_template("errors/429.html"), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error("Internal server error: %s", e, exc_info=True)
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("errors/500.html"), 500

@app.errorhandler(503)
def service_unavailable(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Service unavailable"}), 503
    return render_template("errors/503.html"), 503


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
                               error="Backend services are currently unavailable. Please try again later.")

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
        token  = upsert_certificate(cert_hash, details, action="ISSUE")

        # Determine trusted base URL for QR code generation
        if is_production:
            env_base_url = os.environ.get("BASE_URL")
            if not env_base_url:
                raise RuntimeError("BASE_URL not configured in production")
            base_url = env_base_url.rstrip("/")
        else:
            base_url = request.host_url.rstrip("/")

        qr_data = generate_qr_base64(token, base_url, is_token=True)

        verification = _build_verification_dict(verification_status, details)
        result = _build_result(details, cert_hash, verification, "ISSUE")
        result["qr_data"] = qr_data
        result["token"]   = token

        # Log outcome — do not log raw user agent string at INFO level
        log_verification("ISSUE", cert_hash, verification["status"],
                         request.remote_addr, request.user_agent.platform or "unknown", "Certificate issued")

        return render_template("result.html", **result)
    except Exception as e:
        logger.error("Issue route processing error: %s", e, exc_info=True)
        return render_template("upload.html", action="issue",
                               error="Processing failed. Please check that your file is a valid certificate and try again.")


@app.route("/verify", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def verify():
    if request.method == "GET":
        return render_template("upload.html", action="verify")

    if not SERVICES_OK:
        return render_template("upload.html", action="verify",
                               error="Backend services are currently unavailable. Please try again later.")

    file = request.files.get("certificate")
    if not file or not file.filename or not allowed_file(file.filename):
        return render_template("upload.html", action="verify",
                               error="Please upload a valid file (PNG, JPG, PDF, DOCX).")
    try:
        details, cert_hash, verification_status = _process_upload(file, mode="verify")

        verification = _build_verification_dict(verification_status, details)
        # Only write to DB if the certificate is already trusted (found in ledger/blockchain)
        if verification_status in ("VALID", "PARTIALLY_MATCHED", "FAKE"):
            token = upsert_certificate(cert_hash, details, action="VERIFY")
        else:
            token = None
        result = _build_result(details, cert_hash, verification, "VERIFY")
        result["token"] = token

        log_verification("VERIFY", cert_hash, verification["status"],
                         request.remote_addr, request.user_agent.platform or "unknown", "Certificate verified manually")

        return render_template("result.html", **result)
    except Exception as e:
        logger.error("Verify route processing error: %s", e, exc_info=True)
        return render_template("upload.html", action="verify",
                               error="Processing failed. Please check that your file is a valid certificate and try again.")


@app.route("/certificate/<cert_hash>")
def certificate_view(cert_hash: str):
    # Validate hash format before any DB/blockchain query
    if not _validate_hash(cert_hash):
        abort(400)

    if not SERVICES_OK:
        abort(503)

    from backend.database.db import get_certificate_by_hash
    record = get_certificate_by_hash(cert_hash)
    if not record:
        log_verification("VIEW", cert_hash, "MISSING",
                         request.remote_addr, request.user_agent.platform or "unknown", "Record missing from DB")
        return render_template("upload.html", action="verify",
                               error="Certificate not found in database or ledger. It may be invalid or not issued yet.")

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
        # DB record exists but blockchain doesn't have it → TAMPERED
        verification = {
            "status":           "FAKE",
            "label":            "✗ Tampered Record",
            "color":            "red",
            "message":          "Blockchain integrity check failed.",
            "explanation":      "This record exists in the database but may have been tampered with or corrupted.",
            "confidence_score": 0.0,
        }

    log_verification("VIEW", cert_hash, verification["status"],
                     request.remote_addr, request.user_agent.platform or "unknown", "Viewed via hash")
    result = _build_result(record, cert_hash, verification, "VERIFY")
    return render_template("result.html", **result)


@app.route("/verify_token/<token>")
def verify_token_view(token: str):
    # Validate token format before any DB query
    if not _validate_token(token):
        abort(400)

    if not SERVICES_OK:
        abort(503)

    record = get_certificate_by_token(token)
    if not record:
        log_verification("TOKEN_VIEW", "unknown", "MISSING",
                         request.remote_addr, request.user_agent.platform or "unknown", "Token not found")
        return render_template("upload.html", action="verify",
                               error="Invalid verification token. The certificate cannot be found.")

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
        # DB record exists but blockchain doesn't have it → TAMPERED
        verification = {
            "status":           "FAKE",
            "label":            "✗ Tampered / Corrupted Record",
            "color":            "red",
            "message":          "Blockchain integrity check failed.",
            "explanation":      "This record exists in the database but is missing from the blockchain. It may have been tampered with or revoked.",
            "confidence_score": 0.0,
        }

    log_verification("TOKEN_VIEW", cert_hash, verification["status"],
                     request.remote_addr, request.user_agent.platform or "unknown", "Viewed via secure token")
    result = _build_result(record, cert_hash, verification, "VERIFY")
    return render_template("result.html", **result)


@app.route("/report/<cert_hash>")
@limiter.limit("10 per minute")
def download_report(cert_hash: str):
    # Validate hash format
    if not _validate_hash(cert_hash):
        abort(400)

    if not SERVICES_OK:
        abort(503)

    # Extract credentials
    provided_token = request.args.get("token", "").strip()
    admin_key      = request.headers.get("X-Admin-Key", "").strip()
    expected_admin = (os.environ.get("ADMIN_API_KEY") or "").strip()

    # Fetch record early
    from backend.database.db import get_certificate_by_hash
    record = get_certificate_by_hash(cert_hash)
    if not record:
        abort(404)

    # Normalize token safely
    record_token = (record.get("verification_token") or "").strip()

    # Validate access strictly (NO shortcuts, NO truthy checks)
    valid_token = (
        provided_token != ""
        and record_token != ""
        and provided_token == record_token
    )

    valid_admin = (
        expected_admin != ""
        and admin_key != ""
        and admin_key == expected_admin
    )

    # Authorization rule (STRICT DENY FIRST)
    if not (valid_token or valid_admin):
        abort(403)

    # Check blockchain for original details to ensure maximum field coverage
    block = blockchain.find_by_hash(cert_hash)
    if block and "data" in block:
        for k, v in block["data"].items():
            if k not in record or not record[k]:
                record[k] = v

    verification = {
        "status":           "VALID" if record.get("action") else "UNKNOWN",
        "label":            "✓ Valid Certificate" if record.get("action") else "UNKNOWN",
        "color":            "green" if record.get("action") else "grey",
        "message":          "Valid Historical Record",
        "explanation":      "Retrieved from immutable ledger.",
        "confidence_score": record.get("confidence_score", 95.0),
    }

    result = _build_result(record, cert_hash, verification, record.get("action", "VERIFY"))
    result["token"] = record.get("verification_token")

    path = generate_report(result, base_url=request.host_url.rstrip("/"))
    if not path or not os.path.exists(path):
        logger.error("Failed to generate report for hash_prefix=%s", cert_hash[:12])
        return render_template("upload.html", action="verify",
                               error="Failed to generate the PDF report. Please try again or contact support.")

    # Clean up the PDF after sending to avoid disk accumulation
    from flask import after_this_request

    @after_this_request
    def cleanup_pdf(response):
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info("Cleaned up report PDF after download: %s", os.path.basename(path))
        except Exception as _err:
            logger.warning("Could not clean up report PDF %s: %s", path, _err)
        return response

    return send_file(path, as_attachment=True, download_name=f"report_{cert_hash[:12]}.pdf")


@app.route("/ledger")
def ledger():
    # Require ADMIN_API_KEY via X-Admin-Key header (NOT query param — query params appear in logs)
    if os.environ.get("FLASK_ENV", "production").lower() != "development":
        admin_key    = request.headers.get("X-Admin-Key", "").strip()
        expected_key = os.environ.get("ADMIN_API_KEY", "")
        if not expected_key or admin_key != expected_key:
            abort(403)
    if not SERVICES_OK:
        return render_template("ledger.html", records=[], chain_valid=False)
    records     = get_all_certificates()
    chain_valid = blockchain.is_valid()
    return render_template("ledger.html", records=records, chain_valid=chain_valid)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.route("/api/issue", methods=["POST"])
@limiter.limit("10 per minute")
def api_issue():
    if not SERVICES_OK:
        return jsonify({"error": "Service unavailable"}), 503

    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or missing file"}), 400
    try:
        details, cert_hash, verification_status = _process_upload(file)

        # Prevent duplicate issuance
        if verification_status != "NEWLY REGISTERED":
            return jsonify({
                "error": "This certificate has already been issued and recorded on the blockchain.",
                "code":  "DUPLICATE_CERTIFICATE"
            }), 409

        issue_certificate(cert_hash, details, blockchain)
        upsert_certificate(cert_hash, details, action="ISSUE")

        verification = _build_verification_dict(verification_status, details)
        result = _build_result(details, cert_hash, verification, "ISSUE")
        return jsonify(result)
    except Exception as e:
        logger.error("API issue error: %s", e, exc_info=True)
        return jsonify({"error": "Processing failed. Please try again."}), 500


@app.route("/api/verify", methods=["POST"])
@limiter.limit("20 per minute")
def api_verify():
    if not SERVICES_OK:
        return jsonify({"error": "Service unavailable"}), 503

    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or missing file"}), 400
    try:
        details, cert_hash, verification_status = _process_upload(file, mode="verify")

        verification = _build_verification_dict(verification_status, details)
        # Only write to DB if the certificate is already trusted
        if verification_status in ("VALID", "PARTIALLY_MATCHED", "FAKE"):
            upsert_certificate(cert_hash, details, action="VERIFY")
        result = _build_result(details, cert_hash, verification, "VERIFY")
        return jsonify(result)
    except Exception as e:
        logger.error("API verify error: %s", e, exc_info=True)
        return jsonify({"error": "Processing failed. Please try again."}), 500


@app.route("/api/export", methods=["GET"])
@limiter.limit("5 per day")
def api_export():
    # Admin-only / disabled in production by default
    if os.environ.get("ENABLE_ADMIN_EXPORT", "false").lower() != "true":
        abort(403)

    # Require admin key even when enabled
    admin_key    = request.headers.get("X-Admin-Key", "").strip()
    expected_key = (os.environ.get("ADMIN_API_KEY") or "").strip()
    if not expected_key or admin_key != expected_key:
        abort(403)

    try:
        from backend.database.db import get_all_certificates as _get_all
        records = _get_all()
        bc_data = blockchain.chain
        return jsonify({
            "database_records":  records,
            "blockchain_blocks": bc_data,
        })
    except Exception as e:
        logger.error("Export failed: %s", e, exc_info=True)
        return jsonify({"error": "Export failed"}), 500


@app.route("/api/blockchain")
def api_blockchain():
    admin_key    = request.headers.get("X-Admin-Key", "")
    expected_key = os.environ.get("ADMIN_API_KEY", "")
    if expected_key and admin_key == expected_key:
        # Admin request: return full chain data
        return jsonify({
            "blocks": len(blockchain.chain),
            "valid":  blockchain.is_valid(),
            "chain":  blockchain.chain,
        })
    # Public request: return health stats only — no personal data exposed
    return jsonify({
        "blocks": len(blockchain.chain),
        "valid":  blockchain.is_valid(),
    })


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV", "development").lower() == "development"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, use_reloader=False, host="0.0.0.0", port=port)
