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

def submit_resumes(files, job, owner_id=None, owner_name=None, hr_mode=False):
    if not job:
        st.error("Save job requirements before uploading resumes.")
        return
    if not files:
        st.error("Please upload at least one PDF resume.")
        return
    success=0
    for pdf in files:
        try:
            result=analyze_resume_pdf(pdf.getvalue(),job["description"],job["skills"])
            name=owner_name if owner_id is not None else (st.session_state.get(f"name_{pdf.name}","").strip() or Path(pdf.name).stem)
            record_id=save_analysis(
                name,job["title"],result,applicant_user_id=owner_id,candidate_name=name,
                resume_pdf=pdf.getvalue(),resume_filename=pdf.name
            )
            with sqlite3.connect(DB_PATH) as con:
                con.row_factory=sqlite3.Row
                row=con.execute("SELECT application_id FROM candidates WHERE id=?",(record_id,)).fetchone()
            app_id=row["application_id"]
            st.success(f"Saved application ID: {app_id}")
            with st.expander(f"Analysis for {name} · {app_id}",expanded=True):
                show_result(result)
            success+=1
        except Exception as exc:
            st.error(f"Could not process {pdf.name}: {type(exc).__name__}: {exc}")
    if success:
        st.info("Save the application ID. HR can search it to retrieve the matching application.")

def login_page():
    brand()
    st.subheader("Welcome to your hiring workspace")
    st.write("Choose the appropriate account type. Candidate registration never creates an HR account.")
    tab_login,tab_register,tab_hr=st.tabs(["Login","Candidate Registration","Authorized HR Setup"])
    with tab_login:
        with st.form("login_form"):
            email=st.text_input("Email address",key="login_email")
            password=st.text_input("Password",type="password",key="login_password")
            submit=st.form_submit_button("Login",type="primary",use_container_width=True)
        if submit:
            try:
                user=authenticate_user(email,password)
                if user:
                    st.session_state["hirelens_user"]=user
                    st.rerun()
                else: st.error("Email or password is incorrect.")
            except Exception as exc: st.error(f"Login failed: {exc}")
    with tab_register:
        with st.form("candidate_register"):
            name=st.text_input("Full name",key="reg_name")
            email=st.text_input("Email address",key="reg_email")
            password=st.text_input("Password (minimum 10 characters)",type="password",key="reg_password")
            confirm=st.text_input("Confirm password",type="password",key="reg_confirm")
            submit=st.form_submit_button("Create Candidate Account",type="primary",use_container_width=True)
        if submit:
            if password!=confirm: st.error("Passwords do not match.")
            else:
                try:
                    register_candidate(name,email,password)
                    st.success("Candidate account created. Please log in.")
                except Exception as exc: st.error(str(exc))
    with tab_hr:
        st.warning("HR registration requires the administrator's private HIRELENS_HR_INVITE_KEY secret.")
        with st.form("hr_register"):
            name=st.text_input("HR full name",key="hr_reg_name")
            email=st.text_input("Work email",key="hr_reg_email")
            password=st.text_input("Password (minimum 10 characters)",type="password",key="hr_reg_password")
            confirm=st.text_input("Confirm password",type="password",key="hr_reg_confirm")
            invite=st.text_input("HR authorization key",type="password",key="hr_reg_invite")
            submit=st.form_submit_button("Create Authorized HR Account",type="primary",use_container_width=True)
        if submit:
            if password!=confirm: st.error("Passwords do not match.")
            else:
                try:
                    create_authorized_hr_user(name,email,password,invite)
                    st.success("HR account created. Please log in.")
                except Exception as exc: st.error(str(exc))

def logout():
    if st.sidebar.button("Log out",use_container_width=True):
        st.session_state.pop("hirelens_user",None)
        st.rerun()

def candidate_page(user):
    brand()
    st.sidebar.title("Candidate Portal")
    st.sidebar.write(f"Signed in as **{user['full_name']}**")
    logout()
    st.title("Your Candidate Dashboard")
    upload_tab,apps_tab,about_tab=st.tabs(["Upload Resume","My Applications","About"])
    with upload_tab:
        job=job_form("candidate")
        files=st.file_uploader("Upload resume PDF(s)",type=["pdf"],accept_multiple_files=True,key="candidate_pdfs")
        if st.button("Analyze and Submit",type="primary",use_container_width=True):
            submit_resumes(files,job,owner_id=user["id"],owner_name=user["full_name"])
    with apps_tab:
        apps=get_candidate_applications(user["id"])
        if not apps: st.info("You have no applications yet.")
        for app in apps:
            with st.container(border=True):
                st.subheader(app["job_title"])
                st.write(f"**Application ID:** `{app['application_id']}`")
                st.write(f"**Submitted:** {app['created_at']}")
                st.metric("Match score",f"{float(app['match_score']):.1f}/100")
                if app["published"]:
                    st.success(f"Published decision: {app['hr_decision']}")
                elif app["hr_decision"]:
                    st.info("HR has saved a decision, but has not published it.")
                else: st.info("Application submitted. No decision published yet.")
    with about_tab:
        st.info("AI scores are advisory and do not measure a candidate's worth or guarantee job performance.")

