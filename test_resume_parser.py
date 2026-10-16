
import pymupdf
from resume_parser import extract_text_from_pdf


# Create a temporary sample resume in memory.
sample_pdf = pymupdf.open()
page = sample_pdf.new_page()

sample_text = """
Candidate: Demo Candidate
Skills: Python, SQL, Pandas, Machine Learning
Education: MSc Artificial Intelligence
Experience: Data analysis internship
"""

page.insert_textbox(
    pymupdf.Rect(50, 50, 550, 300),
    sample_text,
    fontsize=12
)

pdf_bytes = sample_pdf.tobytes()
sample_pdf.close()

# Test the resume parser.
try:
    extracted_text = extract_text_from_pdf(pdf_bytes)

    print("SUCCESS: Resume text extracted!")
    print("-" * 40)
    print(extracted_text)

except ValueError as error:
    print("ERROR:", error)
