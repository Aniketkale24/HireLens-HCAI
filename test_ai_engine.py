
from ai_engine import analyze_candidate


resume = """
MSc Artificial Intelligence student.
Skills: Python, SQL, Pandas, NumPy.
Experience: Data analysis internship.
"""

job_description = """
We need a junior Python developer with Python,
SQL, Pandas, Git and Docker experience.
"""

required_skills = [
    "python",
    "sql",
    "pandas",
    "git",
    "docker",
]

result = analyze_candidate(
    resume,
    job_description,
    required_skills,
)

print("\n=== HIRELENS AI ANALYSIS ===")
print("Match score:", result["match_score"], "/100")
print("Skill coverage:", result["skill_score"], "%")
print("Text similarity:", result["text_similarity"])
print("Recommendation:", result["recommendation"])

print("\nMatched skills:", result["matched_skills"])
print("Skills not detected:", result["missing_skills"])

print("\nExplanation:")
for reason in result["reasons"]:
    print("-", reason)
