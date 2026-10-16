
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SKILL_DICTIONARY = [
    "python",
    "java",
    "sql",
    "machine learning",
    "deep learning",
    "pandas",
    "numpy",
    "data analysis",
    "statistics",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "docker",
    "kubernetes",
    "git",
    "flask",
    "streamlit",
    "communication",
    "problem solving",
]


def detect_skills(text):
    """Find known skills mentioned in the supplied text."""
    text_lower = text.lower()
    found = []

    for skill in SKILL_DICTIONARY:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, text_lower):
            found.append(skill)

    return found


def analyze_candidate(resume_text, job_description, required_skills):
    """
    Compare resume content with job requirements.
    Returns a transparent, illustrative match analysis.
    """
    if not resume_text.strip():
        raise ValueError("Resume text cannot be empty.")

    if not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    if not required_skills:
        raise ValueError("Please provide at least one required skill.")

    required = list(dict.fromkeys(
        skill.strip().lower()
        for skill in required_skills
        if skill.strip()
    ))

    if not required:
        raise ValueError("No valid required skills were provided.")

    detected = detect_skills(resume_text)

    matched = [skill for skill in required if skill in detected]
    missing = [skill for skill in required if skill not in detected]

    skill_score = (len(matched) / len(required)) * 100

    # Compare resume text with the job description.
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        vectors = vectorizer.fit_transform([
            resume_text,
            job_description
        ])
        similarity = cosine_similarity(
            vectors[0:1], vectors[1:2]
        )[0][0] * 100
    except ValueError:
        similarity = 0.0

    # Illustrative project weights, not validated hiring criteria.
    overall_score = round(
        0.7 * skill_score + 0.3 * similarity
    )

    if overall_score >= 75:
        recommendation = "Strong Match — HR Review"
    elif overall_score >= 45:
        recommendation = "Partial Match — HR Review"
    else:
        recommendation = "Weak Match — HR Review"

    reasons = []

    if matched:
        reasons.append(
            "Required skills detected: " + ", ".join(matched)
        )

    if missing:
        reasons.append(
            "Required skills not detected: " + ", ".join(missing)
        )

    reasons.append(
        f"Required-skill coverage: {len(matched)}/{len(required)}."
    )

    reasons.append(
        f"Job-description text similarity: {similarity:.1f}/100."
    )

    reasons.append(
        "This score measures textual alignment, not candidate ability."
    )

    reasons.append(
        "The recommendation is advisory. HR makes the final decision."
    )

    return {
        "match_score": overall_score,
        "skill_score": round(skill_score, 1),
        "text_similarity": round(similarity, 1),
        "matched_skills": matched,
        "missing_skills": missing,
        "recommendation": recommendation,
        "reasons": reasons,
    }
