import sqlite3
from pathlib import Path

import streamlit as st

from backend_service import analyze_resume_pdf
from database import (
    DB_PATH,
    save_analysis,
    record_hr_decision,
    publish_decision,
    get_published_decision,
)

st.set_page_config(
    page_title="HireLens",
    page_icon="🔎",
    layout="wide",
)

# ---------- HireLens visual theme ----------
st.markdown("""
<style>
    :root {
        --hl-ink: #e8eef7;
        --hl-muted: #a9b8cc;
        --hl-teal: #43d9c5;
        --hl-blue: #6ba8ff;
        --hl-panel: #151f30;
        --hl-panel2: #1b2940;
    }
    .stApp {
        background:
          radial-gradient(ellipse at 8% 0%, rgba(40, 120, 155, .16), transparent 34%),
          linear-gradient(160deg, #0b1220 0%, #101827 52%, #0b1220 100%);
        color: var(--hl-ink);
    }
    [data-testid="stHeader"] {
        background: rgba(11, 18, 32, .82);
    }
    .block-container {
        max-width: 1440px;
        padding-top: 1.8rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3 {
        letter-spacing: -0.035em;
    }
    h1 { font-weight: 800 !important; }
    h2, h3 { font-weight: 700 !important; }
    [data-testid="stCaptionContainer"] p,
    .stMarkdown small {
        color: var(--hl-muted);
    }
    [data-testid="stTabs"] [role="tablist"] {
        gap: .9rem;
        border-bottom: 1px solid rgba(148, 170, 200, .18);
        padding: .15rem .1rem 0 .1rem;
    }
    [data-testid="stTabs"] button[role="tab"] {
        border-radius: 10px 10px 0 0;
        padding: .85rem 1.15rem;
        margin-right: .15rem;
        font-weight: 650;
        white-space: nowrap;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: var(--hl-teal);
        border-bottom: 3px solid var(--hl-teal);
        background: rgba(67, 217, 197, .07);
    }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(27, 41, 64, .94), rgba(21, 31, 48, .94));
        border: 1px solid rgba(128, 165, 202, .19);
        padding: 1.1rem 1.2rem;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, .13);
    }
    [data-testid="stMetricLabel"] p {
        color: var(--hl-muted);
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: var(--hl-ink);
        font-weight: 800;
    }
    div[data-testid="stForm"],
    div[data-testid="stExpander"],
    div[data-testid="stFileUploader"],
    div[data-testid="stAlert"] {
        border-radius: 14px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid rgba(128, 165, 202, .2);
        background: rgba(21, 31, 48, .55);
        overflow: hidden;
    }
    .stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
        border-radius: 10px !important;
    }
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        border-radius: 10px;
        min-height: 2.8rem;
        font-weight: 700;
        transition: transform .15s ease, border-color .15s ease;
    }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px);
        border-color: var(--hl-teal);
    }
    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background: linear-gradient(100deg, #087f8c, #0c9b91);
        color: white;
        border: 0;
    }
    .hl-hero {
        padding: 1.5rem 1.7rem;
        margin: .4rem 0 1.25rem 0;
        border-radius: 20px;
        border: 1px solid rgba(93, 211, 213, .24);
        background: linear-gradient(115deg, rgba(22, 55, 77, .92), rgba(21, 31, 48, .96) 62%, rgba(31, 53, 77, .9));
        box-shadow: 0 14px 36px rgba(0, 0, 0, .16);
    }
    .hl-brand {
        color: #ffffff;
        font-size: clamp(2.1rem, 4vw, 3.2rem);
        line-height: 1.08;
        font-weight: 850;
        letter-spacing: -.05em;
        margin: 0;
    }
    .hl-brand span { color: var(--hl-teal); }
    .hl-subtitle {
        color: #d5e3f5;
        font-size: 1.08rem;
        margin-top: .65rem;
        margin-bottom: .95rem;
    }
    .hl-note {
        display: inline-block;
        color: #bff7ee;
        background: rgba(67, 217, 197, .09);
        border: 1px solid rgba(67, 217, 197, .22);
        border-radius: 999px;
        padding: .4rem .75rem;
        font-size: .86rem;
        font-weight: 650;
    }
    .hl-section-kicker {
        color: var(--hl-teal);
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .13em;
        font-weight: 800;
        margin-bottom: .3rem;
    }
    .hl-step {
        background: rgba(21, 31, 48, .8);
        border: 1px solid rgba(128, 165, 202, .18);
        border-radius: 14px;
        padding: 1rem;
        min-height: 116px;
    }
    .hl-step-number {
        color: var(--hl-teal);
        font-weight: 850;
        font-size: .78rem;
        letter-spacing: .08em;
        text-transform: uppercase;
    }
    .hl-step-title {
        color: #f2f6fc;
        font-weight: 750;
        margin: .35rem 0;
    }
    .hl-step-desc { color: var(--hl-muted); font-size: .9rem; }
    hr { border-color: rgba(148, 170, 200, .16); }
    @media (max-width: 700px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .hl-hero { padding: 1.15rem; }
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hl-hero">
  <div class="hl-brand">🔎 Hire<span>Lens</span></div>
  <div class="hl-subtitle">An Explainable AI Hiring Decision Analysis Dashboard</div>
  <span class="hl-note">Human-led decisions · Explainable analysis · Responsible AI</span>
</div>
""", unsafe_allow_html=True)

