"""
PDF parsing service.

Converts an uploaded file (PDF or plain text) into a single string of
raw contract text ready to be sent to the AI extraction layer.

Supports:
  - application/pdf  → pdfplumber extracts text page by page
  - text/plain       → decoded directly (UTF-8, fallback latin-1)
"""
import io
from typing import Union

import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract and concatenate text from every page of a PDF."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    return "\n\n".join(text_parts)


def extract_text_from_upload(file_bytes: bytes, content_type: str) -> str:
    """
    Route the uploaded file to the correct parser based on its MIME type.

    Raises ValueError if the file type is not supported — the router turns
    this into a 400 so the caller gets a clear error message.
    """
    if content_type == "application/pdf":
        text = extract_text_from_pdf(file_bytes)
        if not text.strip():
            raise ValueError(
                "PDF was parsed but contained no extractable text. "
                "It may be a scanned image — try a text-based PDF."
            )
        return text

    if content_type in ("text/plain", "text/txt"):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")

    raise ValueError(
        f"Unsupported file type: '{content_type}'. "
        "Please upload a PDF (.pdf) or plain-text (.txt) file."
    )
