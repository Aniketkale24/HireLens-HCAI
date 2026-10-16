
import re
import pymupdf  # PyMuPDF


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract readable text from a PDF resume.

    Args:
        pdf_bytes: The PDF file contents as bytes.

    Returns:
        Extracted resume text.

    Raises:
        ValueError: If the PDF is invalid, empty, or has no readable text.
    """
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")

    try:
       with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.is_encrypted:
                raise ValueError(
                    "This PDF is password-protected. "
                    "Please use an accessible PDF."
                )

            pages = [
                page.get_text("text")
                for page in document
            ]

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "Unable to read this PDF. Please check the file."
        ) from exc

    text = "\n".join(pages)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if not text:
        raise ValueError(
            "No readable text was found. "
            "The PDF may be scanned or image-based."
        )

    return text
