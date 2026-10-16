
from database import (
    initialize_database,
    save_analysis,
    record_hr_decision,
    publish_decision,
    get_published_decision,
)


initialize_database()

sample_result = {
    "match_score": 72.5,
    "skill_score": 80.0,
    "text_similarity": 55.0,
    "matched_skills": ["python", "sql", "pandas", "git"],
    "missing_skills": ["docker"],
    "recommendation": "Partial Match — HR Review",
}

record_id = save_analysis(
    "DEMO-001",
    "Junior Python Developer",
    sample_result,
)

print("Analysis saved:", record_id)

record_hr_decision(
    record_id,
    "Shortlist",
    "Proceed to a human-led technical interview.",
)

print("HR decision recorded.")

print(
    "Before publication:",
    get_published_decision("DEMO-001"),
)

publish_decision(record_id)

print(
    "After publication:",
    get_published_decision("DEMO-001"),
)

print("SUCCESS: Database workflow test completed.")
