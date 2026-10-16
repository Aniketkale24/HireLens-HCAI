
import pymupdf

from backend_service import analyze_resume_pdf
from database import (
    save_analysis,
    record_hr_decision,
    publish_decision,
    get_published_decision,
)

# Create a synthetic candidate resume.
pdf = pymupdf.open()
page = pdf.new_page()

page.insert_textbox(
    pymupdf.Rect(50, 50, 550, 350),
    """
    DEMO CANDIDATE
    Education: MSc Artificial Intelligence
    Skills: Python, SQL, Pandas, NumPy
    Experience: Data analysis internship.
    """,
    fontsize=12,
)

pdf_bytes = pdf.tobytes()
pdf.close()

# 1. Analyse the PDF.
result = analyze_resume_pdf(
    pdf_bytes,
    """
    Junior Python Developer. Requires Python, SQL,
    Pandas, Git and Docker. Data analysis experience
    is useful.
    """,
    ["python", "sql", "pandas", "git", "docker"],
)

print("AI analysis completed:", result["match_score"])

# 2. Save the analysis.
record_id = save_analysis(
    "DEMO-COMPLETE-001",
    "Junior Python Developer",
    result,
)

print("Analysis saved:", record_id)

# 3. Record the human decision.
record_hr_decision(
    record_id,
    "Shortlist",
    "Demo: proceed to a human-led interview.",
)

print("HR decision recorded.")

# 4. Publish the decision.
publish_decision(record_id)

# 5. Verify candidate-facing result.
published = get_published_decision("DEMO-COMPLETE-001")

assert len(published) == 1
assert published[0]["hr_decision"] == "Shortlist"

print("Published candidate result:", published)
print("SUCCESS: Complete backend workflow passed.")
