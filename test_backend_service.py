
import pymupdf

from backend_service import analyze_resume_pdf


# Create a sample PDF in memory.
pdf = pymupdf.open()
page = pdf.new_page()

page.insert_textbox(
    pymupdf.Rect(50, 50, 550, 350),
    """
    DEMO CANDIDATE
    MSc Artificial Intelligence
    Skills: Python, SQL, Pandas, NumPy
    Experience: Data analysis internship.
    Worked on data cleaning and machine learning projects.
    """,
    fontsize=12,
)

pdf_bytes = pdf.tobytes()
pdf.close()

job_description = """
Junior Python Developer. Requires Python, SQL,
Pandas, Git and Docker. Data analysis experience
and programming skills are useful.
"""

required_skills = [
    "python",
    "sql",
    "pandas",
    "git",
    "docker",
]

try:
    result = analyze_resume_pdf(
        pdf_bytes,
        job_description,
        required_skills,
    )

    print("=== HIRELENS BACKEND SERVICE ===")
    print("PDF parsing: SUCCESS")
    print("AI analysis: SUCCESS")
    print("Match score:", result["match_score"], "/100")
    print("Skill coverage:", result["skill_score"], "%")
    print("Matched skills:", result["matched_skills"])
    print("Skills not detected:", result["missing_skills"])
    print("Recommendation:", result["recommendation"])

    print("\nExplanation:")
    for reason in result["reasons"]:
        print("-", reason)

    print("\nSUCCESS: Backend service is working.")

except ValueError as error:
    print("Backend validation error:", error)
