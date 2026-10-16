
from pathlib import Path

from resume_parser import extract_text_from_pdf
from ai_engine import analyze_candidate


# Create a sample resume PDF in memory.
import pymupdf

sample_pdf = pymupdf.open()
page = sample_pdf.new_page()

page.insert_textbox(
    pymupdf.Rect(50, 50, 550, 350),
    """
    DEMO CANDIDATE

    Education: MSc Artificial Intelligence

    Skills: Python, SQL, Pandas, NumPy

    Experience: Data analysis internship.
    Worked on data cleaning and machine learning projects.
    """,
    fontsize=12,
)

pdf_bytes = sample_pdf.tobytes()
sample_pdf.close()

# Step 1: Extract text from the PDF.
resume_text = extract_text_from_pdf(pdf_bytes)

print("STEP 1: RESUME TEXT EXTRACTED")
print(resume_text)

# Step 2: Analyse the extracted text.
job_description = """
Junior Python Developer.
Requires Python, SQL, Pandas, Git and Docker.
Experience with data analysis is useful.
"""

required_skills = [
    "python",
    "sql",
    "pandas",
    "git",
    "docker",
]

result = analyze_candidate(
    resume_text,
    job_description,
    required_skills,
)

print("\nSTEP 2: HIRELENS AI ANALYSIS")
print("Match score:", result["match_score"], "/100")
print("Skill coverage:", result["skill_score"], "%")
print("Text similarity:", result["text_similarity"], "/100")
print("Recommendation:", result["recommendation"])
print("Matched skills:", result["matched_skills"])
print("Skills not detected:", result["missing_skills"])

print("\nEXPLANATION")
for reason in result["reasons"]:
    print("-", reason)

print("\nSUCCESS: PDF parsing and AI analysis are connected.")
print("This is an advisory recommendation; HR makes the final decision.")