def hr_page(user):
    brand()
    st.sidebar.title("HR / Recruiter")
    st.sidebar.write(f"Signed in as **{user['full_name']}**")
    st.sidebar.caption("Authorized HR account")
    logout()
    st.title("HR / Recruiter Dashboard")
    overview,requirements,upload,search,decisions,about=st.tabs(
        ["Overview","Job Requirements","Upload Resumes","Search Application ID","HR Decisions","About"])
    with overview:
        rows=get_records()
        c1,c2,c3=st.columns(3)
        c1.metric("Applications",len(rows))
        c2.metric("Awaiting publication",sum(1 for r in rows if r["hr_decision"] and not r["published"]))
        c3.metric("Published decisions",sum(1 for r in rows if r["published"]))
        st.info("AI recommendations are advisory. HR retains the final decision.")
    with requirements:
        job_form("hr")
    with upload:
        st.write("HR uploads also receive a generated application ID. They are not linked to a candidate login automatically.")
        job=job_form("hr_upload")
        files=st.file_uploader("Upload candidate PDF resume(s)",type=["pdf"],accept_multiple_files=True,key="hr_pdfs")
        if files:
            for pdf in files:
                st.text_input(f"Candidate name for {pdf.name}",value=Path(pdf.name).stem,key=f"name_{pdf.name}")
        if st.button("Analyze and Save HR Upload(s)",type="primary",use_container_width=True):
            submit_resumes(files,job,hr_mode=True)
    with search:
        query=st.text_input("Application ID",placeholder="HL-1A2B3C4D",key="search_app_id")
        if st.button("Search Application",type="primary"):
            if not query.strip(): st.error("Enter an application ID.")
            else:
                record=get_application_by_id(query.strip())
                if record: st.session_state["found_application_id"]=record["application_id"]
                else:
                    st.session_state.pop("found_application_id",None)
                    st.error("No application found for that ID.")
        found=st.session_state.get("found_application_id")
        if found and query.strip().upper()==found:
            record=get_application_by_id(found)
            if record:
                st.subheader(record.get("candidate_name") or record["candidate_id"])
                st.write(f"**Application ID:** `{record['application_id']}`")
                st.write(f"**Job title:** {record['job_title']}")
                c1,c2,c3=st.columns(3)
                c1.metric("Match score",f"{float(record['match_score']):.1f}/100")
                c2.metric("Skill coverage",f"{float(record['skill_score']):.1f}%")
                c3.metric("Text similarity",f"{float(record['text_similarity']):.1f}/100")
                st.write("**Matched skills:**",record["matched_skills"] or "None detected")
                st.write("**Skills not detected:**",record["missing_skills"] or "None detected")
                st.write("**AI recommendation:**",record["ai_recommendation"])
                st.write("**HR decision:**",record["hr_decision"] or "Not decided")
                st.write("**Publication status:**","Published" if record["published"] else "Not published")
                resume=get_application_resume(record["id"])
                if resume:
                    st.download_button("Download original resume",resume["resume_pdf"],
                        file_name=resume["resume_filename"] or f"{found}.pdf",mime="application/pdf")
                else: st.warning("This older application has no saved PDF attached.")
    with decisions:
        rows=get_records()
        if not rows: st.info("No saved applications yet.")
        else:
            choices={f"{r['application_id'] or r['candidate_id']} · {r.get('candidate_name') or r['candidate_id']} · {r['job_title']}":r for r in rows}
            label=st.selectbox("Select application",list(choices.keys()))
            record=choices[label]
            st.write(f"**Application ID:** `{record.get('application_id') or record['candidate_id']}`")
            st.write(f"**Candidate:** {record.get('candidate_name') or record['candidate_id']}")
            st.write(f"**AI recommendation:** {record['ai_recommendation']}")
            with st.form(f"decision_form_{record['id']}"):
                options=["Shortlist","Reject","Hold"]
                previous=record["hr_decision"]
                decision=st.radio("HR final decision",options,horizontal=True,
                    index=options.index(previous) if previous in options else 2)
                feedback=st.text_area("HR feedback",value=record["hr_feedback"] or "")
                save=st.form_submit_button("Save HR Decision",type="primary",use_container_width=True)
            if save:
                try:
                    record_hr_decision(record["id"],decision,feedback)
                    st.success("Decision saved. It is not published yet.")
                    st.rerun()
                except Exception as exc: st.error(f"Could not save decision: {exc}")
            latest=get_application_by_id(record.get("application_id") or record["candidate_id"])
            if latest and latest.get("hr_decision") and not latest["published"]:
                if st.button("Publish Decision",key=f"publish_{record['id']}",use_container_width=True):
                    try:
                        publish_decision(record["id"])
                        st.success("Decision published.")
                        st.rerun()
                    except Exception as exc: st.error(f"Could not publish decision: {exc}")
            elif latest and latest["published"]:
                st.success("Decision is published.")
    with about:
        st.subheader("Responsible-use principles")
        st.write("- AI recommendations are advisory; HR makes the final decision.")
        st.write("- A skill not detected in resume text does not prove the candidate lacks it.")
        st.write("- Scores measure textual alignment, not candidate worth or guaranteed performance.")
        st.divider()
        st.subheader("Project Team")
        left,right=st.columns(2)
        with left:
            st.markdown("### Aniket Kale")
            st.write("Backend & AI Integration")
        with right:
            st.markdown("### Sagar Chandratre")
            st.write("Frontend & UI Design")

# Main application
if "hirelens_user" not in st.session_state:
    st.session_state["hirelens_user"]=None

if st.session_state["hirelens_user"] is None:
    login_page()
    st.stop()

user=st.session_state["hirelens_user"]
if user.get("role")=="candidate":
    candidate_page(user)
elif user.get("role")=="hr":
    hr_page(user)
else:
    st.session_state["hirelens_user"]=None
    st.error("Invalid account role. Please log in again.")
    st.stop()
