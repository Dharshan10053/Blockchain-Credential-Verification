import os
import base64
import json
import logging
import re
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

def validate_extracted_data(data: dict) -> dict:
    """
    Validate and clean extracted certificate data.
    Ensures data integrity and removes invalid values.
    """
    if not isinstance(data, dict):
        logger.warning("Invalid data type received for validation")
        return {
            "name": None,
            "certificate_title": None,
            "issuer": None,
            "date": None,
            "certificate_id": None,
            "confidence_score": 0.0
        }
    
    # Generic invalid values to filter out
    invalid_values = {
        "certificate", "completion", "achievement", "certified", 
        "award", "recognition", "program", "course"
    }
    
    def clean_string(value):
        """Clean and validate string values"""
        if value is None:
            return None
        
        if not isinstance(value, str):
            value = str(value)
        
        # Strip whitespace
        value = value.strip()
        
        # Check for invalid generic phrases
        if value.lower() in invalid_values:
            return None
        
        # Filter out very short or meaningless strings
        if len(value) < 2:
            return None
            
        return value if value else None
    
    # Extract and clean all fields
    name = clean_string(data.get("name"))
    certificate_title = clean_string(data.get("certificate_title"))
    issuer = clean_string(data.get("issuer"))
    date = clean_string(data.get("date"))
    certificate_id = clean_string(data.get("certificate_id"))
    confidence_score = data.get("confidence_score", 0.0)
    
    # Critical validation: issuer != name
    if issuer and name and issuer.lower() == name.lower():
        logger.info(f"Issuer '{issuer}' matches name '{name}', setting issuer to null")
        issuer = None
    
    # Additional validation: certificate_title shouldn't be generic
    if certificate_title and certificate_title.lower() in invalid_values:
        logger.info(f"Certificate title '{certificate_title}' is too generic, setting to null")
        certificate_title = None
    
    validated_data = {
        "name": name,
        "certificate_title": certificate_title,
        "issuer": issuer,
        "date": date,
        "certificate_id": certificate_id,
        "confidence_score": float(confidence_score) if confidence_score else 0.0
    }
    
    logger.info(f"Validated data: name={name}, issuer={issuer}, course={certificate_title}")
    return validated_data

def _image_to_base64(filepath: str) -> str:
    try:
        with Image.open(filepath) as img:
            # Convert to RGB in case it's RGBA or something else
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to process image {filepath}: {str(e)}")
        raise ValueError(f"Image processing failed: {str(e)}")

def _pdf_to_base64(filepath: str) -> str:
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(filepath, dpi=200, first_page=1, last_page=1)
        if not images:
            raise ValueError("Could not extract image from PDF")
        img = images[0]
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to process PDF {filepath}: {str(e)}")
        raise ValueError(f"PDF processing failed: {str(e)}")

def _docx_to_base64(filepath: str) -> str:
    try:
        import tempfile
        from docx2pdf import convert
        
        # We create a temporary PDF file
        temp_pdf = os.path.join(tempfile.gettempdir(), os.path.basename(filepath) + ".pdf")
        try:
            convert(filepath, temp_pdf)
            return _pdf_to_base64(temp_pdf)
        finally:
            # Clean up temporary file
            if os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Failed to process DOCX {filepath}: {str(e)}")
        raise ValueError(f"DOCX processing failed: {str(e)}")

def extract_details(filepath: str) -> dict:
    """
    Process the input file (Image/PDF/DOCX), convert to base64,
    and extract structured JSON using Gemini multimodal API.
    """
    logger.info(f"Extracting details directly from image via AI for {filepath}")
    
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext in (".png", ".jpg", ".jpeg"):
        base64_image = _image_to_base64(filepath)
    elif ext == ".pdf":
        base64_image = _pdf_to_base64(filepath)
    elif ext == ".docx":
        base64_image = _docx_to_base64(filepath)
    else:
        raise ValueError(f"Unsupported file type for extraction: {ext}")
    
    # DEBUG: Log base64 image size and confirmation
    logger.info(f"DEBUG: Base64 image size: {len(base64_image)} characters")
    logger.info(f"DEBUG: Base64 image preview: {base64_image[:100]}...")
    logger.info(f"DEBUG: Image successfully converted and ready for API call")

    import google.generativeai as genai
    import re
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        # Convert base64 string to bytes for Gemini
        image_bytes = base64.b64decode(base64_image)
        
        prompt = """
You are a strict document parser.

Extract the following fields from the certificate image:
- name
- course
- issuer
- date
- certificate_id

Return ONLY valid JSON.
No explanation.
No markdown.
No extra text.

Example:
{
  "name": "John Doe",
  "course": "Python",
  "issuer": "ABC Institute",
  "date": "2022-10-18",
  "certificate_id": "XYZ123"
}
"""

        response = model.generate_content([
            prompt,
            {
                "mime_type": "image/jpeg",
                "data": image_bytes
            }
        ])
        
        content = response.text
        
        # DEBUG: Print RAW response
        logger.info(f"Raw Gemini response: {content[:200]}...")
        
        # Extract JSON safely
        match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if not match:
            raise ValueError("No JSON found in Gemini response")
        
        clean_json = match.group(0)
        
        parsed = json.loads(clean_json)
        
        # DEBUG: Print parsed data
        
        return parsed
            
    except Exception as e:
        logger.error(f"Image-based AI extraction failed: {str(e)}")
        raise
