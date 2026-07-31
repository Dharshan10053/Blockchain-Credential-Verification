import hashlib
import re

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-z0-9 ]', '', text)
    return text.strip()


def generate_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
