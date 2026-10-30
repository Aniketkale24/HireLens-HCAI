import os
import sqlite3
import hashlib
from pathlib import Path

import streamlit as st

from backend_service import analyze_resume_pdf
from database import (
    DB_PATH,
    register_candidate,
    authenticate_user,
    create_authorized_hr_user,
    save_analysis,
    get_application_by_id,
    get_application_resume,
    get_candidate_applications,
    record_hr_decision,
    publish_decision,
    create_job,
    get_jobs,
    get_job_by_id,
    get_resumes_for_matching,
    save_job_match,
    get_job_matches,
    get_job_match_resume,
    record_job_match_decision,
    publish_job_match_decision,
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

try:
    os.environ.setdefault(
        "HIRELENS_HR_INVITE_KEY",
        str(st.secrets["HIRELENS_HR_INVITE_KEY"])
    )
except Exception:
    pass

st.set_page_config(
    page_title="HireLens",
    page_icon="🔎",
    layout="wide"
)

st.markdown("""
<style>
/* HireLens fixed light design system. The app intentionally stays light for every visitor. */
:root {
  --hl-accent: #7057e8; --hl-accent-2: #8b70ff; --hl-teal: #21b7a8;
  --hl-sidebar: #14213d; --hl-sidebar-2: #202f50;
  --hl-radius: 18px;
}
.stApp { background: #f5f7fc !important; color: #18243b !important; }
[data-testid="stAppViewContainer"] { background: #f5f7fc !important; color: #18243b !important; }
[data-testid="stHeader"] { background: transparent !important; }
.block-container { max-width: 1500px; padding-top: 1.35rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,var(--hl-sidebar),var(--hl-sidebar-2)) !important; border-right: 1px solid rgba(255,255,255,.08); }
[data-testid="stSidebar"] * { color: #eef3ff !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding: .55rem .65rem; border-radius: 10px; margin: .12rem 0; transition: background .15s ease; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: rgba(255,255,255,.12) !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background: rgba(125,105,255,.25) !important; }
/* Keep sidebar controls visible without relying on hover. */
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button,
[data-testid="stSidebar"] [data-testid="stFormSubmitButton"] > button * {
  background: #ffffff !important; color: #17243b !important;
  -webkit-text-fill-color: #17243b !important;
  border: 1px solid #d7def0 !important; font-weight: 800 !important;
  opacity: 1 !important; visibility: visible !important;
}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stButton > button:hover * {
  background: #eeeaff !important; color: #40328f !important;
  -webkit-text-fill-color: #40328f !important; border-color: #c8bfff !important;
}
[data-testid="stMetric"] { background: #ffffff !important; border: 1px solid #e1e6f0 !important; border-radius: var(--hl-radius) !important; padding: 1.05rem 1.15rem !important; box-shadow: 0 7px 22px rgba(30,45,80,.06); }
[data-testid="stMetricLabel"] { opacity: .78; font-weight: 650 !important; }
[data-testid="stMetricValue"] { font-weight: 850 !important; letter-spacing: -.035em; }
[data-testid="stTabs"] [role="tablist"] { gap: .55rem; border-bottom: 1px solid #e1e6f0; }
[data-testid="stTabs"] button[role="tab"] { padding: .72rem 1rem; font-weight: 700; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: var(--primary-color, var(--hl-accent)) !important; border-bottom: 3px solid var(--primary-color, var(--hl-accent)) !important; }
.stButton > button:not([kind="primary"]), [data-testid="stFormSubmitButton"] > button:not([kind="primary"]) { color:#24324a !important; -webkit-text-fill-color:#24324a !important; background:#ffffff !important; border:1px solid #d8deea !important; }\n.stButton > button, [data-testid="stFormSubmitButton"] > button { border-radius: 11px !important; min-height: 2.7rem; font-weight: 700 !important; opacity: 1 !important; transition: transform .15s ease, box-shadow .15s ease, background .15s ease; }
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(91,75,190,.15); }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] { background: linear-gradient(100deg,#6554d7,#806be9) !important; color: #fff !important; border: 0 !important; }
.stTextInput input, .stTextArea textarea, .stNumberInput input, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea { background: #ffffff !important; color: #18243b !important; -webkit-text-fill-color: #18243b !important; border-color: #d8deea !important; border-radius: 10px !important; opacity: 1 !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { opacity: .58 !important; -webkit-text-fill-color: #18243b !important; }
.stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label, .stFileUploader label, .stNumberInput label, .stMultiSelect label { color: #18243b !important; font-weight: 650 !important; }
[data-testid="stExpander"] { border: 1px solid #e1e6f0; border-radius: 14px; }
[data-testid="stAlert"] { border-radius: 12px; }
.hl-hero { padding: 1.45rem 1.65rem; margin: .15rem 0 1.25rem; border-radius: 22px; border: 1px solid rgba(126,112,225,.18); background: linear-gradient(112deg,#fff 0%,#f1efff 58%,#e9f8f6 100%); box-shadow: 0 9px 28px rgba(31,48,78,.06); }
.hl-brand { color: #17243b; font-size: clamp(2rem,3.8vw,2.8rem); line-height: 1.08; font-weight: 900; letter-spacing: -.05em; }
.hl-brand span { color: #6b59dc; }
.hl-subtitle { color: #59677e; font-size: 1rem; margin-top: .45rem; margin-bottom: .8rem; }
.hl-note { display: inline-block; color: #286c68; background: #e5f6f3; border: 1px solid #ccebe6; border-radius: 999px; padding: .38rem .75rem; font-size: .82rem; font-weight: 750; }
.hl-page-kicker { color: #806be9; font-size: .73rem; font-weight: 850; letter-spacing: .13em; text-transform: uppercase; margin-bottom: .28rem; }
.hl-page-title { color: #18243b; font-size: clamp(1.55rem,2.5vw,2rem); line-height: 1.2; font-weight: 850; letter-spacing: -.04em; margin: 0 0 .35rem; }
.hl-page-sub { color: #18243b; opacity: .68; font-size: .96rem; margin-bottom: 1.1rem; }
.hl-panel { background: #ffffff; border: 1px solid #e1e6f0; border-radius: 17px; padding: 1.1rem 1.2rem; box-shadow: 0 6px 20px rgba(31,48,78,.045); }
.hl-panel-title { color: #18243b; font-weight: 800; font-size: 1rem; margin-bottom: .25rem; }
.hl-muted { color: #18243b; opacity: .68; font-size: .86rem; }
.hl-login-panel { background: linear-gradient(145deg,#111e3c,#263b69 70%,#443b91); border-radius: 22px; padding: 2rem; min-height: 430px; color: white; }
.hl-login-panel h1,.hl-login-panel h2,.hl-login-panel p,.hl-login-panel li { color: white !important; }
.hl-login-panel h1 { font-size: clamp(2rem,4vw,3.1rem); line-height: 1.08; letter-spacing: -.045em; }
.hl-login-chip { display:inline-block; padding:.42rem .7rem; border-radius:999px; background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.18); margin:.25rem .25rem .25rem 0; font-size:.8rem; }
@media (max-width: 850px) { .block-container { padding-left: 1rem; padding-right: 1rem; } .hl-hero { padding: 1rem; } .hl-login-panel { min-height: auto; margin-bottom: 1rem; } }

.hl-decision-chart { background:#ffffff; border:1px solid #e1e6f0; border-radius:16px; padding:1.2rem 1.35rem; margin-top:.6rem; box-shadow:0 6px 20px rgba(31,48,78,.045); }
.hl-chart-row { display:grid; grid-template-columns:180px minmax(100px,1fr) 42px; gap:14px; align-items:center; margin:.9rem 0; }
.hl-chart-label { color:#475569; font-weight:650; font-size:.9rem; }
.hl-chart-track { height:13px; border-radius:999px; background:#edf0f7; overflow:hidden; }
.hl-chart-fill { height:100%; border-radius:999px; min-width:0; }
.hl-chart-value { color:#18243b; font-weight:800; text-align:right; }
[data-testid="stSidebar"] .stButton > button { min-height:3rem !important; }
@media (max-width:650px) { .hl-chart-row { grid-template-columns:120px minmax(50px,1fr) 30px; gap:8px; } }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# BRANDING AND COMMON HELPERS
# --------------------------------------------------

def brand():
    st.markdown("""
    <div class="hl-hero">
      <div class="hl-brand">🔎 Hire<span>Lens</span></div>
      <div class="hl-subtitle">An Explainable AI Hiring Decision Analysis Dashboard</div>
      <span class="hl-note">Human-led decisions&nbsp; · &nbsp;Explainable analysis&nbsp; · &nbsp;Responsible AI</span>
    </div>
    """, unsafe_allow_html=True)


def get_records():
    if not Path(DB_PATH).exists():
        return []

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("""
                SELECT
                    id, candidate_id, application_id, candidate_name,
                    job_title, match_score, skill_score, text_similarity,
                    matched_skills, missing_skills, ai_recommendation,
                    hr_decision, hr_feedback, published, created_at
                FROM candidates
                ORDER BY id DESC
            """).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            return []


def get_candidate_job_matches(user_id):
    """Return saved-job matches linked to this candidate's own account."""
    if not Path(DB_PATH).exists():
        return []

    try:
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT
                    jm.id AS match_id,
                    jm.job_id,
                    jm.match_score,
                    jm.skill_score,
                    jm.text_similarity,
                    jm.matched_skills,
                    jm.missing_skills,
                    jm.ai_recommendation,
                    jm.hr_decision,
                    jm.hr_feedback,
                    jm.published,
                    jm.created_at AS matched_at,
                    j.title AS job_title,
                    j.description AS job_description,
                    c.application_id,
                    c.created_at AS submitted_at
                FROM job_matches jm
                JOIN candidates c ON c.id = jm.source_candidate_id
                JOIN jobs j ON j.id = jm.job_id
                WHERE c.applicant_user_id = ?
                ORDER BY jm.id DESC
            """, (user_id,)).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.OperationalError:
        # Safe fallback if the database has not yet been migrated.
        return []


def job_form(key):
    with st.form(f"{key}_job_form"):
        title = st.text_input(
            "Job title",
            key=f"{key}_title",
            placeholder="e.g. Junior Python Developer"
        )
        description = st.text_area(
            "Job description",
            key=f"{key}_description",
            height=110
        )
        skills = st.text_input(
            "Required skills (comma-separated)",
            key=f"{key}_skills",
            placeholder="Python, SQL, Pandas"
        )
        save = st.form_submit_button(
            "Save Job Details",
            type="primary"
        )

    if save:
        if not title.strip() or not description.strip() or not skills.strip():
            st.error(
                "Enter the job title, description, and required skills."
            )
        else:
            st.session_state[f"{key}_job"] = {
                "title": title.strip(),
                "description": description.strip(),
                "skills": [
                    item.strip()
                    for item in skills.split(",")
                    if item.strip()
                ],
            }
            st.session_state[f"{key}_job_saved_notice"] = (
                "Job details saved. Upload your resume and click Submit when ready."
            )

    if st.session_state.get(f"{key}_job_saved_notice"):
        st.success(st.session_state[f"{key}_job_saved_notice"])

    return st.session_state.get(f"{key}_job")


def show_result(result):
    c1, c2 = st.columns(2)

    c1.metric(
        "Match score",
        f'{float(result.get("match_score", 0)):.1f}/100'
    )
    c2.metric(
        "Skill coverage",
        f'{float(result.get("skill_score", 0)):.1f}%'
    )

    st.progress(max(
        0,
        min(100, int(round(float(result.get("match_score", 0)))))
    ))

    st.write("**Matched skills**")
    st.write(", ".join(result.get("matched_skills", []))
             or "No required skills detected.")

    st.write("**Skills not detected**")
    st.write(", ".join(result.get("missing_skills", []))
             or "No missing required skills detected.")

    st.write("**AI recommendation (advisory only)**")
    st.write(result.get("recommendation", "No recommendation returned."))

    st.write("**Explanation**")
    reasons = result.get("reasons", [])
    if reasons:
        for reason in reasons:
            st.write(f"- {reason}")
    else:
        st.info("The analysis engine did not return separate explanation reasons.")

    st.caption(
        "Scores measure textual alignment; they do not measure candidate "
        "worth or guarantee job performance. HR makes the final decision."
    )


def submit_resumes(files, job, owner_id=None, owner_name=None):
    if not job:
        st.error("Enter and submit the job requirements first.")
        return

    if not files:
        st.error("Please upload at least one PDF resume.")
        return

    success = 0
    skipped = 0

    for pdf in files:
        try:
            pdf_bytes = pdf.getvalue()
            name = (
                owner_name if owner_id is not None else
                st.session_state.get(f"name_{pdf.name}", "").strip()
                or Path(pdf.name).stem
            )

            # Avoid creating another application when the same account submits
            # the same PDF for the same job again.
            existing = None
            with sqlite3.connect(DB_PATH) as con:
                con.row_factory = sqlite3.Row
                existing = con.execute("""
                    SELECT id, application_id, match_score, skill_score
                    FROM candidates
                    WHERE applicant_user_id IS ?
                      AND job_title = ?
                      AND resume_filename = ?
                      AND resume_pdf = ?
                    ORDER BY id DESC
                    LIMIT 1
                """, (
                    owner_id, job["title"], pdf.name, sqlite3.Binary(pdf_bytes)
                )).fetchone()

            if existing:
                # Re-analyse the existing application against the latest job
                # details. Keep the same Application ID and do not create a row.
                result = analyze_resume_pdf(
                    pdf_bytes,
                    job["description"],
                    job["skills"]
                )
                with sqlite3.connect(DB_PATH) as con:
                    con.execute("""UPDATE candidates
                        SET job_title = ?, job_description = ?, required_skills = ?,
                            match_score = ?, skill_score = ?, text_similarity = ?,
                            matched_skills = ?, missing_skills = ?, ai_recommendation = ?
                        WHERE id = ?""", (
                        job["title"], job["description"], ", ".join(job["skills"]),
                        result["match_score"], result["skill_score"], result["text_similarity"],
                        ", ".join(result["matched_skills"]),
                        ", ".join(result["missing_skills"]), result["recommendation"],
                        existing["id"]
                    ))
                st.warning(
                    f"This resume was already submitted. We updated the analysis "
                    f"using your latest job details. Your existing Application ID "
                    f"is {existing['application_id']}; no duplicate application was created."
                )
                left, right = st.columns(2)
                left.metric("Updated match score", f"{float(result['match_score']):.1f}/100")
                right.metric("Updated skill coverage", f"{float(result['skill_score']):.1f}%")
                with st.expander("View updated analysis", expanded=True):
                    show_result(result)
                skipped += 1
                continue

            result = analyze_resume_pdf(
                pdf_bytes,
                job["description"],
                job["skills"]
            )

            record_id = save_analysis(
                name,
                job["title"],
                result,
                applicant_user_id=owner_id,
                candidate_name=name,
                resume_pdf=pdf_bytes,
                resume_filename=pdf.name,
                job_description=job["description"],
                required_skills=", ".join(job["skills"]),
            )

            with sqlite3.connect(DB_PATH) as con:
                row = con.execute(
                    "SELECT application_id FROM candidates WHERE id = ?",
                    (record_id,)
                ).fetchone()

            app_id = row[0]
            st.success(f"Saved application ID: {app_id}")
            with st.expander(f"Analysis for {name} · {app_id}", expanded=True):
                show_result(result)
            success += 1

        except Exception as exc:
            st.error(
                f"Could not process {pdf.name}: "
                f"{type(exc).__name__}: {exc}"
            )

    if success:
        st.info(
            f"{success} new application(s) saved. Their original PDFs are "
            "available for matching against saved jobs."
        )
    if skipped:
        st.info(f"Skipped {skipped} duplicate submission(s). No new application was created for them.")


def logout():
    if st.sidebar.button("↪  Log out", key="hirelens_logout", use_container_width=True):
        st.session_state.pop("hirelens_user", None)
        st.rerun()


# --------------------------------------------------
# LOGIN AND REGISTRATION
# --------------------------------------------------

def login_page():
    """Responsive split welcome/login experience for candidates and HR."""
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown("""
        <div class="hl-login-panel">
          <div style="font-size:1.05rem;font-weight:800;letter-spacing:.02em">🔎 HireLens</div>
          <div style="height:2.3rem"></div>
          <h1>Smarter Hiring.<br>More Opportunities.</h1>
          <p style="font-size:1.02rem;opacity:.88;line-height:1.6">AI-assisted resume analysis with clear explanations. Final decisions always remain in human hands.</p>
          <div style="height:1rem"></div>
          <div class="hl-login-chip">✓ Explainable AI</div>
          <div class="hl-login-chip">✓ Fairer review</div>
          <div class="hl-login-chip">✓ Human-led decisions</div>
          <div style="height:2.2rem"></div>
          <div style="padding:1rem;border-radius:15px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.12)">
            <div style="font-size:1.5rem;font-weight:800">Your skills. Your insights.</div>
            <div style="opacity:.82;margin-top:.35rem">A clearer way to understand how a resume aligns with a role.</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown('<div class="hl-page-kicker">Welcome to HireLens</div><div class="hl-page-title">Your hiring workspace</div><div class="hl-page-sub">Sign in or create the right account to continue.</div>', unsafe_allow_html=True)
        tab_login, tab_register, tab_hr = st.tabs(["Login", "Candidate registration", "Authorized HR setup"])
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email address", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submit = st.form_submit_button("Login", type="primary", use_container_width=True)
            if submit:
                try:
                    user = authenticate_user(email, password)
                    if user:
                        st.session_state["hirelens_user"] = user
                        st.rerun()
                    else:
                        st.error("Email or password is incorrect.")
                except Exception as exc:
                    st.error(f"Login failed: {exc}")
        with tab_register:
            with st.form("candidate_register"):
                name = st.text_input("Full name", key="reg_name")
                email = st.text_input("Email address", key="reg_email")
                password = st.text_input("Password (minimum 10 characters)", type="password", key="reg_password")
                confirm = st.text_input("Confirm password", type="password", key="reg_confirm")
                submit = st.form_submit_button("Create candidate account", type="primary", use_container_width=True)
            if submit:
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        register_candidate(name, email, password)
                        st.success("Candidate account created. Please log in.")
                    except Exception as exc:
                        st.error(str(exc))
        with tab_hr:
            st.info("HR registration requires the administrator's private authorization key.")
            with st.form("hr_register"):
                name = st.text_input("HR full name", key="hr_reg_name")
                email = st.text_input("Work email", key="hr_reg_email")
                password = st.text_input("Password (minimum 10 characters)", type="password", key="hr_reg_password")
                confirm = st.text_input("Confirm password", type="password", key="hr_reg_confirm")
                invite = st.text_input("HR authorization key", type="password", key="hr_reg_invite")
                submit = st.form_submit_button("Create authorized HR account", type="primary", use_container_width=True)
            if submit:
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        create_authorized_hr_user(name, email, password, invite)
                        st.success("HR account created. Please log in.")
                    except Exception as exc:
                        st.error(str(exc))


# --------------------------------------------------
# CANDIDATE PORTAL
# --------------------------------------------------

@st.fragment(run_every="5s")
def render_candidate_applications(user_id):
    """Refresh only the candidate's application list periodically."""
    st.subheader("Applications you submitted")
    apps = get_candidate_applications(user_id)
    job_matches = get_candidate_job_matches(user_id)

    matches_by_app = {}
    for match in job_matches:
        app_id = match.get("application_id")
        if app_id:
            matches_by_app.setdefault(app_id, []).append(match)

    if not apps:
        st.info(
            "You have no applications yet. Applications uploaded independently "
            "by HR are not shown here."
        )
        return

    for app in apps:
        app_id = app.get("application_id")
        matching_results = matches_by_app.get(app_id, [])
        with st.container(border=True):
            st.subheader(app["job_title"])
            st.write(f'**Application ID:** `{app_id}`')
            st.write(f'**Submitted:** {app["created_at"]}')

            if matching_results:
                # Show all job-specific matches inside the source application,
                # never create another application card for each match.
                for match in matching_results:
                    st.divider()
                    st.markdown(f'**HR matching job:** {match["job_title"]}')
                    c1, c2 = st.columns(2)
                    c1.metric(
                        "Match score",
                        f'{float(match.get("match_score") or 0):.1f}/100'
                    )
                    c2.metric(
                        "Skill coverage",
                        f'{float(match.get("skill_score") or 0):.1f}%'
                    )
                    st.write(
                        f'**AI recommendation:** '
                        f'{match.get("ai_recommendation") or "Not available"}'
                    )
                    st.write(
                        "**Matched skills:**",
                        match.get("matched_skills") or "None detected"
                    )
                    st.write(
                        "**Skills not detected:**",
                        match.get("missing_skills") or "None detected"
                    )
                    if match.get("published") and match.get("hr_decision"):
                        decision = match["hr_decision"]
                        if decision == "Shortlist":
                            st.success(f"Published HR decision: {decision}")
                        elif decision == "Reject":
                            st.error(f"Published HR decision: {decision}")
                        else:
                            st.info(f"Published HR decision: {decision}")
                        if match.get("hr_feedback"):
                            st.write(f'**Feedback from HR:** {match["hr_feedback"]}')
                    elif match.get("hr_decision"):
                        st.info(
                            "HR has saved a decision, but it has not been published yet."
                        )
                    else:
                        st.info("HR has not published a decision for this job yet.")
            else:
                st.metric(
                    "Initial match score",
                    f'{float(app.get("match_score") or 0):.1f}/100'
                )
                if app.get("published") and app.get("hr_decision"):
                    decision = app["hr_decision"]
                    if decision == "Shortlist":
                        st.success(f"Published HR decision: {decision}")
                    elif decision == "Reject":
                        st.error(f"Published HR decision: {decision}")
                    else:
                        st.info(f"Published HR decision: {decision}")
                    if app.get("hr_feedback"):
                        st.write(f'**Feedback from HR:** {app["hr_feedback"]}')
                elif app.get("hr_decision"):
                    st.info("HR has saved a decision, but it has not been published yet.")
                else:
                    st.info("No decision has been published for this application yet.")

            st.caption("AI scores are advisory. The hiring decision is made by HR.")


def candidate_page(user):
    brand()
    st.sidebar.markdown("## Candidate Portal")
    st.sidebar.caption(f"Signed in as {user['full_name']}")
    st.sidebar.divider()
    section = st.sidebar.radio(
        "Navigation", ["Dashboard", "Job Details & Apply", "My Applications", "Profile"],
        key="candidate_sidebar_navigation"
    )
    logout()

    apps = get_candidate_applications(user["id"])
    job_matches = get_candidate_job_matches(user["id"])
    decisions = [m for m in job_matches if m.get("published") and m.get("hr_decision")]
    shortlisted = sum(1 for m in decisions if m.get("hr_decision") == "Shortlist")
    rejected = sum(1 for m in decisions if m.get("hr_decision") == "Reject")
    pending = max(len(apps) - len(decisions), 0)

    if section == "Dashboard":
        st.markdown('<div class="hl-page-kicker">Candidate workspace</div><div class="hl-page-title">Welcome back, '+str(user.get("full_name", "Candidate"))+' 👋</div><div class="hl-page-sub">Take the next step in your career with clear, AI-assisted resume insights.</div>', unsafe_allow_html=True)
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Total applications", len(apps))
        k2.metric("Under review", pending)
        k3.metric("Shortlisted", shortlisted)
        k4.metric("Rejected", rejected)
        st.markdown(
            '<div class="hl-panel"><div class="hl-panel-title">Your next opportunity starts here</div>'
            '<div class="hl-muted">Add a role, upload your resume and understand how its text aligns with the job requirements.</div></div>',
            unsafe_allow_html=True
        )
        st.markdown("### Make your next move")
        st.write("Keep your applications organised and check updates shared by the HR team.")
        if st.button("＋  Add job details and apply", type="primary", use_container_width=False):
            st.session_state["candidate_sidebar_navigation"] = "Job Details & Apply"
            st.rerun()
        st.markdown("### Recent applications")
        if apps:
            for app in apps[:3]:
                with st.container(border=True):
                    st.markdown(f"**{app.get('job_title') or 'Application'}**")
                    st.caption(f"Application ID: {app.get('application_id','—')}  ·  Submitted: {app.get('created_at','—')}")
        else:
            st.info("You haven't submitted an application yet. Start by adding job details and uploading your resume.")
        st.caption("AI scores are advisory and measure textual alignment only. HR makes the final hiring decision.")

    elif section == "Job Details & Apply":
        st.markdown('<div class="hl-page-kicker">Application workspace</div><div class="hl-page-title">Apply for a role</div><div class="hl-page-sub">Enter the role details, upload your PDF resume and review the analysis.</div>', unsafe_allow_html=True)
        st.markdown("### 1 · Job details")
        job = job_form("candidate")
        st.markdown("### 2 · Upload your resume")
        files = st.file_uploader("Upload resume PDF(s)", type=["pdf"], accept_multiple_files=True, key="candidate_pdfs")
        if st.button("Submit application", type="primary", use_container_width=True):
            if not job:
                st.error("Please save the job details first.")
            elif not files:
                st.error("Please upload at least one PDF resume.")
            else:
                submit_resumes(files, job, owner_id=user["id"], owner_name=user["full_name"])
                st.session_state["candidate_submission_notice"] = "Your submission has been processed. Check the application ID(s) above."
        if st.session_state.get("candidate_submission_notice"):
            st.success(st.session_state["candidate_submission_notice"])

    elif section == "My Applications":
        st.markdown('<div class="hl-page-kicker">Application tracker</div><div class="hl-page-title">My applications</div><div class="hl-page-sub">Track submissions and view HR decisions and feedback when they are published.</div>', unsafe_allow_html=True)
        render_candidate_applications(user["id"])

    elif section == "Profile":
        st.markdown('<div class="hl-page-kicker">Account</div><div class="hl-page-title">Your profile</div><div class="hl-page-sub">Your account information.</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.write("**Full name**", user.get("full_name", "—"))
            st.write("**Email address**", user.get("email", "—"))
            st.write("**Account type**", "Candidate")


def job_requirements_tab(user):
    st.subheader("Create and manage jobs")

    if st.session_state.get("job_saved_notice"):
        st.success(st.session_state["job_saved_notice"])

    st.write(
        "Save job details once, then match them against stored "
        "resume PDFs from candidate submissions and HR uploads."
    )

    with st.form("create_saved_job_form"):
        title = st.text_input(
            "Job title",
            placeholder="e.g. Junior Python Developer"
        )
        description = st.text_area(
            "Job description",
            height=130
        )
        skills_text = st.text_input(
            "Required skills (comma-separated)",
            placeholder="Python, SQL, Pandas"
        )

        create = st.form_submit_button(
            "Save Job Requirements",
            type="primary",
            use_container_width=True
        )

    if create:
        skills = [
            skill.strip()
            for skill in skills_text.split(",")
            if skill.strip()
        ]

        try:
            new_job_id = create_job(
                title,
                description,
                skills,
                created_by=user["id"]
            )
            st.session_state["selected_job_id"] = new_job_id
            st.session_state["job_saved_notice"] = (
                f"Job requirements saved successfully. Job ID: {new_job_id}"
            )
            st.rerun()

        except Exception as exc:
            st.error(f"Could not save job: {exc}")

    st.divider()
    st.subheader("Saved jobs")

    jobs = get_jobs()

    if not jobs:
        st.info("No saved jobs yet. Create a job above to begin.")
        return

    job_options = {
        f'{job["title"]} · Job #{job["id"]}': job["id"]
        for job in jobs
    }

    selected_id = st.session_state.get("selected_job_id")
    option_labels = list(job_options.keys())

    default_index = 0
    for index, label in enumerate(option_labels):
        if job_options[label] == selected_id:
            default_index = index
            break

    selected_label = st.selectbox(
        "Choose a job to manage",
        option_labels,
        index=default_index,
        key="saved_job_selector"
    )

    job_id = job_options[selected_label]
    st.session_state["selected_job_id"] = job_id
    job = get_job_by_id(job_id)

    if not job:
        st.error("This saved job could not be found.")
        return

    with st.container(border=True):
        st.markdown(f"### {job['title']}")
        st.write(job["description"])
        st.write(f'**Required skills:** {job["required_skills"]}')
        st.caption(f'Job ID: {job["id"]} · Created: {job["created_at"]}')

    st.divider()
    st.subheader("Match resumes to this job")

    st.write(
        "HireLens will analyse every stored resume PDF against this job. "
        "Existing results for this same job and resume are updated rather "
        "than duplicated."
    )

    if st.button(
        "Run Matching",
        type="primary",
        use_container_width=True,
        key=f"run_matching_{job_id}"
    ):
        resumes = get_resumes_for_matching()

        if not resumes:
            st.warning(
                "No saved resume PDFs were found. Upload resumes in the "
                "Upload Resumes tab first."
            )
        else:
            skills = [
                skill.strip()
                for skill in job["required_skills"].split(",")
                if skill.strip()
            ]

            progress = st.progress(0)
            status = st.empty()
            successful = 0
            errors = []

            for index, resume in enumerate(resumes):
                name = (
                    resume.get("candidate_name")
                    or resume.get("candidate_id")
                    or "Candidate"
                )
                app_id = resume.get("application_id") or "ID unavailable"

                status.write(
                    f"Analysing {index + 1} of {len(resumes)}: "
                    f"{name} ({app_id})"
                )

                try:
                    result = analyze_resume_pdf(
                        bytes(resume["resume_pdf"]),
                        job["description"],
                        skills
                    )

                    save_job_match(
                        job_id,
                        resume["id"],
                        result
                    )
                    successful += 1

                except Exception as exc:
                    errors.append(
                        f"{name} ({app_id}): {type(exc).__name__}: {exc}"
                    )

                progress.progress((index + 1) / len(resumes))

            status.empty()
            progress.empty()

            st.success(
                f"Matching complete: {successful} resume(s) analysed "
                f"successfully out of {len(resumes)}."
            )

            for error in errors:
                st.warning(error)

            st.rerun()

    st.divider()
    st.subheader("Matching results")

    matches = get_job_matches(job_id)

    if not matches:
        st.info(
            "No matching results yet. Click Run Matching to analyse "
            "the stored resumes against this job."
        )
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Resumes matched", len(matches))
    c2.metric(
        "Awaiting HR decision",
        sum(1 for match in matches if not match["hr_decision"])
    )
    c3.metric(
        "Decisions published",
        sum(1 for match in matches if match["published"])
    )

    st.caption(
        "Ranked by match score. Scores are advisory and must not be used "
        "as the sole basis for a hiring decision."
    )

    for rank, match in enumerate(matches, start=1):
        candidate_name = match.get("candidate_name") or "Candidate"
        app_id = match.get("source_application_id") or "ID unavailable"
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.markdown(f"### {rank}. {candidate_name}")
                st.write(f"**Application ID:** `{app_id}`")
                st.write(f'**Job:** {match["job_title"]}')
                st.write(f'**AI recommendation:** {match.get("ai_recommendation") or "Not available"}')
                st.write("**Matched skills:**", match.get("matched_skills") or "None detected")
                st.write("**Skills not detected:**", match.get("missing_skills") or "None detected")
                if match.get("hr_decision"):
                    st.write(f'**HR decision:** {match["hr_decision"]}')
                else:
                    st.write("**HR decision:** Not decided")
                if match.get("published"):
                    st.success("Decision published")
                elif match.get("hr_decision"):
                    st.info("Decision saved, not yet published")
            with right:
                st.metric("Match score", f'{float(match.get("match_score") or 0):.1f}/100')
                st.metric("Skill coverage", f'{float(match.get("skill_score") or 0):.1f}%')
            st.caption("For resume review and the detailed AI explanation, use Search Application ID. Save and publish human decisions in HR Decisions.")


# --------------------------------------------------
# HR UPLOAD RESUMES
# --------------------------------------------------

def hr_upload_tab():
    st.subheader("Upload resumes to the candidate pool")
    st.write(
        "Upload PDFs here to make them available for matching against "
        "any saved job. You do not need to enter job requirements here."
    )
    st.info(
        "These are HR-managed resume-pool records, not candidate-owned applications. "
        "They will not appear in a candidate's personal portal unless the candidate "
        "submits their own application."
    )

    staged = st.session_state.setdefault("staged_hr_resumes", {})
    newly_uploaded = st.file_uploader(
        "Upload candidate PDF resume(s)",
        type=["pdf"],
        accept_multiple_files=True,
        key="hr_pdfs"
    )

    # Copy uploads into session state immediately so switching sidebar sections
    # does not discard unsaved PDFs when Streamlit removes the uploader widget.
    if newly_uploaded:
        for pdf in newly_uploaded:
            pdf_bytes = pdf.getvalue()
            digest = hashlib.sha256(pdf_bytes).hexdigest()
            staged_key = f"{pdf.name}:{digest}"
            if staged_key not in staged:
                staged[staged_key] = {
                    "filename": pdf.name,
                    "bytes": pdf_bytes,
                    "digest": digest,
                    "name": Path(pdf.name).stem,
                }

    if staged:
        st.subheader(f"Pending uploads ({len(staged)})")
        st.caption(
            "Pending files stay available while you navigate between HR sections "
            "in this session. Save them to the database before closing or refreshing the app."
        )
        for staged_key, item in list(staged.items()):
            col_name, col_file, col_remove = st.columns([3, 2, 1])
            with col_name:
                item["name"] = st.text_input(
                    f"Candidate name · {item['filename']}",
                    value=item.get("name") or Path(item["filename"]).stem,
                    key=f"staged_name_{item['digest']}"
                )
            with col_file:
                st.caption(item["filename"])
            with col_remove:
                if st.button("Remove", key=f"remove_staged_{item['digest']}"):
                    staged.pop(staged_key, None)
                    st.rerun()

        if st.button(
            "Save Pending Resumes to Pool",
            type="primary",
            use_container_width=True
        ):
            success = 0
            skipped = 0
            errors = []

            for staged_key, item in list(staged.items()):
                try:
                    name = (
                        st.session_state.get(
                            f"staged_name_{item['digest']}",
                            item.get("name", "")
                        ).strip()
                        or Path(item["filename"]).stem
                    )
                    pdf_bytes = item["bytes"]

                    with sqlite3.connect(DB_PATH) as con:
                        con.row_factory = sqlite3.Row
                        existing = con.execute("""
                            SELECT application_id FROM candidates
                            WHERE applicant_user_id IS NULL
                              AND candidate_name = ?
                              AND resume_filename = ?
                              AND resume_pdf = ?
                            ORDER BY id DESC LIMIT 1
                        """, (
                            name, item["filename"], sqlite3.Binary(pdf_bytes)
                        )).fetchone()

                    if existing:
                        st.info(
                            f"{name} is already in the HR resume pool. "
                            f"Existing ID: {existing['application_id']}"
                        )
                        skipped += 1
                        staged.pop(staged_key, None)
                        continue

                    placeholder_result = {
                        "match_score": 0,
                        "skill_score": 0,
                        "text_similarity": 0,
                        "matched_skills": [],
                        "missing_skills": [],
                        "recommendation": (
                            "Not analyzed yet. Run matching against a saved job."
                        ),
                    }

                    record_id = save_analysis(
                        name,
                        "Resume Pool — Not Yet Matched",
                        placeholder_result,
                        applicant_user_id=None,
                        candidate_name=name,
                        resume_pdf=pdf_bytes,
                        resume_filename=item["filename"],
                    )

                    with sqlite3.connect(DB_PATH) as con:
                        row = con.execute(
                            "SELECT application_id FROM candidates WHERE id = ?",
                            (record_id,)
                        ).fetchone()

                    st.success(f"Saved {name} · Application ID: {row[0]}")
                    success += 1
                    staged.pop(staged_key, None)

                except Exception as exc:
                    errors.append(
                        f"{item['filename']}: {type(exc).__name__}: {exc}"
                    )

            for error in errors:
                st.error(f"Could not save {error}")

            if success:
                st.success(f"{success} resume(s) saved to the HR pool.")
            if skipped:
                st.info(f"{skipped} duplicate resume(s) skipped.")
            st.rerun()
    else:
        st.caption("No pending uploads.")


# --------------------------------------------------
# EXISTING APPLICATION SEARCH
# --------------------------------------------------

def application_search_tab():
    st.subheader("Search application and review resume")
    query = st.text_input("Application ID", placeholder="HL-1A2B3C4D", key="search_app_id")

    if st.button("Search Application", type="primary"):
        if not query.strip():
            st.error("Enter an application ID.")
        else:
            record = get_application_by_id(query.strip())
            if record:
                st.session_state["found_application_id"] = record["application_id"]
            else:
                st.session_state.pop("found_application_id", None)
                st.error("No application found for that ID.")

    found = st.session_state.get("found_application_id")
    if not found or query.strip().upper() != found:
        return

    record = get_application_by_id(found)
    if not record:
        st.error("The application record could not be loaded.")
        return

    st.write(f'**Candidate:** {record.get("candidate_name") or record["candidate_id"]}')
    st.write(f'**Application ID:** `{record["application_id"]}`')
    st.write(f'**Original job title:** {record["job_title"]}')
    # Keep this section focused on the application identity and original PDF.
    # Scores and skill details are shown once per saved-job match below.

    resume = get_application_resume(record["id"])
    if resume:
        st.download_button(
            "Download original resume", data=resume["resume_pdf"],
            file_name=resume.get("resume_filename") or f"{found}.pdf",
            mime="application/pdf", key=f"search_download_{record['id']}"
        )
    else:
        st.warning("This application has no saved PDF attached.")

    # Find every saved-job match tied to this exact source application.
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT jm.id AS match_id, jm.job_id, jm.match_score, jm.skill_score,
                   jm.matched_skills, jm.missing_skills, jm.ai_recommendation,
                   jm.hr_decision, jm.hr_feedback, jm.published,
                   j.title AS saved_job_title, j.description AS job_description,
                   j.required_skills
            FROM job_matches jm
            JOIN jobs j ON j.id = jm.job_id
            WHERE jm.source_candidate_id = ?
            ORDER BY jm.id DESC
        """, (record["id"],)).fetchall()
        matches = [dict(row) for row in rows]

    if matches:
        st.divider()
        st.subheader("Saved-job matching results and explanations")
        for match in matches:
            with st.expander(f'{match["saved_job_title"]} · Match #{match["match_id"]}', expanded=True):
                a, b = st.columns(2)
                a.metric("Match score", f'{float(match.get("match_score") or 0):.1f}/100')
                b.metric("Skill coverage", f'{float(match.get("skill_score") or 0):.1f}%')
                st.write("**AI recommendation:**", match.get("ai_recommendation") or "Not available")
                st.write("**Matched skills:**", match.get("matched_skills") or "None detected")
                st.write("**Skills not detected:**", match.get("missing_skills") or "None detected")
                if match.get("published") and match.get("hr_decision"):
                    st.success(f'Published HR decision: {match["hr_decision"]}')
                    if match.get("hr_feedback"):
                        st.write(f'**Published feedback:** {match["hr_feedback"]}')
                elif match.get("hr_decision"):
                    st.info(f'Decision saved but not published: {match["hr_decision"]}')
                else:
                    st.info("No HR decision has been saved for this job match yet.")

                source_resume = get_job_match_resume(match["match_id"])
                if source_resume and st.button(
                    "Generate detailed AI explanation",
                    key=f"search_explain_{match['match_id']}"
                ):
                    try:
                        detail = analyze_resume_pdf(
                            source_resume["resume_pdf"],
                            match["job_description"],
                            [
                                x.strip()
                                for x in (match.get("required_skills") or "").split(",")
                                if x.strip()
                            ]
                        )
                        st.session_state[f"explanation_{match['match_id']}"] = detail
                    except Exception as exc:
                        st.error(f"Could not generate explanation: {exc}")

                saved_detail = st.session_state.get(f"explanation_{match['match_id']}")
                if saved_detail:
                    with st.expander("Detailed AI explanation", expanded=True):
                        st.write("**Explanation**")
                        reasons = saved_detail.get("reasons", [])
                        if reasons:
                            for reason in reasons:
                                st.write(f"- {reason}")
                        else:
                            st.info(
                                "The analysis engine did not return separate "
                                "explanation reasons."
                            )
                        st.caption(
                            "This explanation describes textual alignment only. "
                            "It does not measure candidate worth or guarantee job "
                            "performance. HR makes the final decision."
                        )
    else:
        st.info("This application has not been matched against any saved HR job yet.")

    st.caption("AI scores are advisory. HR retains the final hiring decision.")


def existing_decisions_tab():
    st.subheader("Decisions for existing applications")

    rows = get_records()

    if not rows:
        st.info("No saved applications yet.")
        return

    choices = {
        (
            f'{r["application_id"] or r["candidate_id"]} · '
            f'{r.get("candidate_name") or r["candidate_id"]} · '
            f'{r["job_title"]}'
        ): r
        for r in rows
    }

    label = st.selectbox(
        "Select existing application",
        list(choices.keys())
    )
    record = choices[label]

    st.write(
        f'**Application ID:** `{record.get("application_id") or record["candidate_id"]}`'
    )
    st.write(
        f'**Candidate:** {record.get("candidate_name") or record["candidate_id"]}'
    )
    st.write(f'**Job:** {record["job_title"]}')
    st.write(f'**AI recommendation:** {record["ai_recommendation"]}')

    with st.form(f"existing_decision_form_{record['id']}"):
        options = ["Shortlist", "Reject", "Hold"]
        previous = record["hr_decision"]

        decision = st.radio(
            "HR final decision",
            options,
            horizontal=True,
            index=options.index(previous) if previous in options else 2
        )

        feedback = st.text_area(
            "HR feedback",
            value=record["hr_feedback"] or ""
        )

        save = st.form_submit_button(
            "Save HR Decision",
            type="primary",
            use_container_width=True
        )

    if save:
        try:
            record_hr_decision(record["id"], decision, feedback)
            st.success("Decision saved. It is not published yet.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save decision: {exc}")

    latest = get_application_by_id(
        record.get("application_id") or record["candidate_id"]
    )

    if latest and latest.get("hr_decision") and not latest["published"]:
        if st.button(
            "Publish Existing Application Decision",
            key=f"publish_existing_{record['id']}",
            use_container_width=True
        ):
            try:
                publish_decision(record["id"])
                st.success("Decision published.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not publish decision: {exc}")

    elif latest and latest["published"]:
        st.success("Decision is published.")


def job_match_decisions_page():
    st.subheader("Job-specific HR decisions")
    st.write(
        "Review each resume match, record the human HR decision, and publish "
        "the decision and feedback to the candidate."
    )

    jobs = get_jobs()
    if not jobs:
        st.info("Create and save a job first, then run matching in Job & Matching.")
    else:
        any_matches = False
        for job_item in jobs:
            matches = get_job_matches(job_item["id"])
            if not matches:
                continue
            any_matches = True
            with st.expander(f'{job_item["title"]} · Job #{job_item["id"]}', expanded=True):
                for match in matches:
                    any_matches = True
                    candidate_name = match.get("candidate_name") or "Candidate"
                    app_id = match.get("source_application_id") or "ID unavailable"
                    with st.container(border=True):
                        st.markdown(f'### {candidate_name}')
                        st.write(f'**Application ID:** `{app_id}`')
                        st.write(f'**AI recommendation:** {match.get("ai_recommendation") or "Not available"}')
                        st.write(
                            f'**Match score:** {float(match.get("match_score") or 0):.1f}/100 '
                            f' · **Skill coverage:** {float(match.get("skill_score") or 0):.1f}%'
                        )
                        if match.get("published"):
                            st.success(f'Decision published: {match.get("hr_decision") or "Not specified"}')
                        elif match.get("hr_decision"):
                            st.info(f'Decision saved, not published: {match["hr_decision"]}')
                        else:
                            st.info("No HR decision saved yet.")

                        with st.form(f"decision_page_form_{match['match_id']}"):
                            options = ["Shortlist", "Reject", "Hold"]
                            previous = match.get("hr_decision")
                            decision = st.radio(
                                "HR final decision",
                                options,
                                horizontal=True,
                                index=options.index(previous) if previous in options else 2,
                                key=f"decision_page_value_{match['match_id']}"
                            )
                            feedback = st.text_area(
                                "Feedback for candidate",
                                value=match.get("hr_feedback") or "",
                                key=f"decision_page_feedback_{match['match_id']}"
                            )
                            save_decision = st.form_submit_button(
                                "Save HR Decision",
                                type="primary"
                            )

                        if save_decision:
                            try:
                                record_job_match_decision(match["match_id"], decision, feedback)
                                st.success("HR decision saved. Publish it when ready.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Could not save decision: {exc}")

                        if match.get("hr_decision") and not match.get("published"):
                            if st.button(
                                "Publish Decision to Candidate",
                                key=f"decision_page_publish_{match['match_id']}",
                                use_container_width=True
                            ):
                                try:
                                    publish_job_match_decision(match["match_id"])
                                    st.success("Decision published to the candidate portal.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Could not publish decision: {exc}")

        if not any_matches:
            st.info("No job matches yet. Run matching from Job Requirements first.")

    st.divider()
    with st.expander("Legacy application decisions"):
        existing_decisions_tab()


# --------------------------------------------------
# HR DASHBOARD
# --------------------------------------------------

def hr_page(user):
    brand()

    st.sidebar.title("HR / Recruiter")
    st.sidebar.write(f"Signed in as **{user['full_name']}**")
    st.sidebar.caption("Authorized HR account")
    st.sidebar.divider()
    section = st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Job & Matching",
            "Upload Resumes",
            "Search Application ID",
            "HR Decisions",
            "About",
        ],
        key="hr_sidebar_navigation"
    )
    logout()

    st.markdown('<div class="hl-page-kicker">HR workspace</div><div class="hl-page-title">Recruiter dashboard</div><div class="hl-page-sub">Manage roles, compare resume alignment, and communicate human decisions.</div>', unsafe_allow_html=True)

    if section == "Overview":
        rows = get_records()
        jobs = get_jobs()
        pending = sum(1 for r in rows if not r.get("hr_decision"))
        shortlisted = sum(1 for r in rows if r.get("hr_decision") == "Shortlist")
        rejected = sum(1 for r in rows if r.get("hr_decision") == "Reject")
        on_hold = sum(1 for r in rows if r.get("hr_decision") == "Hold")
        published = sum(1 for r in rows if r.get("published"))

        st.markdown("""<div class="hl-page-kicker">Recruitment workspace</div>
        <div class="hl-page-title">Your hiring overview</div>
        <div class="hl-page-sub">Here is a snapshot of your hiring activity and application pipeline.</div>""", unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Resume records", len(rows), help="All candidate and HR-uploaded resume records")
        k2.metric("Active job posts", len(jobs))
        k3.metric("Awaiting decision", pending)
        k4.metric("Decisions published", published)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="hl-panel"><div class="hl-panel-title">Application decision overview</div>'
            '<div class="hl-muted">Current HR decisions across stored resume records</div></div>',
            unsafe_allow_html=True
        )
        decision_rows = [
            ("Awaiting decision", pending, "#64748b"),
            ("Shortlisted", shortlisted, "#16a085"),
            ("On hold", on_hold, "#d99b25"),
            ("Rejected", rejected, "#e05a67"),
        ]
        max_value = max([value for _, value, _ in decision_rows] + [1])
        chart_html = '<div class="hl-decision-chart">'
        for label, value, color in decision_rows:
            width = (value / max_value) * 100
            chart_html += (
                '<div class="hl-chart-row"><div class="hl-chart-label">' + label + '</div>'
                '<div class="hl-chart-track"><div class="hl-chart-fill" style="width:' + str(width) +
                '%;background:' + color + '"></div></div><div class="hl-chart-value">' + str(value) + '</div></div>'
            )
        chart_html += '</div>'
        st.markdown(chart_html, unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("### Recent application records")
        if rows:
            preview = []
            for record in rows[:6]:
                preview.append({
                    "Candidate": record.get("candidate_name") or record.get("candidate_id") or "Candidate",
                    "Application ID": record.get("application_id") or "—",
                    "Job title": record.get("job_title") or "—",
                    "AI recommendation": record.get("ai_recommendation") or "Not analyzed",
                    "HR status": record.get("hr_decision") or "Awaiting decision",
                })
            st.dataframe(preview, use_container_width=True, hide_index=True)
        else:
            st.info("No application records yet. Upload resumes or receive candidate submissions to get started.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="hl-panel"><div class="hl-panel-title">Responsible AI reminder</div><div class="hl-muted">HireLens provides an explainable, text-based comparison to support review. A skill not detected in a resume does not prove the candidate lacks it. AI scores and recommendations are advisory only; the authorized HR reviewer makes and publishes the final decision.</div></div>', unsafe_allow_html=True)

    elif section == "Job & Matching":
        job_requirements_tab(user)

    elif section == "Upload Resumes":
        hr_upload_tab()

    elif section == "Search Application ID":
        application_search_tab()

    elif section == "HR Decisions":
        job_match_decisions_page()

    elif section == "About":
        st.subheader("Responsible-use principles")
        st.write(
            "- AI recommendations are advisory; HR makes the final decision."
        )
        st.write(
            "- A skill not detected in a resume does not prove the candidate lacks it."
        )
        st.write(
            "- Scores measure textual alignment, not candidate worth or guaranteed job performance."
        )
        st.divider()
        st.subheader("Project Team")
        left, right = st.columns(2)
        with left:
            st.markdown("### Aniket Kale")
            st.write("Backend & AI Integration")
        with right:
            st.markdown("### Sagar Chandratre")
            st.write("Frontend & UI Design")


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if "hirelens_user" not in st.session_state:
    st.session_state["hirelens_user"] = None

if st.session_state["hirelens_user"] is None:
    login_page()
    st.stop()

user = st.session_state["hirelens_user"]

if user.get("role") == "candidate":
    candidate_page(user)

elif user.get("role") == "hr":
    hr_page(user)

else:
    st.session_state["hirelens_user"] = None
    st.error("Invalid account role. Please log in again.")
    st.stop()
