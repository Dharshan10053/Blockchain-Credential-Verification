"""
Standalone test for OCR extraction and certificate hashing.
Uses the same modules as the app (extract_details, generate_cert_hash, blockchain).
Run from project root: python test_ocr.py
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.ocr import extract_text, extract_details
from utils.cert_hash import generate_cert_hash
from blockchain import Blockchain

def main():
    image_path = "test_images/sample.png"
    if not os.path.exists(image_path):
        print(f"Optional: add {image_path} to test with a real image.")
        print("Using dummy text for extraction test.\n")
        text = """
        Certificate of Completion
        This is to certify that
        John Doe
        has successfully completed the course
        Python 101
        Date: 01/15/2024
        Certificate ID: CERT-2024-001
        """
    else:
        text = extract_text(image_path)

    name, course, date, cert_id, full_text = extract_details(text)
    print("------ EXTRACTED DETAILS ------")
    print("Name:", name)
    print("Course:", course)
    print("Date:", date)
    print("Certificate ID:", cert_id)

    cert_hash = generate_cert_hash(name, course, date, cert_id)
    print("\n------ CANONICAL HASH ------")
    print(cert_hash)

    chain = Blockchain()
    print("\n------ CHAIN LENGTH ------")
    print(len(chain.chain))
    if chain.validate_chain():
        print("Chain is valid.")
    found = chain.find_block_by_cert_hash(cert_hash)
    print("Hash found on chain:", found is not None)


if __name__ == "__main__":
    main()
