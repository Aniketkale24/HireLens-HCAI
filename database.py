import os
import re
import hmac
import secrets
import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hirelens.db"


def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def hash_password(password):
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 600_000
    )
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 600_000
        )
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError, AttributeError):
        return False


def generate_application_id(con):
    for _ in range(20):
        app_id = "HL-" + secrets.token_hex(4).upper()
        exists = con.execute(
            "SELECT 1 FROM candidates WHERE application_id=?",
            (app_id,)
        ).fetchone()
        if not exists:
            return app_id
    raise RuntimeError("Could not generate a unique application ID.")


def initialize_database():
    with get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('candidate','hr')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                job_title TEXT NOT NULL,
                match_score REAL NOT NULL,
                skill_score REAL NOT NULL,
                text_similarity REAL NOT NULL,
                matched_skills TEXT NOT NULL,
                missing_skills TEXT NOT NULL,
                ai_recommendation TEXT NOT NULL,
                hr_decision TEXT,
                hr_feedback TEXT,
                published INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cols = {
            row["name"]
            for row in con.execute("PRAGMA table_info(candidates)").fetchall()
        }

        migrations = {
            "application_id": "TEXT",
            "candidate_name": "TEXT",
            "applicant_user_id": "INTEGER",
            "resume_filename": "TEXT",
            "resume_pdf": "BLOB",
        }

        for name, column_type in migrations.items():
            if name not in cols:
                con.execute(
                    f"ALTER TABLE candidates ADD COLUMN {name} {column_type}"
                )

        con.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_application_id
            ON candidates(application_id)
            WHERE application_id IS NOT NULL
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_applicant_user
            ON candidates(applicant_user_id)
        """)

        old_rows = con.execute("""
            SELECT id, candidate_id
            FROM candidates
            WHERE application_id IS NULL OR application_id=''
        """).fetchall()

        for row in old_rows:
            con.execute("""
                UPDATE candidates
                SET application_id=?,
                    candidate_name=COALESCE(
                        NULLIF(candidate_name, ''), candidate_id
                    )
                WHERE id=?
            """, (generate_application_id(con), row["id"]))


def register_candidate(full_name, email, password):
    initialize_database()
    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise ValueError("Please enter your full name.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Please enter a valid email address.")

    hashed = hash_password(password)

    try:
        with get_connection() as con:
            cur = con.execute("""
                INSERT INTO users(full_name, email, password_hash, role)
                VALUES (?, ?, ?, 'candidate')
            """, (full_name, email, hashed))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email already exists.")


def create_authorized_hr_user(
    full_name, email, password, authorization_key
):
    expected = os.environ.get("HIRELENS_HR_INVITE_KEY")

    if not expected:
        raise RuntimeError(
            "Administrator must configure HIRELENS_HR_INVITE_KEY "
            "before HR registration."
        )

    if not hmac.compare_digest(authorization_key, expected):
        raise ValueError("Invalid HR authorization key.")

    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise ValueError("Please enter your full name.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Please enter a valid email address.")

    hashed = hash_password(password)

    try:
        with get_connection() as con:
            cur = con.execute("""
                INSERT INTO users(full_name, email, password_hash, role)
                VALUES (?, ?, ?, 'hr')
            """, (full_name, email, hashed))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email already exists.")


def authenticate_user(email, password):
    initialize_database()

    with get_connection() as con:
        row = con.execute("""
            SELECT id, full_name, email, password_hash, role
            FROM users WHERE email=?
        """, (email.strip().lower(),)).fetchone()

    if row and verify_password(password, row["password_hash"]):
        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "role": row["role"],
        }

    return None


def save_analysis(
    candidate_id,
    job_title,
    result,
    applicant_user_id=None,
    candidate_name=None,
    resume_pdf=None,
    resume_filename=None,
):
    initialize_database()
    name = (candidate_name or candidate_id or "Candidate").strip()

    with get_connection() as con:
        app_id = generate_application_id(con)

        cur = con.execute("""
            INSERT INTO candidates (
                candidate_id, application_id, candidate_name,
                applicant_user_id, resume_filename, resume_pdf,
                job_title, match_score, skill_score, text_similarity,
                matched_skills, missing_skills, ai_recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_id,
            app_id,
            name,
            applicant_user_id,
            resume_filename,
            sqlite3.Binary(resume_pdf) if resume_pdf is not None else None,
            job_title,
            result["match_score"],
            result["skill_score"],
            result["text_similarity"],
            ", ".join(result["matched_skills"]),
            ", ".join(result["missing_skills"]),
            result["recommendation"],
        ))

        return cur.lastrowid


def get_application_by_id(application_id):
    initialize_database()

    with get_connection() as con:
        row = con.execute("""
            SELECT id, candidate_id, application_id, candidate_name,
                   applicant_user_id, job_title, match_score, skill_score,
                   text_similarity, matched_skills, missing_skills,
                   ai_recommendation, hr_decision, hr_feedback, published,
                   resume_filename, created_at
            FROM candidates
            WHERE application_id=?
        """, (application_id.strip().upper(),)).fetchone()

        return dict(row) if row else None


def get_application_resume(record_id):
    initialize_database()

    with get_connection() as con:
        row = con.execute("""
            SELECT resume_pdf, resume_filename
            FROM candidates WHERE id=?
        """, (record_id,)).fetchone()

        if not row or not row["resume_pdf"]:
            return None

        return {
            "resume_pdf": bytes(row["resume_pdf"]),
            "resume_filename": row["resume_filename"],
        }


def get_candidate_applications(user_id):
    initialize_database()

    with get_connection() as con:
        rows = con.execute("""
            SELECT id, application_id, candidate_name, job_title,
                   match_score, hr_decision, published, created_at
            FROM candidates
            WHERE applicant_user_id=?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        return [dict(row) for row in rows]


def record_hr_decision(record_id, decision, feedback=""):
    if decision not in {"Shortlist", "Reject", "Hold"}:
        raise ValueError("Invalid HR decision.")

    initialize_database()

    with get_connection() as con:
        cur = con.execute("""
            UPDATE candidates
            SET hr_decision=?, hr_feedback=?, published=0
            WHERE id=?
        """, (decision, feedback, record_id))

        if cur.rowcount == 0:
            raise ValueError("Application record not found.")


def publish_decision(record_id):
    initialize_database()

    with get_connection() as con:
        cur = con.execute("""
            UPDATE candidates
            SET published=1
            WHERE id=? AND hr_decision IS NOT NULL
        """, (record_id,))

        if cur.rowcount == 0:
            raise ValueError(
                "Record not found or HR has not made a decision."
            )


def get_published_decision(candidate_id):
    initialize_database()

    with get_connection() as con:
        rows = con.execute("""
            SELECT candidate_id, application_id, candidate_name,
                   job_title, hr_decision, hr_feedback
            FROM candidates
            WHERE (candidate_id=? OR application_id=?)
              AND published=1
            ORDER BY id DESC
        """, (
            candidate_id.strip(),
            candidate_id.strip().upper(),
        )).fetchall()

        return [dict(row) for row in rows]


initialize_database()
