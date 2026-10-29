import os
import sqlite3
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
.stApp {
    background: radial-gradient(
        ellipse at 8% 0%,
        rgba(40,120,155,.16),
        transparent 34%
    ), linear-gradient(
        160deg,#0b1220 0%,#101827 52%,#0b1220 100%
    );
    color: #e8eef7;
}
[data-testid="stHeader"] {background:rgba(11,18,32,.82)}
.block-container {
    max-width:1400px;
    padding-top:1.5rem;
    padding-bottom:3rem;
}
[data-testid="stMetric"] {
    background:linear-gradient(
        145deg,rgba(27,41,64,.94),rgba(21,31,48,.94)
    );
    border:1px solid rgba(128,165,202,.19);
    padding:1rem;
    border-radius:16px;
}
[data-testid="stTabs"] [role="tablist"] {gap:.65rem}
[data-testid="stTabs"] button[role="tab"] {
    padding:.7rem .9rem;
    font-weight:650;
    white-space:nowrap;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color:#43d9c5;
    border-bottom:3px solid #43d9c5;
}
.stButton>button,
[data-testid="stFormSubmitButton"]>button {
    border-radius:10px;
    min-height:2.7rem;
    font-weight:700;
}
.stButton>button[kind="primary"],
[data-testid="stFormSubmitButton"]>button[kind="primary"] {
    background:linear-gradient(100deg,#087f8c,#0c9b91);
    color:white;
    border:0;
}
.hl-hero {
    padding:1.4rem 1.6rem;
    margin:.3rem 0 1.2rem;
    border-radius:20px;
    border:1px solid rgba(93,211,213,.24);
    background:linear-gradient(
        115deg,rgba(22,55,77,.92),
        rgba(21,31,48,.96) 62%,rgba(31,53,77,.9)
    );
}
.hl-brand {
    color:white;
    font-size:clamp(2rem,4vw,3rem);
    line-height:1.08;
    font-weight:850;
    letter-spacing:-.05em;
}
.hl-brand span {color:#43d9c5}
.hl-subtitle {
    color:#d5e3f5;
    font-size:1.05rem;
    margin-top:.6rem;
    margin-bottom:.9rem;
}
.hl-note {
    display:inline-block;
    color:#bff7ee;
    background:rgba(67,217,197,.09);
    border:1px solid rgba(67,217,197,.22);
    border-radius:999px;
    padding:.4rem .75rem;
    font-size:.85rem;
    font-weight:650;
}


/* --------------------------------------------------
   FIX: readable text in job descriptions and form fields
   Applies to both candidate and HR portals.
-------------------------------------------------- */
.stTextArea textarea,
.stTextInput input,
.stNumberInput input,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
    background-color: #ffffff !important;
    opacity: 1 !important;
    caret-color: #172033 !important;
}

.stTextArea textarea::placeholder,
.stTextInput input::placeholder,
[data-baseweb="textarea"] textarea::placeholder,
[data-baseweb="input"] input::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
}

