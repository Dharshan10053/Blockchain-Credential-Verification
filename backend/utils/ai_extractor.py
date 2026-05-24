import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")

def ai_extract_details(text: str) -> dict:
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
Extract structured details from this certificate text.

Return JSON only with:
name, course, certificate_id, date, issuer

Rules:
- Name = candidate name (not director/founder)
- Issuer = organization/company/university
- Ignore signatures and roles
- Be accurate

TEXT:
{text}
"""

    response = model.generate_content(prompt)

    try:
        import json
        return json.loads(response.text)
    except:
        return {}