st.info(
    "AI assists HR with evidence-based analysis. "
    "The final hiring decision belongs to a human."
)
st.caption(
    "Match scores describe resume-to-job text alignment. They do not measure "
    "a candidate's worth or guarantee future job performance."
)

# Keep results across Streamlit reruns.
if "hirelens_analyses" not in st.session_state:
    st.session_state.hirelens_analyses = {}
if "hirelens_notices" not in st.session_state:
    st.session_state.hirelens_notices = []


def read_saved_records():
    """Read saved rows for the HR dashboard without modifying database.py."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT id, candidate_id, job_title, match_score, skill_score,
                       text_similarity, matched_skills, missing_skills,
                       ai_recommendation, hr_decision, hr_feedback, published,
                       created_at
                FROM candidates
                ORDER BY id DESC
                """
            ).fetchall()
        except sqlite3.OperationalError:
            # The table is created by the existing database functions.
            return []
    return [dict(row) for row in rows]


def format_list(value):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [item.strip() for item in str(value).split(",") if item.strip()]


overview_tab, requirements_tab, analysis_tab, hr_tab, portal_tab, about_tab = st.tabs(
    [
        "Home / Overview",
        "Job Requirements",
        "Candidate Analysis",
        "HR Decision",
        "Candidate Portal",
        "About HireLens",
    ]
)