.stTextArea label,
.stTextInput label,
.stNumberInput label {
    color: #e8eef7 !important;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# BRANDING AND COMMON HELPERS
# --------------------------------------------------

def brand():
    st.markdown("""
    <div class="hl-hero">
      <div class="hl-brand">🔎 Hire<span>Lens</span></div>
      <div class="hl-subtitle">
        An Explainable AI Hiring Decision Analysis Dashboard
      </div>
      <span class="hl-note">
        Human-led decisions · Explainable analysis · Responsible AI
      </span>
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
            "Analyze and Submit",
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

    return st.session_state.get(f"{key}_job")


def show_result(result):
    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Match score",
        f'{float(result.get("match_score", 0)):.1f}/100'
    )
    c2.metric(
        "Skill coverage",
        f'{float(result.get("skill_score", 0)):.1f}%'
    )
    c3.metric(
        "Text similarity",
        f'{float(result.get("text_similarity", 0)):.1f}/100'
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
        st.info(
            "The analysis engine did not return separate explanation reasons."
        )

    st.caption(
        "Scores measure textual alignment; they do not measure candidate "
        "worth or guarantee job performance."
    )


def submit_resumes(files, job, owner_id=None, owner_name=None):
    if not job:
        st.error("Enter and submit the job requirements first.")
        return

    if not files:
        st.error("Please upload at least one PDF resume.")
        return

    success = 0

    for pdf in files:
        try:
            pdf_bytes = pdf.getvalue()

            result = analyze_resume_pdf(
                pdf_bytes,
                job["description"],
                job["skills"]
            )

            if owner_id is not None:
                name = owner_name
            else:
                name = (
                    st.session_state.get(f"name_{pdf.name}", "").strip()
                    or Path(pdf.name).stem
                )

            record_id = save_analysis(
                name,
                job["title"],
                result,
                applicant_user_id=owner_id,
                candidate_name=name,
                resume_pdf=pdf_bytes,
                resume_filename=pdf.name,
            )

            with sqlite3.connect(DB_PATH) as con:
                row = con.execute(
                    "SELECT application_id FROM candidates WHERE id = ?",
                    (record_id,)
                ).fetchone()

            app_id = row[0]

            st.success(f"Saved application ID: {app_id}")

            with st.expander(
                f"Analysis for {name} · {app_id}",
                expanded=True
            ):
                show_result(result)

            success += 1

        except Exception as exc:
            st.error(
                f"Could not process {pdf.name}: "
                f"{type(exc).__name__}: {exc}"
            )

    if success:
        st.info(
            "Applications saved. Their original PDFs are available "
            "for matching against saved jobs."
        )


def logout():
    if st.sidebar.button("Log out", use_container_width=True):
        st.session_state.pop("hirelens_user", None)
        st.rerun()


# --------------------------------------------------
# LOGIN AND REGISTRATION
# --------------------------------------------------

def login_page():
    brand()

    st.subheader("Welcome to your hiring workspace")
    st.write(
        "Choose the appropriate account type. Candidate registration "
        "never creates an HR account."
    )

    tab_login, tab_register, tab_hr = st.tabs([
        "Login",
        "Candidate Registration",
        "Authorized HR Setup"
    ])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )
            submit = st.form_submit_button(
                "Login",
                type="primary",
                use_container_width=True
            )

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
            password = st.text_input(
                "Password (minimum 10 characters)",
                type="password",
                key="reg_password"
            )
            confirm = st.text_input(
                "Confirm password",
                type="password",
                key="reg_confirm"
            )
            submit = st.form_submit_button(
                "Create Candidate Account",
                type="primary",
                use_container_width=True
            )

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
        st.warning(
            "HR registration requires the administrator's private "
            "HIRELENS_HR_INVITE_KEY secret."
        )

        with st.form("hr_register"):
            name = st.text_input("HR full name", key="hr_reg_name")
            email = st.text_input("Work email", key="hr_reg_email")
            password = st.text_input(
                "Password (minimum 10 characters)",
                type="password",
                key="hr_reg_password"
            )
            confirm = st.text_input(
                "Confirm password",
                type="password",
                key="hr_reg_confirm"
            )
            invite = st.text_input(
                "HR authorization key",
                type="password",
                key="hr_reg_invite"
            )
            submit = st.form_submit_button(
                "Create Authorized HR Account",
                type="primary",
                use_container_width=True
            )

        if submit:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    create_authorized_hr_user(
                        name, email, password, invite
                    )
                    st.success("HR account created. Please log in.")
                except Exception as exc:
                    st.error(str(exc))


# --------------------------------------------------
# CANDIDATE PORTAL
# --------------------------------------------------

def candidate_page(user):
    brand()

    st.sidebar.title("Candidate Portal")
    st.sidebar.write(f"Signed in as **{user['full_name']}**")
    logout()

    st.title("Your Candidate Dashboard")

    upload_tab, apps_tab, about_tab = st.tabs([
        "Upload Resume",
        "My Applications",
        "About"
    ])

    with upload_tab:
        st.write(
            "Enter the job details for the position you want to apply for."
        )

        job = job_form("candidate")

        files = st.file_uploader(
            "Upload resume PDF(s)",
            type=["pdf"],
            accept_multiple_files=True,
            key="candidate_pdfs"
        )

        if st.button(
            "Analyze and Submit",
            type="primary",
            use_container_width=True
        ):
            submit_resumes(
                files,
                job,
                owner_id=user["id"],
                owner_name=user["full_name"]
            )

    with apps_tab:
        apps = get_candidate_applications(user["id"])

        if not apps:
            st.info("You have no applications yet.")

        for app in apps:
            with st.container(border=True):
                st.subheader(app["job_title"])
                st.write(f'**Application ID:** `{app["application_id"]}`')
                st.write(f'**Submitted:** {app["created_at"]}')
                st.metric(
                    "Match score",
                    f'{float(app["match_score"]):.1f}/100'
                )

                if app["published"]:
                    st.success(
                        f'Published decision: {app["hr_decision"]}'
                    )
                    if app.get("hr_feedback"):
                        st.write(f'**HR feedback:** {app["hr_feedback"]}')
                elif app["hr_decision"]:
                    st.info(
                        "HR has saved a decision, but has not published it."
                    )
                else:
                    st.info(
                        "Application submitted. No decision published yet."
                    )

    with about_tab:
        st.info(
            "AI scores are advisory and do not measure a candidate's "
            "worth or guarantee job performance."
        )


# --------------------------------------------------
# HR JOB REQUIREMENTS AND MATCHING WORKSPACE
# --------------------------------------------------

def job_requirements_tab(user):
    st.subheader("Create a job")
    st.write(
        "Save job requirements once, then match them against all stored "
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
            st.success("Job saved permanently.")
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
    st.subheader("Match all saved resumes")

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
                st.write(
                    f'**AI recommendation:** {match["ai_recommendation"]}'
                )

                if match["hr_decision"]:
                    st.write(f'**HR decision:** {match["hr_decision"]}')
                else:
                    st.write("**HR decision:** Not decided")

                if match["published"]:
                    st.success("Decision published")
                elif match["hr_decision"]:
                    st.info("Decision saved, not yet published")

            with right:
                st.metric(
                    "Match score",
                    f'{float(match["match_score"]):.1f}/100'
                )
                st.metric(
                    "Skill coverage",
                    f'{float(match["skill_score"]):.1f}%'
                )

            with st.expander("Review resume and explanation"):
                resume = get_job_match_resume(match["match_id"])

                if resume:
                    st.download_button(
                        "Download original resume",
                        data=resume["resume_pdf"],
                        file_name=(
                            resume["resume_filename"]
                            or f"{app_id}.pdf"
                        ),
                        mime="application/pdf",
                        key=f"download_match_{match['match_id']}"
                    )
                else:
                    st.warning("The original resume PDF is unavailable.")

                st.write("**Matched skills**")
                st.write(match["matched_skills"] or "None detected")

                st.write("**Skills not detected**")
                st.write(match["missing_skills"] or "None detected")

                # Re-run the analysis to show detailed explanation reasons.
                if resume and st.button(
                    "Show detailed AI explanation",
                    key=f"explain_match_{match['match_id']}"
                ):
                    try:
                        detailed = analyze_resume_pdf(
                            resume["resume_pdf"],
                            job["description"],
                            [
                                skill.strip()
                                for skill in job["required_skills"].split(",")
                                if skill.strip()
                            ]
                        )
                        show_result(detailed)
                    except Exception as exc:
                        st.error(f"Could not generate explanation: {exc}")

            with st.form(f"job_match_decision_{match['match_id']}"):
                options = ["Shortlist", "Reject", "Hold"]
                previous = match["hr_decision"]

                decision = st.radio(
                    "HR final decision",
                    options,
                    horizontal=True,
                    index=(
                        options.index(previous)
                        if previous in options else 2
                    ),
                    key=f"decision_value_{match['match_id']}"
                )

                feedback = st.text_area(
                    "Feedback for candidate",
                    value=match["hr_feedback"] or "",
                    key=f"feedback_value_{match['match_id']}"
                )

                save_decision = st.form_submit_button(
                    "Save HR Decision",
                    type="primary"
                )

            if save_decision:
                try:
                    record_job_match_decision(
                        match["match_id"],
                        decision,
                        feedback
                    )
                    st.success(
                        "HR decision saved. It is not published yet."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save decision: {exc}")

            latest = next(
                (
                    item for item in get_job_matches(job_id)
                    if item["match_id"] == match["match_id"]
                ),
                None
            )

            if latest and latest["hr_decision"] and not latest["published"]:
                if st.button(
                    "Publish Decision to Candidate",
                    key=f"publish_job_match_{match['match_id']}",
                    use_container_width=True
                ):
                    try:
                        publish_job_match_decision(match["match_id"])
                        st.success("Decision published.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not publish decision: {exc}")


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
        "These uploads are stored with a generated application ID. "
        "Their matching scores are calculated when you run a saved job."
    )

    files = st.file_uploader(
        "Upload candidate PDF resume(s)",
        type=["pdf"],
        accept_multiple_files=True,
        key="hr_pdfs"
    )

    if files:
        for pdf in files:
            st.text_input(
                f"Candidate name for {pdf.name}",
                value=Path(pdf.name).stem,
                key=f"name_{pdf.name}"
            )

    if st.button(
        "Save Resumes to Pool",
        type="primary",
        use_container_width=True
    ):
        if not files:
            st.error("Please upload at least one PDF resume.")
            return

        success = 0

        for pdf in files:
            try:
                name = (
                    st.session_state.get(f"name_{pdf.name}", "").strip()
                    or Path(pdf.name).stem
                )

                # The current candidates schema requires non-null analysis
                # fields. These values are explicitly placeholders only.
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
                    resume_pdf=pdf.getvalue(),
                    resume_filename=pdf.name,
                )

                with sqlite3.connect(DB_PATH) as con:
                    row = con.execute(
                        "SELECT application_id FROM candidates WHERE id = ?",
                        (record_id,)
                    ).fetchone()

                st.success(
                    f"Saved {name} · Application ID: {row[0]}"
                )
                success += 1

            except Exception as exc:
                st.error(
                    f"Could not save {pdf.name}: "
                    f"{type(exc).__name__}: {exc}"
                )

        if success:
            st.info(
                f"{success} resume(s) added to the pool. "
                "Open Job Requirements and run matching."
            )


# --------------------------------------------------
# EXISTING APPLICATION SEARCH
# --------------------------------------------------

def application_search_tab():
    st.subheader("Search existing application")

    query = st.text_input(
        "Application ID",
        placeholder="HL-1A2B3C4D",
        key="search_app_id"
    )

    if st.button("Search Application", type="primary"):
        if not query.strip():
            st.error("Enter an application ID.")
        else:
            record = get_application_by_id(query.strip())

            if record:
                st.session_state["found_application_id"] = (
                    record["application_id"]
                )
            else:
                st.session_state.pop("found_application_id", None)
                st.error("No application found for that ID.")

    found = st.session_state.get("found_application_id")

    if found and query.strip().upper() == found:
        record = get_application_by_id(found)

        if record:
            st.write(
                f'**Candidate:** {record.get("candidate_name") or record["candidate_id"]}'
            )
            st.write(f'**Application ID:** `{record["application_id"]}`')
            st.write(f'**Job title:** {record["job_title"]}')

            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Match score",
                f'{float(record["match_score"]):.1f}/100'
            )
            c2.metric(
                "Skill coverage",
                f'{float(record["skill_score"]):.1f}%'
            )
            c3.metric(
                "Text similarity",
                f'{float(record["text_similarity"]):.1f}/100'
            )

            st.write("**Matched skills:**", record["matched_skills"] or "None")
            st.write("**Skills not detected:**", record["missing_skills"] or "None")
            st.write("**AI recommendation:**", record["ai_recommendation"])
            st.write("**HR decision:**", record["hr_decision"] or "Not decided")
            st.write(
                "**Publication status:**",
                "Published" if record["published"] else "Not published"
            )

            resume = get_application_resume(record["id"])

            if resume:
                st.download_button(
                    "Download original resume",
                    data=resume["resume_pdf"],
                    file_name=resume["resume_filename"] or f"{found}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("This application has no saved PDF attached.")


# --------------------------------------------------
# EXISTING APPLICATION DECISIONS
# --------------------------------------------------

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


# --------------------------------------------------
# HR DASHBOARD
# --------------------------------------------------

def hr_page(user):
    brand()

    st.sidebar.title("HR / Recruiter")
    st.sidebar.write(f"Signed in as **{user['full_name']}**")
    st.sidebar.caption("Authorized HR account")
    logout()

    st.title("HR / Recruiter Dashboard")

    overview, requirements, upload, search, decisions, about = st.tabs([
        "Overview",
        "Job Requirements",
        "Upload Resumes",
        "Search Application ID",
        "HR Decisions",
        "About"
    ])

    with overview:
        rows = get_records()
        jobs = get_jobs()

        c1, c2, c3 = st.columns(3)
        c1.metric("Stored resume records", len(rows))
        c2.metric("Saved jobs", len(jobs))
        c3.metric(
            "Awaiting decision",
            sum(1 for r in rows if not r["hr_decision"])
        )

        st.info(
            "AI recommendations are advisory. HR retains the final decision. "
            "Use Job Requirements to match all stored resumes against a job."
        )

    with requirements:
        job_requirements_tab(user)

    with upload:
        hr_upload_tab()

    with search:
        application_search_tab()

    with decisions:
        existing_decisions_tab()

    with about:
        st.subheader("Responsible-use principles")
        st.write(
            "- AI recommendations are advisory; HR makes the final decision."
        )
        st.write(
            "- A skill not detected in a resume does not prove the "
            "candidate lacks it."
        )
        st.write(
            "- Scores measure textual alignment, not candidate worth "
            "or guaranteed job performance."
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
