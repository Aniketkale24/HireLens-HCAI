
from resume_parser import extract_text_from_pdf
from ai_engine import analyze_candidate


def analyze_resume_pdf(
    pdf_bytes,
    job_description,
    required_skills,
):
    """
    Connect PDF resume extraction to the HireLens AI engine.
    """

    if not pdf_bytes:
        raise ValueError("Please provide a non-empty PDF file.")

    if not job_description or not job_description.strip():
        raise ValueError("Please provide a job description.")

    if not required_skills:
        raise ValueError("Please provide required skills.")

    # Step 1: Extract text from the uploaded PDF.
    resume_text = extract_text_from_pdf(pdf_bytes)

    # Step 2: Analyse the extracted text.
    result = analyze_candidate(
        resume_text=resume_text,
        job_description=job_description,
        required_skills=required_skills,
    )

    # Step 3: Include extracted text for authorised HR review.
    result["resume_text"] = resume_text

    return result
