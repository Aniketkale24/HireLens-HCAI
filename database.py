
import os
import re
import hmac
import hashlib
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hirelens.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def hash_password(password):
    """Hash a password instead of storing it as plain text."""
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")

    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 600_000
    )
    return f"{salt.hex()}${hashed.hex()}"


def verify_password(password, stored_hash):
    try:
        salt_hex, hash_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 600_000
        )
        return hmac.compare_digest(actual_hash, expected_hash)
    except (ValueError, TypeError):
        return False


def generate_application_id(connection):
    """Generate an ID and verify that it is not already in use."""
    for _ in range(10):
        application_id = f"HL-{secrets.token_hex(4).upper()}"
        exists = connection.execute(
            "SELECT 1 FROM candidates WHERE application_id = ?",
            (application_id,),
        ).fetchone()

        if not exists:
            return application_id

    raise RuntimeError("Could not generate a unique application ID.")


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('candidate', 'hr')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
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

        # Migrate existing databases safely by adding only missing columns.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(candidates)"
            ).fetchall()
        }

        if "application_id" not in columns:
            connection.execute(
                "ALTER TABLE candidates ADD COLUMN application_id TEXT"
            )

        if "candidate_name" not in columns:
            connection.execute(
                "ALTER TABLE candidates ADD COLUMN candidate_name TEXT"
            )

        if "applicant_user_id" not in columns:
            connection.execute(
                "ALTER TABLE candidates ADD COLUMN applicant_user_id INTEGER"
            )

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_candidates_application_id
            ON candidates(application_id)
            WHERE application_id IS NOT NULL
        """)

        # Give existing records IDs too, without deleting their decisions.
        rows = connection.execute("""
            SELECT id, candidate_id
            FROM candidates
            WHERE application_id IS NULL OR application_id = ''
        """).fetchall()

        for row in rows:
            application_id = generate_application_id(connection)
            connection.execute("""
                UPDATE candidates
                SET application_id = ?,
                    candidate_name = COALESCE(candidate_name, candidate_id)
                WHERE id = ?
            """, (application_id, row["id"]))

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_candidates_candidate_id
            ON candidates(candidate_id)
        """)


def register_candidate(full_name, email, password):
    """Register a candidate account. Public registration cannot create HR."""
    initialize_database()

    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise ValueError("Please enter your full name.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Please enter a valid email address.")

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (?, ?, ?, 'candidate')
            """, (full_name, email, password_hash))
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email already exists.")


def create_authorized_hr_user(full_name, email, password, authorization_key):
    """
    Create an HR account only when the supplied key matches the secret
    configured in the HIRELENS_HR_INVITE_KEY environment variable.
    """
    expected_key = os.environ.get("HIRELENS_HR_INVITE_KEY")

    if not expected_key:
        raise RuntimeError(
            "HR account creation is not configured by the administrator."
        )

    if not hmac.compare_digest(authorization_key, expected_key):
        raise ValueError("Invalid HR authorization key.")

    initialize_database()
    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise ValueError("Please enter your full name.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Please enter a valid email address.")

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (?, ?, ?, 'hr')
            """, (full_name, email, password_hash))
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email already exists.")


def authenticate_user(email, password):
    """Return account details after verifying the password, or None."""
    initialize_database()
    email = email.strip().lower()

    with get_connection() as connection:
        row = connection.execute("""
            SELECT id, full_name, email, password_hash, role
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

    if row and verify_password(password, row["password_hash"]):
        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "role": row["role"],
        }

    return None


def save_analysis(
    candidate_id, job_title, result, applicant_user_id=None,
    candidate_name=None
):
    """
    Save an analysis with a generated application ID.
    The first argument remains for compatibility with the existing app.
    It is treated as the candidate name when candidate_name is not supplied.
    """
    initialize_database()

    name = (candidate_name or candidate_id or "").strip()
    if not name:
        name = "Candidate"

    with get_connection() as connection:
        application_id = generate_application_id(connection)

        cursor = connection.execute("""
            INSERT INTO candidates (
                candidate_id,
                application_id,
                candidate_name,
                applicant_user_id,
                job_title,
                match_score,
                skill_score,
                text_similarity,
                matched_skills,
                missing_skills,
                ai_recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            application_id,
            name,
            applicant_user_id,
            job_title,
            result["match_score"],
            result["skill_score"],
            result["text_similarity"],
            ", ".join(result["matched_skills"]),
            ", ".join(result["missing_skills"]),
            result["recommendation"],
        ))

        return cursor.lastrowid


def get_application_by_id(application_id):
    """Find one application by its generated ID."""
    initialize_database()

    with get_connection() as connection:
        row = connection.execute("""
            SELECT *
            FROM candidates
            WHERE application_id = ?
        """, (application_id.strip().upper(),)).fetchone()

        return dict(row) if row else None


def get_candidate_applications(user_id):
    """Return only the applications linked to a candidate account."""
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, application_id, candidate_name, job_title,
                   match_score, hr_decision, published, created_at
            FROM candidates
            WHERE applicant_user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        return [dict(row) for row in rows]


def record_hr_decision(record_id, decision, feedback=""):
    allowed_decisions = {"Shortlist", "Reject", "Hold"}

    if decision not in allowed_decisions:
        raise ValueError("Invalid HR decision.")

    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE candidates
            SET hr_decision = ?,
                hr_feedback = ?,
                published = 0
            WHERE id = ?
        """, (decision, feedback, record_id))

        if cursor.rowcount == 0:
            raise ValueError("Application record not found.")


def publish_decision(record_id):
    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE candidates
            SET published = 1
            WHERE id = ? AND hr_decision IS NOT NULL
        """, (record_id,))

        if cursor.rowcount == 0:
            raise ValueError(
                "Record not found or HR has not made a decision."
            )


def get_published_decision(candidate_id):
    """Compatibility function; accepts the application ID."""
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT candidate_id, application_id, candidate_name,
                   job_title, hr_decision, hr_feedback
            FROM candidates
            WHERE (candidate_id = ? OR application_id = ?)
              AND published = 1
            ORDER BY id DESC
        """, (candidate_id.strip(), candidate_id.strip().upper())).fetchall()

        return [dict(row) for row in rows]


initialize_database()
