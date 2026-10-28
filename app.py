import os
import sqlite3
from pathlib import Path

import streamlit as st
from backend_service import analyze_resume_pdf
from database import (
    DB_PATH, register_candidate, authenticate_user, create_authorized_hr_user,
    save_analysis, get_application_by_id, get_application_resume,
    get_candidate_applications, record_hr_decision, publish_decision,
)

# Allow Streamlit Community Cloud secrets to supply the HR invitation key.
try:
    os.environ.setdefault("HIRELENS_HR_INVITE_KEY", str(st.secrets["HIRELENS_HR_INVITE_KEY"]))
except Exception:
    pass

st.set_page_config(page_title="HireLens", page_icon="🔎", layout="wide")

st.markdown("""
<style>
.stApp {background:radial-gradient(ellipse at 8% 0%,rgba(40,120,155,.16),transparent 34%),linear-gradient(160deg,#0b1220 0%,#101827 52%,#0b1220 100%);color:#e8eef7}
[data-testid="stHeader"] {background:rgba(11,18,32,.82)}
.block-container {max-width:1400px;padding-top:1.5rem;padding-bottom:3rem}
[data-testid="stMetric"] {background:linear-gradient(145deg,rgba(27,41,64,.94),rgba(21,31,48,.94));border:1px solid rgba(128,165,202,.19);padding:1rem;border-radius:16px}
[data-testid="stTabs"] [role="tablist"] {gap:.65rem}
[data-testid="stTabs"] button[role="tab"] {padding:.7rem .9rem;font-weight:650;white-space:nowrap}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color:#43d9c5;border-bottom:3px solid #43d9c5}
.stButton>button,[data-testid="stFormSubmitButton"]>button {border-radius:10px;min-height:2.7rem;font-weight:700}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"]>button[kind="primary"] {background:linear-gradient(100deg,#087f8c,#0c9b91);color:white;border:0}
.hl-hero {padding:1.4rem 1.6rem;margin:.3rem 0 1.2rem;border-radius:20px;border:1px solid rgba(93,211,213,.24);background:linear-gradient(115deg,rgba(22,55,77,.92),rgba(21,31,48,.96) 62%,rgba(31,53,77,.9))}
.hl-brand {color:white;font-size:clamp(2rem,4vw,3rem);line-height:1.08;font-weight:850;letter-spacing:-.05em}
.hl-brand span {color:#43d9c5}
.hl-subtitle {color:#d5e3f5;font-size:1.05rem;margin-top:.6rem;margin-bottom:.9rem}
.hl-note {display:inline-block;color:#bff7ee;background:rgba(67,217,197,.09);border:1px solid rgba(67,217,197,.22);border-radius:999px;padding:.4rem .75rem;font-size:.85rem;font-weight:650}
</style>
""", unsafe_allow_html=True)

def brand():
    st.markdown("""
    <div class="hl-hero">
      <div class="hl-brand">🔎 Hire<span>Lens</span></div>
      <div class="hl-subtitle">An Explainable AI Hiring Decision Analysis Dashboard</div>
      <span class="hl-note">Human-led decisions · Explainable analysis · Responsible AI</span>
    </div>""", unsafe_allow_html=True)

def get_records():
    if not Path(DB_PATH).exists():
        return []
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("""SELECT id,candidate_id,application_id,candidate_name,job_title,
                match_score,skill_score,text_similarity,matched_skills,missing_skills,
                ai_recommendation,hr_decision,hr_feedback,published,created_at
                FROM candidates ORDER BY id DESC""").fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            return []

def job_form(key):
    with st.form(f"{key}_job_form"):
        title = st.text_input("Job title", key=f"{key}_title", placeholder="e.g. Junior Python Developer")
        description = st.text_area("Job description", key=f"{key}_description", height=110)
        skills = st.text_input("Required skills (comma-separated)", key=f"{key}_skills", placeholder="Python, SQL, Pandas")
        save = st.form_submit_button("Save job requirements", type="primary")
    if save:
        if not title.strip() or not description.strip() or not skills.strip():
            st.error("Enter the job title, job description, and at least one required skill.")
        else:
            st.session_state[f"{key}_job"] = {
                "title": title.strip(), "description": description.strip(),
                "skills": [x.strip() for x in skills.split(",") if x.strip()]
            }
            st.success("Job requirements saved for this session.")
    return st.session_state.get(f"{key}_job")

def show_result(result):
    c1,c2,c3=st.columns(3)
    c1.metric("Match score",f'{float(result.get("match_score",0)):.1f}/100')
    c2.metric("Skill coverage",f'{float(result.get("skill_score",0)):.1f}%')
    c3.metric("Text similarity",f'{float(result.get("text_similarity",0)):.1f}/100')
    st.progress(max(0, min(100, int(round(float(result.get("match_score", 0)))))))
    st.write("**Matched skills**")
    st.write(", ".join(result.get("matched_skills",[])) or "No required skills detected.")
    st.write("**Skills not detected**")
    st.write(", ".join(result.get("missing_skills",[])) or "No missing required skills detected.")
    st.write("**AI recommendation (advisory only)**")
    st.write(result.get("recommendation","No recommendation returned."))
    st.write("**Explanation**")
    reasons=result.get("reasons",[])
    if reasons:
        for reason in reasons: st.write(f"- {reason}")
    else: st.write("No explanation reasons were returned.")
    st.caption("Scores measure textual alignment; they do not measure candidate worth or guarantee performance.")