with overview_tab:
    st.markdown('<div class="hl-section-kicker">Your workspace</div>', unsafe_allow_html=True)
    st.header("Welcome to your hiring workspace")
    st.write(
        "Compare resume evidence with role requirements, understand the AI's "
        "reasoning, and keep every final decision in human hands."
    )
    records = read_saved_records()
    total = len(records)
    published_count = sum(1 for row in records if row["published"])
    pending_count = sum(
        1 for row in records
        if row["hr_decision"] and not row["published"]
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Saved analyses", total)
    c2.metric("Decisions awaiting publication", pending_count)
    c3.metric("Published decisions", published_count)
    st.divider()
    st.markdown('<div class="hl-section-kicker">How it works</div>', unsafe_allow_html=True)
    st.subheader("A transparent, human-led workflow")
    steps = [
        ("01", "Define the role", "Add the job description and required skills."),
        ("02", "Analyze resumes", "Extract evidence and compare it with the role."),
        ("03", "Review explanations", "Inspect match signals, detected skills, and gaps."),
        ("04", "Make an HR decision", "A human reviewer chooses the outcome."),
        ("05", "Publish the result", "Candidates see only decisions HR has published."),
    ]
    step_cols = st.columns(5)
    for col, (number, title, description) in zip(step_cols, steps):
        with col:
            st.markdown(
                f'<div class="hl-step"><div class="hl-step-number">STEP {number}</div>'
                f'<div class="hl-step-title">{title}</div>'
                f'<div class="hl-step-desc">{description}</div></div>',
                unsafe_allow_html=True,
            )

with requirements_tab:
    st.header("1. Job Requirements")
    st.write(
        "Enter the job details here. These values are used when you analyze "
        "resumes in the Candidate Analysis tab."
    )
    with st.form("job_requirements_form"):
        job_title_input = st.text_input(
            "Job title",
            placeholder="e.g., Junior Python Developer",
            key="job_title_input",
        )
        job_description_input = st.text_area(
            "Job description",
            placeholder="Describe the role and its responsibilities...",
            height=160,
            key="job_description_input",
        )
        required_skills_input = st.text_input(
            "Required skills (separate with commas)",
            placeholder="Python, SQL, Pandas, Git, Docker",
            key="required_skills_input",
        )
        st.form_submit_button(
            "Save job details",
            type="primary",
            use_container_width=True,
        )
    st.caption("Job details remain in this Streamlit session.")

with analysis_tab:
    st.header("2. Candidate Analysis")
    st.write(
        "Upload PDF resumes. Each file is analyzed by your existing "
        "`backend_service.analyze_resume_pdf()` function."
    )
    job_title = st.session_state.get("job_title_input", "").strip()
    job_description = st.session_state.get("job_description_input", "").strip()
    skills_text = st.session_state.get("required_skills_input", "")
    required_skills = [s.strip() for s in skills_text.split(",") if s.strip()]

    if not job_title or not job_description.strip() or not required_skills:
        st.warning(
            "First open Job Requirements and enter a job title, job description, "
            "and at least one required skill."
        )
    else:
        st.info(
            f"Current role: **{job_title}**  \n"
            f"Required skills: {', '.join(required_skills)}"
        )

    id_mode = st.radio(
        "How would you like to assign candidate IDs?",
        ["Generate IDs automatically", "Enter IDs manually"],
        horizontal=True,
        key="candidate_id_mode",
        help="Choose automatic IDs for a batch, or provide one ID per PDF in upload order.",
    )
    if id_mode == "Generate IDs automatically":
        candidate_id_prefix = st.text_input(
            "Candidate ID prefix",
            value="DEMO",
            help="For three uploaded PDFs, the IDs will be DEMO-01, DEMO-02, and DEMO-03.",
            key="candidate_id_prefix",
        ).strip()
        manual_candidate_ids = []
    else:
        candidate_id_prefix = ""
        manual_ids_text = st.text_area(
            "Candidate IDs (one per line or separated by commas)",
            placeholder="DEMO-001\nDEMO-002\nDEMO-003",
            height=110,
            key="manual_candidate_ids",
            help="Enter exactly one unique ID for each uploaded PDF, in the same order as the files appear below.",
        )
        manual_candidate_ids = [
            value.strip()
            for line in manual_ids_text.splitlines()
            for value in line.split(",")
            if value.strip()
        ]

    uploaded_files = st.file_uploader(
        "Upload candidate resumes (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key="resume_pdf_uploads",
    )

    if st.button(
        "Analyze and Save Resumes",
        type="primary",
        use_container_width=True,
        disabled=not (
            job_title and job_description.strip() and required_skills
            and uploaded_files
            and (
                bool(candidate_id_prefix)
                if id_mode == "Generate IDs automatically"
                else bool(manual_candidate_ids)
            )
        ),
    ):
        results_for_run = []
        errors = []
        if id_mode == "Generate IDs automatically":
            candidate_ids = [f"{candidate_id_prefix}-{index:02d}" for index in range(1, len(uploaded_files) + 1)]
        else:
            candidate_ids = manual_candidate_ids

        # Validate the whole batch before saving any record.
        if len(candidate_ids) != len(uploaded_files):
            st.error(
                f"You uploaded {len(uploaded_files)} PDF(s) but supplied "
                f"{len(candidate_ids)} candidate ID(s). Please make the counts match."
            )
        elif len(set(candidate_ids)) != len(candidate_ids):
            st.error("Duplicate IDs detected in your entry. Each resume must have a different candidate ID.")
        else:
            existing_ids = {str(row["candidate_id"]).strip() for row in read_saved_records()}
            duplicate_existing = sorted(set(candidate_ids) & existing_ids)
            if duplicate_existing:
                st.error(
                    "These candidate IDs already exist in the database: "
                    + ", ".join(duplicate_existing)
                    + ". Please use new IDs so records are not confused."
                )
            else:
                for uploaded_file, candidate_id in zip(uploaded_files, candidate_ids):
                    try:
                        pdf_bytes = uploaded_file.getvalue()
                        result = analyze_resume_pdf(
                            pdf_bytes,
                            job_description,
                            required_skills,
                        )
                        record_id = save_analysis(candidate_id, job_title, result)
                        saved_item = {
                            "record_id": record_id,
                            "candidate_id": candidate_id,
                            "job_title": job_title,
                            "filename": uploaded_file.name,
                            "result": result,
                        }
                        st.session_state.hirelens_analyses[str(record_id)] = saved_item
                        results_for_run.append(saved_item)
                    except ValueError as exc:
                        errors.append(f"{uploaded_file.name}: {exc}")
                    except Exception as exc:
                        # Keep a bad file from stopping the remaining batch.
                        errors.append(
                            f"{uploaded_file.name}: analysis failed ({type(exc).__name__}: {exc})"
                        )
            for error in errors:
                st.error(error)
            if results_for_run:
                st.success(
                    f"Successfully analyzed and saved {len(results_for_run)} resume(s). "
                    "Open HR Decision to record a human decision."
                )
    # Show saved results from this session.
    current_items = list(st.session_state.hirelens_analyses.values())
    if current_items:
        st.divider()
        st.subheader("Analysis results")
        for item in reversed(current_items):
            result = item["result"]
            with st.expander(
                f'{item["candidate_id"]} — {item["filename"]} '
                f'(Record #{item["record_id"]})',
                expanded=True,
            ):
                m1, m2, m3 = st.columns(3)
                m1.metric("Match Score", f'{result["match_score"]}/100')
                m2.metric("Skill Coverage", f'{result["skill_score"]:.1f}%')
                m3.metric("Text Similarity", f'{result["text_similarity"]:.1f}/100')
                st.progress(
                    max(0, min(100, int(round(float(result["match_score"])))))
                )
                st.write("**Matched skills**")
                matched = format_list(result.get("matched_skills"))
                st.write(", ".join(matched) if matched else "No required skills detected.")
                st.write("**Skills not detected**")
                missing = format_list(result.get("missing_skills"))
                st.write(", ".join(missing) if missing else "No missing required skills.")
                st.write("**AI recommendation (advisory only)**")
                st.write(result.get("recommendation", "No recommendation returned."))
                st.write("**Explanation**")
                reasons = result.get("reasons", [])
                if reasons:
                    for reason in reasons:
                        st.write(f"- {reason}")
                else:
                    st.write("The backend did not return explanation reasons.")
                st.caption(
                    "The score and recommendation come from the backend; "
                    "the frontend does not calculate a second score."
                )

with hr_tab:
    st.header("3. HR Decision")
    st.write(
        "Choose the final decision explicitly. The AI recommendation is not "
        "automatically used as the HR decision."
    )
    saved_records = read_saved_records()
    if not saved_records:
        st.info("No saved analyses found yet. Analyze and save a resume first.")
    else:
        record_options = {
            f'#{row["id"]} · {row["candidate_id"]} · {row["job_title"]} '
            f'· {"Published" if row["published"] else "Not published"}': row
            for row in saved_records
        }
        selected_label = st.selectbox(
            "Select a saved candidate record",
            list(record_options.keys()),
            key="hr_selected_record",
        )
        selected = record_options[selected_label]
        st.write(
            f'**Candidate ID:** {selected["candidate_id"]}  \n'
            f'**Role:** {selected["job_title"]}  \n'
            f'**AI recommendation:** {selected["ai_recommendation"]}'
        )
        if selected["hr_decision"]:
            st.write(f'**Current HR decision:** {selected["hr_decision"]}')
            st.write(f'**Current HR feedback:** {selected["hr_feedback"] or "No feedback"}')
            st.write(
                f'**Publication status:** {"Published" if selected["published"] else "Not published"}'
            )

        with st.form(f'hr_decision_form_{selected["id"]}'):
            decision = st.radio(
                "HR final decision",
                ["Shortlist", "Reject", "Hold"],
                horizontal=True,
                index=(
                    ["Shortlist", "Reject", "Hold"].index(selected["hr_decision"])
                    if selected["hr_decision"] in ["Shortlist", "Reject", "Hold"]
                    else 2
                ),
            )
            feedback = st.text_area(
                "HR feedback",
                value=selected["hr_feedback"] or "",
                placeholder="Enter feedback suitable for the candidate...",
                height=100,
            )
            confirm_decision = st.form_submit_button(
                "Confirm and Save HR Decision",
                type="primary",
                use_container_width=True,
            )

        if confirm_decision:
            try:
                record_hr_decision(selected["id"], decision, feedback)
                st.success(
                    "HR decision saved. It is not published yet. "
                    "Use the separate button below when ready."
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        # Refresh the selected row after saving.
        refreshed = next(
            (row for row in read_saved_records() if row["id"] == selected["id"]),
            selected,
        )
        if refreshed["hr_decision"] and not refreshed["published"]:
            st.warning("This decision is not visible in the Candidate Portal yet.")
            if st.button(
                f'Publish decision for {refreshed["candidate_id"]}',
                type="secondary",
                key=f'publish_{refreshed["id"]}',
                use_container_width=True,
            ):
                try:
                    publish_decision(refreshed["id"])
                    st.success("Decision published successfully.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        elif refreshed["published"]:
            st.success("This decision is already published.")

with portal_tab:
    st.header("4. Candidate Portal")
    st.write(
        "Demo portal: enter the exact candidate ID used when the resume was saved. "
        "Only published decisions are displayed."
    )
    candidate_lookup_id = st.text_input(
        "Candidate ID",
        value="DEMO-001",
        placeholder="e.g., DEMO-001",
        key="portal_candidate_id",
    )
    if st.button(
        "Check Published Decision",
        type="primary",
        use_container_width=True,
    ):
        if not candidate_lookup_id.strip():
            st.error("Please enter a candidate ID.")
        else:
            try:
                published = get_published_decision(candidate_lookup_id.strip())
                st.session_state["hirelens_portal_result"] = {
                    "candidate_id": candidate_lookup_id.strip(),
                    "published": published,
                }
            except Exception as exc:
                st.error(f"Could not retrieve the published decision: {exc}")

    portal_result = st.session_state.get("hirelens_portal_result")
    if portal_result:
        if portal_result["candidate_id"] != candidate_lookup_id.strip():
            st.session_state.pop("hirelens_portal_result", None)
            portal_result = None
    if portal_result:
        if not portal_result["published"]:
            st.info("Your application decision has not been published yet.")
        else:
            for published_row in portal_result["published"]:
                st.subheader(published_row["job_title"])
                st.write(f'**Final HR decision:** {published_row["hr_decision"]}')
                st.write(
                    f'**HR feedback:** {published_row["hr_feedback"] or "No feedback provided."}'
                )
                st.divider()
    st.caption(
        "This is a synthetic demonstration portal. A real deployment needs "
        "authentication and authorization to prevent candidates from accessing "
        "another person's results."
    )

with about_tab:
    st.header("About HireLens")
    st.write(
        "HireLens is an explainable AI hiring decision analysis dashboard. "
        "It compares resume text with job requirements and presents evidence "
        "for a human reviewer."
    )
    st.markdown("**Responsible-use principles**")
    st.write("- AI recommendations are advisory and never become HR decisions automatically.")
    st.write("- HR must explicitly select and save a decision.")
    st.write("- A separate action is required to publish the decision.")
    st.write("- Missing a skill in resume text does not prove the candidate lacks it.")
    st.write("- Scores measure textual alignment, not candidate worth or guaranteed performance.")
    
    st.divider()
    st.subheader("Project Team")
    st.caption(
        "MSc Artificial Intelligence | Human-Centred AI Project"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Aniket Kale")
        st.markdown("**Backend & AI Integration**")
        st.write(
            "Worked on backend logic, AI analysis integration, "
            "resume processing, database integration, testing, "
            "and deployment, with additional UI contributions."
        )

    with col2:
        st.markdown("### Sagar Chandratre")
        st.markdown("**Frontend & UI Design**")
        st.write(
            "Led the frontend interface and user-interface design "
            "to make the HireLens dashboard clear and easy to navigate."
        )

    st.caption(
        "HireLens — An Explainable AI Hiring Decision Analysis Dashboard"
    )

    st.write(
        "This college demo uses synthetic IDs. A real system needs "
        "authentication, authorization, data protection, and audit controls."
    )
